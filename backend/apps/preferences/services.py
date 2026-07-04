from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from functools import lru_cache

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.books.models import BookTag
from apps.community.models import ReviewModerationStatus, UserReview, UserReviewLike
from apps.libraries.models import LibraryFacilityProfile, LibraryTag
from apps.myoutings.models import UserBookSave, UserLibrarySave, UserProgramSave
from apps.preferences.models import UserPreference, UserPreferenceItem, UserPreferenceStatus
from apps.programs.models import ProgramTag
from apps.tags.models import Tag


ALGORITHM_VERSION = "v1_recency365_halflife90_replace_all"
OBSERVATION_WINDOW_DAYS = 365
HALF_LIFE_DAYS = 90

SOURCE_LIBRARY = "library"
SOURCE_BOOK = "book"
SOURCE_PROGRAM = "program"
SOURCE_REVIEW_WRITTEN = "review_written"
SOURCE_REVIEW_LIKED = "review_liked"

SOURCE_WEIGHTS = {
    SOURCE_LIBRARY: Decimal("1.0"),
    SOURCE_BOOK: Decimal("1.0"),
    SOURCE_PROGRAM: Decimal("1.0"),
    SOURCE_REVIEW_WRITTEN: Decimal("1.5"),
    SOURCE_REVIEW_LIKED: Decimal("0.8"),
}

FACILITY_TAG_CODE_BY_FIELD = {
    "has_reading_room": "facility_reading_room",
    "has_children_room": "facility_children_room",
    "has_digital_room": "facility_digital_room",
    "has_parking": "facility_parking",
    "has_cafe": "facility_cafe",
    "has_wifi": "facility_wifi",
    "has_nursing_room": "facility_nursing_room",
    "has_accessible_facility": "facility_accessible",
    "has_elevator": "facility_elevator",
    "has_lounge": "facility_lounge",
    "has_outdoor_space": "facility_outdoor_space",
}
FACILITY_BONUS_MULTIPLIER = Decimal("0.5")


@dataclass
class PreferenceContribution:
    score: Decimal = Decimal("0")
    count: Decimal = Decimal("0")
    source_counts: dict = field(default_factory=lambda: defaultdict(int))


def mark_user_preference_pending(user):
    preference, _ = UserPreference.objects.get_or_create(user=user)
    if preference.status == UserPreferenceStatus.PENDING:
        return preference
    preference.status = UserPreferenceStatus.PENDING
    preference.failure_message = ""
    preference.save(update_fields=["status", "failure_message", "updated_at"])
    return preference


def schedule_user_preference_pending(user):
    # 저장/좋아요/후기 변경이 rollback되면 성향 상태도 바꾸지 않도록 commit 이후에 예약한다.
    transaction.on_commit(lambda: mark_user_preference_pending(user))


def ensure_user_preference_current(user):
    preference, _ = UserPreference.objects.get_or_create(user=user)
    if preference.status == UserPreferenceStatus.READY:
        return preference
    return rebuild_user_preference(user)


def get_behavior_preference_items(user, limit=None):
    preference = ensure_user_preference_current(user)
    queryset = (
        UserPreferenceItem.objects.filter(user_preference=preference)
        .select_related("tag")
        .order_by("rank", "-score", "tag_id")
    )
    if limit is not None:
        queryset = queryset[:limit]
    return list(queryset)


def rebuild_user_preference(user):
    preference, _ = UserPreference.objects.get_or_create(user=user)
    try:
        return _rebuild_user_preference(user, preference)
    except Exception as exc:
        preference.status = UserPreferenceStatus.FAILED
        preference.failure_message = f"{exc.__class__.__name__}: {str(exc)[:200]}"
        preference.save(update_fields=["status", "failure_message", "updated_at"])
        return preference


