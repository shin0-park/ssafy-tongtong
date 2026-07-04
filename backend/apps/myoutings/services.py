from collections import Counter
from decimal import Decimal

from django.db.models import Prefetch

from apps.community.models import ReviewModerationStatus, UserReview, UserReviewLike
from apps.integrations.gms import enhance_summary_sentence
from apps.libraries.models import LibraryStatisticSnapshot
from apps.libraries.services import FACILITY_FIELDS
from apps.myoutings.models import UserBookSave, UserLibrarySave, UserProgramSave
from apps.programs.models import ProgramCategory


TOP_ITEM_LIMIT = 5
AXES = ("study", "book", "program", "rest")

FACILITY_LABELS = {
    "has_reading_room": "열람실",
    "has_children_room": "어린이자료실",
    "has_digital_room": "디지털자료실",
    "has_parking": "주차장",
    "has_cafe": "카페",
    "has_wifi": "무료 와이파이",
    "has_nursing_room": "수유실",
    "has_accessible_facility": "이동약자 편의시설",
    "has_elevator": "엘리베이터",
    "has_lounge": "휴게 공간",
    "has_outdoor_space": "야외 공간",
}

FACILITY_AXIS_WEIGHTS = {
    "has_reading_room": {"study": Decimal("2.0")},
    "has_digital_room": {"study": Decimal("1.0")},
    "has_wifi": {"study": Decimal("0.7")},
    "has_children_room": {"rest": Decimal("0.7")},
    "has_nursing_room": {"rest": Decimal("0.4")},
    "has_lounge": {"rest": Decimal("1.2")},
    "has_outdoor_space": {"rest": Decimal("1.0")},
    "has_cafe": {"rest": Decimal("0.7")},
}

REVIEW_GROUP_AXIS_WEIGHTS = {
    "study_reading": {"study": Decimal("2.0")},
    "collection": {"book": Decimal("1.5")},
    "program": {"program": Decimal("1.5")},
    "space_atmosphere": {"rest": Decimal("1.5")},
    "kids_family": {"rest": Decimal("0.8")},
    "access_convenience": {"rest": Decimal("0.4")},
    "guidance_management": {"rest": Decimal("0.3")},
}

PROGRAM_CATEGORY_LABELS = dict(ProgramCategory.choices)
current_statistic_prefetch = Prefetch(
    "library__statistic_snapshots",
    queryset=LibraryStatisticSnapshot.objects.filter(is_current=True).order_by("-reference_date", "-id"),
    to_attr="current_statistic_snapshots",
)
review_library_statistic_prefetch = Prefetch(
    "library__statistic_snapshots",
    queryset=LibraryStatisticSnapshot.objects.filter(is_current=True).order_by("-reference_date", "-id"),
    to_attr="current_statistic_snapshots",
)
liked_review_library_statistic_prefetch = Prefetch(
    "review__library__statistic_snapshots",
    queryset=LibraryStatisticSnapshot.objects.filter(is_current=True).order_by("-reference_date", "-id"),
    to_attr="current_statistic_snapshots",
)


def build_my_outings_dashboard(user, preference=None):
    saved_libraries = list(
        UserLibrarySave.objects.filter(user=user, library__is_active=True)
        .select_related("library", "library__facility_profile")
        .prefetch_related("library__tag_links__tag", current_statistic_prefetch)
    )
    saved_books = list(
        UserBookSave.objects.filter(user=user, book__is_active=True)
        .select_related("book")
        .prefetch_related("book__tag_links__tag")
    )
    saved_programs = list(
        UserProgramSave.objects.filter(
            user=user,
            program__is_visible=True,
            program__deleted_at__isnull=True,
        )
        .select_related("program", "program__library")
        .prefetch_related("program__tag_links__tag")
    )
    written_reviews = list(
        UserReview.objects.filter(user=user, moderation_status=ReviewModerationStatus.VISIBLE)
        .select_related("library", "library__facility_profile")
        .prefetch_related(
            "tag_links__tag",
            review_library_statistic_prefetch,
            "book_references__book__tag_links__tag",
            "program_references__program__tag_links__tag",
        )
    )
    liked_reviews = list(
        UserReviewLike.objects.filter(
            user=user,
            review__moderation_status=ReviewModerationStatus.VISIBLE,
        )
        .select_related("review", "review__library", "review__library__facility_profile")
        .prefetch_related(
            "review__tag_links__tag",
            liked_review_library_statistic_prefetch,
            "review__book_references__book__tag_links__tag",
            "review__program_references__program__tag_links__tag",
        )
    )

    profile_summary = build_profile_summary(user, saved_libraries, saved_books, saved_programs, written_reviews, liked_reviews)
    activity_summary = build_activity_summary(profile_summary)
    written_review_ids = {review.id for review in written_reviews}
    behavior_liked_reviews = [
        liked_review for liked_review in liked_reviews if liked_review.review_id not in written_review_ids
    ]

    counters = build_behavior_counters(saved_libraries, saved_books, saved_programs, written_reviews, behavior_liked_reviews)
    axis_scores = calculate_axis_scores(saved_libraries, saved_books, saved_programs, written_reviews, behavior_liked_reviews)
    signal_count = activity_summary["total_signal_count"]
    preference_status = build_preference_status(preference, signal_count)

    rule_summary_sentence = build_summary_sentence(axis_scores, counters, signal_count)
    dashboard = {
        "profile_summary": profile_summary,
        "activity_summary": activity_summary,
        "preference_summary": {
            "top_regions": top_region_items(counters["regions"]),
            "top_library_facilities": top_counter_items(counters["facilities"]),
            "top_book_subjects": top_counter_items(counters["book_subjects"]),
            "top_program_categories": top_counter_items(counters["program_categories"]),
            "top_review_tags": top_counter_items(counters["review_tags"]),
        },
        "outing_type_summary": normalize_axis_scores(axis_scores),
        "summary_sentence": build_enhanced_summary_sentence(axis_scores, counters, signal_count, rule_summary_sentence),
        "analysis_basis": build_analysis_basis(signal_count),
        "preference_status": preference_status,
    }
    return dashboard


def build_profile_summary(user, saved_libraries, saved_books, saved_programs, written_reviews, liked_reviews):
    return {
        "nickname": user.nickname,
        "saved_library_count": len(saved_libraries),
        "saved_book_count": len(saved_books),
        "saved_program_count": len(saved_programs),
        "review_count": len(written_reviews),
        "liked_review_count": len(liked_reviews),
    }


def build_activity_summary(profile_summary):
    total_saved_count = (
        profile_summary["saved_library_count"]
        + profile_summary["saved_book_count"]
        + profile_summary["saved_program_count"]
    )
    return {
        "total_saved_count": total_saved_count,
        "total_review_count": profile_summary["review_count"],
        "total_like_count": profile_summary["liked_review_count"],
        "total_signal_count": total_saved_count + profile_summary["review_count"] + profile_summary["liked_review_count"],
    }


def build_behavior_counters(saved_libraries, saved_books, saved_programs, written_reviews, liked_reviews):
    counters = {
        "regions": Counter(),
        "facilities": Counter(),
        "book_subjects": Counter(),
        "program_categories": Counter(),
        "review_tags": Counter(),
    }

    for library in iter_libraries(saved_libraries, written_reviews, liked_reviews):
        counters["regions"][region_key(library)] += 1
        for field in true_facility_fields(library):
            counters["facilities"][(field, FACILITY_LABELS[field])] += 1

    for saved_book in saved_books:
        count_book_subjects(counters["book_subjects"], saved_book.book)

    for saved_program in saved_programs:
        count_program_category(counters["program_categories"], saved_program.program)

    for review in written_reviews:
        count_review_tags(counters["review_tags"], review)
        for reference in review.book_references.all():
            count_book_subjects(counters["book_subjects"], reference.book)
        for reference in review.program_references.all():
            count_program_category(counters["program_categories"], reference.program)

    for liked_review in liked_reviews:
        review = liked_review.review
        count_review_tags(counters["review_tags"], review)
        for reference in review.book_references.all():
            count_book_subjects(counters["book_subjects"], reference.book)
        for reference in review.program_references.all():
            count_program_category(counters["program_categories"], reference.program)

    return counters