@transaction.atomic
def _rebuild_user_preference(user, preference):
    now = timezone.now()
    threshold = now - timedelta(days=OBSERVATION_WINDOW_DAYS)
    contributions = defaultdict(PreferenceContribution)

    signal_counts = {
        "library_signal_count": 0,
        "book_signal_count": 0,
        "program_signal_count": 0,
        "written_review_signal_count": 0,
        "liked_review_signal_count": 0,
    }

    saved_libraries = list(
        UserLibrarySave.objects.filter(user=user, library__is_active=True, created_at__gte=threshold)
        .select_related("library", "library__facility_profile")
        .prefetch_related("library__tag_links__tag")
    )
    signal_counts["library_signal_count"] = len(saved_libraries)
    for saved_library in saved_libraries:
        recency = recency_weight(saved_library.created_at, now)
        for link in active_links(saved_library.library.tag_links.all()):
            add_contribution(contributions, link.tag_id, SOURCE_LIBRARY, saved_library.created_at, recency, link.score, link.confidence)
        add_facility_contributions(contributions, saved_library.library_id, SOURCE_LIBRARY, saved_library.created_at, recency)

    saved_books = list(
        UserBookSave.objects.filter(user=user, book__is_active=True, created_at__gte=threshold)
        .select_related("book")
        .prefetch_related("book__tag_links__tag")
    )
    signal_counts["book_signal_count"] = len(saved_books)
    for saved_book in saved_books:
        recency = recency_weight(saved_book.created_at, now)
        for link in active_links(saved_book.book.tag_links.all()):
            add_contribution(contributions, link.tag_id, SOURCE_BOOK, saved_book.created_at, recency, link.score, link.confidence)

    saved_programs = list(
        UserProgramSave.objects.filter(
            user=user,
            program__is_visible=True,
            program__deleted_at__isnull=True,
            created_at__gte=threshold,
        )
        .select_related("program")
        .prefetch_related("program__tag_links__tag")
    )
    signal_counts["program_signal_count"] = len(saved_programs)
    for saved_program in saved_programs:
        recency = recency_weight(saved_program.created_at, now)
        for link in active_links(saved_program.program.tag_links.all()):
            add_contribution(contributions, link.tag_id, SOURCE_PROGRAM, saved_program.created_at, recency, link.score, link.confidence)

    written_reviews = list(
        UserReview.objects.filter(
            user=user,
            moderation_status=ReviewModerationStatus.VISIBLE,
            created_at__gte=threshold,
        ).prefetch_related("tag_links__tag")
    )
    signal_counts["written_review_signal_count"] = len(written_reviews)
    for review in written_reviews:
        recency = recency_weight(review.created_at, now)
        for link in review.tag_links.all():
            add_contribution(contributions, link.tag_id, SOURCE_REVIEW_WRITTEN, review.created_at, recency)

    liked_reviews = list(
        UserReviewLike.objects.filter(
            user=user,
            review__moderation_status=ReviewModerationStatus.VISIBLE,
            created_at__gte=threshold,
        )
        .exclude(review__user=user)
        .select_related("review")
        .prefetch_related("review__tag_links__tag")
    )
    signal_counts["liked_review_signal_count"] = len(liked_reviews)
    for liked_review in liked_reviews:
        recency = recency_weight(liked_review.created_at, now)
        for link in liked_review.review.tag_links.all():
            add_contribution(contributions, link.tag_id, SOURCE_REVIEW_LIKED, liked_review.created_at, recency)

    signal_count = sum(signal_counts.values())
    items = build_preference_items(preference, contributions)

    # 현재 알고리즘 버전의 결과만 유지해 이전 계산과 새 계산이 섞이지 않게 한다.
    UserPreferenceItem.objects.filter(user_preference=preference).delete()
    if items:
        UserPreferenceItem.objects.bulk_create(items)

    if signal_count and preference.eligible_since is None:
        preference.eligible_since = now
    if not signal_count:
        preference.eligible_since = None

    preference.status = UserPreferenceStatus.READY if signal_count else UserPreferenceStatus.COLLECTING
    preference.signal_count = signal_count
    preference.library_signal_count = signal_counts["library_signal_count"]
    preference.book_signal_count = signal_counts["book_signal_count"]
    preference.program_signal_count = signal_counts["program_signal_count"]
    preference.written_review_signal_count = signal_counts["written_review_signal_count"]
    preference.liked_review_signal_count = signal_counts["liked_review_signal_count"]
    preference.algorithm_version = ALGORITHM_VERSION
    preference.calculated_at = now
    preference.failure_message = ""
    preference.save(
        update_fields=[
            "status",
            "signal_count",
            "library_signal_count",
            "book_signal_count",
            "program_signal_count",
            "written_review_signal_count",
            "liked_review_signal_count",
            "algorithm_version",
            "eligible_since",
            "calculated_at",
            "failure_message",
            "updated_at",
        ]
    )
    return preference