def iter_libraries(saved_libraries, written_reviews, liked_reviews):
    for saved_library in saved_libraries:
        yield saved_library.library
    for review in written_reviews:
        yield review.library
    for liked_review in liked_reviews:
        yield liked_review.review.library


def region_key(library):
    return (f"21:{library.sigungu}", library.sido, library.sigungu)


def true_facility_fields(library):
    try:
        facility_profile = library.facility_profile
    except Exception:
        return []
    return [field for field in FACILITY_FIELDS if getattr(facility_profile, field) is True]


def count_book_subjects(counter, book):
    tag_links = [link for link in book.tag_links.all() if link.is_active]
    if tag_links:
        for link in tag_links:
            counter[(link.tag.code, link.tag.label)] += 1
        return
    if book.kdc_class_name:
        code = book.kdc_class_no[:1] if book.kdc_class_no else "kdc_unknown"
        label = book.kdc_class_name.split(">")[0].strip()
        counter[(f"kdc_{code}", label)] += 1


def count_program_category(counter, program):
    code = program.category_code or "other"
    counter[(code, PROGRAM_CATEGORY_LABELS.get(code, "기타"))] += 1
    for link in program.tag_links.all():
        if link.is_active:
            counter[(link.tag.code, link.tag.label)] += 1


def count_review_tags(counter, review):
    for link in review.tag_links.all():
        counter[(link.tag.code, link.tag.review_label or link.tag.label)] += 1


def calculate_axis_scores(saved_libraries, saved_books, saved_programs, written_reviews, liked_reviews):
    scores = {axis: Decimal("0") for axis in AXES}

    for saved_library in saved_libraries:
        add_library_axis_scores(scores, saved_library.library)
    for saved_book in saved_books:
        scores["book"] += Decimal("1.5")
        add_book_axis_scores(scores, saved_book.book)
    for saved_program in saved_programs:
        scores["program"] += Decimal("1.5")
    for review in written_reviews:
        add_review_axis_scores(scores, review, weight=Decimal("1.2"))
        add_library_axis_scores(scores, review.library, weight=Decimal("0.4"))
    for liked_review in liked_reviews:
        add_review_axis_scores(scores, liked_review.review, weight=Decimal("1.0"))
        add_library_axis_scores(scores, liked_review.review.library, weight=Decimal("0.3"))

    return scores


def add_library_axis_scores(scores, library, weight=Decimal("1")):
    for field in true_facility_fields(library):
        for axis, axis_weight in FACILITY_AXIS_WEIGHTS.get(field, {}).items():
            scores[axis] += axis_weight * weight
    try:
        statistic = library.current_statistic_snapshots[0] if library.current_statistic_snapshots else None
    except AttributeError:
        statistic = library.statistic_snapshots.filter(is_current=True).order_by("-reference_date", "-id").first()
    if statistic:
        if statistic.reading_seat_count and statistic.reading_seat_count >= 100:
            scores["study"] += Decimal("0.6") * weight
        if statistic.book_count and statistic.book_count >= 50000:
            scores["book"] += Decimal("0.8") * weight


def add_book_axis_scores(scores, book):
    if book.kdc_class_name and any(keyword in book.kdc_class_name for keyword in ("문학", "총류", "사회과학", "자연과학")):
        scores["book"] += Decimal("0.5")


def add_review_axis_scores(scores, review, weight):
    for link in review.tag_links.all():
        review_group = link.tag.review_group
        for axis, axis_weight in REVIEW_GROUP_AXIS_WEIGHTS.get(review_group, {}).items():
            scores[axis] += axis_weight * weight