def active_links(links):
    return [link for link in links if link.is_active]


def add_contribution(
    contributions,
    tag_id,
    source,
    observed_at,
    recency,
    score=Decimal("1"),
    confidence=Decimal("1"),
    multiplier=Decimal("1"),
):
    if not tag_id:
        return
    weighted_score = SOURCE_WEIGHTS[source] * recency * decimal_value(score) * decimal_value(confidence) * multiplier
    contribution = contributions[tag_id]
    contribution.score += weighted_score
    contribution.count += recency
    contribution.source_counts[source] += 1


def add_facility_contributions(contributions, library_id, source, observed_at, recency):
    try:
        facility_profile = LibraryFacilityProfile.objects.get(library_id=library_id)
    except LibraryFacilityProfile.DoesNotExist:
        return
    tag_by_code = get_facility_tag_by_code()
    for field, tag_code in FACILITY_TAG_CODE_BY_FIELD.items():
        if getattr(facility_profile, field) is not True:
            continue
        tag = tag_by_code.get(tag_code)
        if tag:
            add_contribution(
                contributions,
                tag.id,
                source,
                observed_at,
                recency,
                multiplier=FACILITY_BONUS_MULTIPLIER,
            )


@lru_cache(maxsize=1)
def get_facility_tag_by_code():
    return {
        tag.code: tag
        for tag in Tag.objects.filter(code__in=FACILITY_TAG_CODE_BY_FIELD.values(), is_active=True)
    }


def build_preference_items(preference, contributions):
    ranked = sorted(
        contributions.items(),
        key=lambda item: (-item[1].score, item[0]),
    )
    return [
        UserPreferenceItem(
            user_preference=preference,
            tag_id=tag_id,
            score=quantize(contribution.score),
            count=quantize(contribution.count),
            rank=rank,
            source_count_library=contribution.source_counts[SOURCE_LIBRARY],
            source_count_book=contribution.source_counts[SOURCE_BOOK],
            source_count_program=contribution.source_counts[SOURCE_PROGRAM],
            source_count_review_written=contribution.source_counts[SOURCE_REVIEW_WRITTEN],
            source_count_review_liked=contribution.source_counts[SOURCE_REVIEW_LIKED],
        )
        for rank, (tag_id, contribution) in enumerate(ranked, start=1)
        if contribution.score > 0
    ]


def recency_weight(observed_at, now):
    age_seconds = max((now - observed_at).total_seconds(), 0)
    age_days = age_seconds / 86400
    return Decimal(str(0.5 ** (age_days / HALF_LIFE_DAYS)))


def decimal_value(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def quantize(value):
    return value.quantize(Decimal("0.000001"))


def rebuild_user_preferences_for_queryset(queryset):
    stats = {
        "processed": 0,
        "ready": 0,
        "collecting": 0,
        "failed": 0,
        "items": 0,
    }
    for user in queryset:
        preference = rebuild_user_preference(user)
        stats["processed"] += 1
        if preference.status == UserPreferenceStatus.READY:
            stats["ready"] += 1
        elif preference.status == UserPreferenceStatus.COLLECTING:
            stats["collecting"] += 1
        else:
            stats["failed"] += 1
        stats["items"] += preference.items.count()
    return stats


def get_active_user_model():
    return get_user_model()