def normalize_axis_scores(scores):
    total = sum(scores.values(), Decimal("0"))
    if total <= 0:
        return {axis: 0.0 for axis in AXES}

    percentages = {
        axis: float((scores[axis] / total * Decimal("100")).quantize(Decimal("0.1")))
        for axis in AXES
    }
    correction = round(100.0 - sum(percentages.values()), 1)
    if correction:
        top_axis = max(AXES, key=lambda axis: percentages[axis])
        percentages[top_axis] = round(percentages[top_axis] + correction, 1)
    return percentages


def build_summary_sentence(axis_scores, counters, signal_count):
    if signal_count == 0:
        return "아직 나들이 취향을 분석할 활동이 충분하지 않아요."

    top_axis = max(AXES, key=lambda axis: axis_scores[axis])
    top_facility = first_label(counters["facilities"])
    top_book = first_label(counters["book_subjects"])
    top_program = first_label(counters["program_categories"])
    top_review = first_label(counters["review_tags"])

    if top_axis == "study":
        focus = top_review or top_facility or "조용한 학습공간"
        return f"{focus} 중심으로 공부하기 좋은 도서관을 자주 찾고 있어요."
    if top_axis == "book":
        focus = top_book or "장서가 풍부한 도서관"
        return f"{focus} 분야와 책 탐색에 관심이 많아요."
    if top_axis == "program":
        focus = top_program or "문화 프로그램"
        return f"{focus} 중심의 도서관 활동에 관심이 많아요."

    focus = top_facility or top_review or "편안한 공간"
    return f"{focus} 같은 머물기 좋은 도서관을 선호하고 있어요."


def build_enhanced_summary_sentence(axis_scores, counters, signal_count, rule_sentence):
    if signal_count == 0:
        return rule_sentence
    # GMS는 규칙 기반 결과를 문장으로 다듬는 보조 단계이며, 점수나 사실 필드는 바꾸지 않는다.
    enhanced = enhance_summary_sentence(
        {
            "top_axis": top_axis_code(axis_scores),
            "top_labels": summary_top_labels(counters),
            "signal_count": signal_count,
            "rule_sentence": rule_sentence,
        }
    )
    return enhanced or rule_sentence


def top_axis_code(axis_scores):
    if not axis_scores:
        return ""
    return max(AXES, key=lambda axis: axis_scores[axis])


def summary_top_labels(counters):
    labels = []
    for key in ("facilities", "book_subjects", "program_categories", "review_tags"):
        label = first_label(counters[key])
        if label and label not in labels:
            labels.append(label)
    return labels[:TOP_ITEM_LIMIT]


def build_analysis_basis(signal_count):
    if signal_count == 0:
        return {
            "has_enough_data": False,
            "basis_text": "도서관, 책, 프로그램을 저장하거나 후기를 남기면 취향을 보여드릴게요.",
            "signal_count": 0,
        }
    return {
        "has_enough_data": True,
        "basis_text": "저장한 도서관, 책, 프로그램과 작성·좋아요한 후기를 바탕으로 분석했어요.",
        "signal_count": signal_count,
    }


def build_preference_status(preference, fallback_signal_count):
    if preference is None:
        return {
            "status": "ready" if fallback_signal_count else "collecting",
            "signal_count": fallback_signal_count,
            "calculated_at": None,
        }
    return {
        "status": preference.status,
        "signal_count": preference.signal_count,
        "calculated_at": preference.calculated_at,
    }


def top_region_items(counter):
    return [
        {
            "region_key": region_key_value,
            "sido": sido,
            "sigungu": sigungu,
            "count": count,
            "score": score_string(count),
        }
        for (region_key_value, sido, sigungu), count in counter.most_common(TOP_ITEM_LIMIT)
    ]


def top_counter_items(counter):
    return [
        {
            "code": code,
            "label": label,
            "count": count,
            "score": score_string(count),
        }
        for (code, label), count in counter.most_common(TOP_ITEM_LIMIT)
    ]


def first_label(counter):
    if not counter:
        return ""
    return counter.most_common(1)[0][0][1]


def score_string(value):
    return str(Decimal(value).quantize(Decimal("0.0000")))
