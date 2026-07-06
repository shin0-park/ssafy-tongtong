import math

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone

from apps.accounts.models import (
    UserPreferredPurpose,
    UserPreferredRegion,
    UserPreferredTag,
)
from apps.libraries.models import (
    Library,
    LibraryFacilityProfile,
    LibraryImage,
    LibraryStatisticSnapshot,
    LibraryTag,
)
from apps.libraries.serializers import library_thumbnail_image_queryset
from apps.libraries.services import resolve_library_operation_status
from apps.preferences.services import (
    ensure_user_preference_current,
    get_behavior_preference_items,
)
from apps.tags.models import Tag

from .models import (
    DailyLibraryRecommendationSet,
    DailyRecommendationTheme,
    Purpose,
)
from .providers import RecommendationProviderError, get_provider
from .schemas import (
    RecommendationSchemaError,
    validate_preference_plan,
    validate_rerank_result,
)


HOME_PURPOSE_CODES = ("study", "book", "kids", "mood", "nearby")
TODAY_ITEM_LIMIT = 3
THEME_ITEM_LIMIT = 6
PERSONAL_ITEM_LIMIT = 3
BEHAVIOR_ITEM_LIMIT = 20
MANUAL_PERSONAL_WEIGHT = 1.0
BEHAVIOR_PERSONAL_WEIGHT = 0.5

TODAY_THEME_REASON_TEMPLATES = {
    "large_space": "넓은 공간과 규모를 기준으로 골랐어요.",
    "rich_collection": "장서 규모가 돋보이는 도서관이에요.",
    "mood_space": "공간 분위기와 머무르기 좋은 조건을 기준으로 골랐어요.",
    "study_seats": "좌석과 열람 환경을 기준으로 골랐어요.",
    "family_outing": "어린이·가족 방문에 어울리는 조건을 기준으로 골랐어요.",
    "restful_space": "쉬어가기 좋은 공간 조건을 기준으로 골랐어요.",
}

PURPOSE_REASON_TEMPLATES = {
    "study": "좌석과 열람 공간을 기준으로 골랐어요.",
    "book": "장서 규모를 기준으로 골랐어요.",
    "kids": "어린이·가족 방문에 어울리는 조건을 기준으로 골랐어요.",
    "mood": "머무르기 좋은 공간과 편의시설을 기준으로 골랐어요.",
    "nearby": "좌표가 확인된 도서관을 기준으로 골랐어요.",
}


def build_home_payload(user=None, lat=None, lng=None, date=None):
    date = date or timezone.localdate()
    libraries = list(get_candidate_libraries())
    stat_max = build_stat_max(libraries)
    today = build_today_recommendations(libraries, stat_max, date)
    themes = build_theme_recommendations(libraries, stat_max, lat, lng)
    personal = build_personal_recommendations(user, libraries, stat_max)
    return {
        "today": today,
        "themes": themes,
        "personal": personal,
    }


def get_candidate_libraries():
    return (
        Library.objects.filter(is_active=True)
        .select_related("facility_profile")
        .prefetch_related(
            Prefetch(
                "statistic_snapshots",
                queryset=LibraryStatisticSnapshot.objects.filter(is_current=True).order_by("-reference_date", "-id"),
                to_attr="current_statistic_snapshots",
            ),
            Prefetch(
                "images",
                queryset=library_thumbnail_image_queryset(LibraryImage.objects.all()),
                to_attr="thumbnail_images",
            ),
            Prefetch(
                "tag_links",
                queryset=LibraryTag.objects.filter(is_active=True).select_related("tag"),
                to_attr="active_tag_links",
            ),
        )
    )


def build_stat_max(libraries):
    max_values = {
        "book_count": 0,
        "reading_seat_count": 0,
        "building_area": 0,
        "site_area": 0,
    }
    for library in libraries:
        statistic = get_current_statistic(library)
        if not statistic:
            continue
        for field in max_values:
            max_values[field] = max(max_values[field], number(getattr(statistic, field, 0)))
    return max_values


def build_today_recommendations(libraries, stat_max, date):
    saved_set = (
        DailyLibraryRecommendationSet.objects.filter(recommendation_date=date)
        .select_related("theme")
        .prefetch_related("items")
        .order_by("-generated_at", "-id")
        .first()
    )
    if saved_set:
        library_by_id = {library.id: library for library in libraries}
        items = []
        for recommendation_item in saved_set.items.all().order_by("rank", "id")[:TODAY_ITEM_LIMIT]:
            library = library_by_id.get(recommendation_item.library_id)
            if not library:
                continue
            set_reason(library, TODAY_THEME_REASON_TEMPLATES.get(saved_set.theme.code, "오늘의 추천 기준으로 골랐어요."))
            items.append(library)
        return {
            "theme": theme_payload(saved_set.theme),
            "items": items,
        }

    themes = list(DailyRecommendationTheme.objects.filter(is_active=True).order_by("display_order", "code"))
    if not themes:
        return {"theme": None, "items": []}

    # 저장된 추천 세트가 없을 때만 날짜 기준 테마를 선택해 홈이 매일 같은 규칙으로 재현되게 한다.
    theme = themes[date.toordinal() % len(themes)]
    items = rank_libraries(
        libraries,
        lambda library: score_daily_theme(library, theme.code, stat_max),
        TODAY_ITEM_LIMIT,
        TODAY_THEME_REASON_TEMPLATES.get(theme.code, "오늘의 추천 기준으로 골랐어요."),
    )
    return {
        "theme": theme_payload(theme),
        "items": items,
    }


def build_theme_recommendations(libraries, stat_max, lat=None, lng=None):
    purposes = Purpose.objects.filter(
        code__in=HOME_PURPOSE_CODES,
        is_active=True,
        is_home_theme=True,
    ).order_by("display_order", "code")
    purpose_by_code = {purpose.code: purpose for purpose in purposes}
    recommendations = []
    for code in HOME_PURPOSE_CODES:
        purpose = purpose_by_code.get(code)
        if not purpose:
            continue
        items = rank_libraries(
            libraries,
            lambda library, purpose_code=code: score_purpose(library, purpose_code, stat_max, lat, lng),
            THEME_ITEM_LIMIT,
            PURPOSE_REASON_TEMPLATES.get(code, "테마 조건을 기준으로 골랐어요."),
        )
        recommendations.append({"purpose": purpose, "items": items})
    return recommendations


def build_personal_recommendations(user, libraries, stat_max):
    if not user or not user.is_authenticated:
        return {
            "available": False,
            "reason": "로그인 후 선호 목적과 지역을 설정하면 맞춤 추천을 볼 수 있어요.",
            "priority_tags": [],
            "fallback_used": False,
            "provider": None,
            "mode": "unavailable",
            "items": [],
        }

    preferred_purposes = list(
        UserPreferredPurpose.objects.filter(user=user, is_active=True, purpose__is_active=True)
        .select_related("purpose")
        .order_by("display_order", "id")
    )
    preferred_regions = list(
        UserPreferredRegion.objects.filter(user=user, is_active=True).order_by("display_order", "id")
    )
    preferred_tags = list(
        UserPreferredTag.objects.filter(user=user, is_active=True, tag__is_active=True)
        .select_related("tag")
        .order_by("display_order", "id")
    )
    has_manual_preference = bool(preferred_purposes or preferred_regions or preferred_tags)
    preference = ensure_user_preference_current(user)
    behavior_items = get_behavior_preference_items(user, limit=BEHAVIOR_ITEM_LIMIT) if preference.signal_count else []
    behavior_tag_scores = build_behavior_tag_scores(behavior_items)
    has_behavior_preference = bool(behavior_tag_scores)

    if not has_manual_preference and not has_behavior_preference:
        return {
            "available": False,
            "reason": "선호 목적과 지역을 설정하면 맞춤 추천을 볼 수 있어요.",
            "priority_tags": [],
            "fallback_used": False,
            "provider": None,
            "mode": "unavailable",
            "items": [],
        }

    region_values = {preference.sigungu for preference in preferred_regions if preference.sigungu}
    purpose_codes = [preference.purpose.code for preference in preferred_purposes]
    tag_codes = [preference.tag.code for preference in preferred_tags]
    reason = personal_reason(has_manual_preference, has_behavior_preference)
    context = build_preference_planning_context(
        preferred_purposes,
        preferred_regions,
        preferred_tags,
        behavior_items,
    )
    result = build_personal_recommendations_v4(
        libraries,
        stat_max,
        purpose_codes,
        region_values,
        tag_codes,
        behavior_tag_scores,
        context,
        reason,
    )
    if not result["items"]:
        return {
            "available": False,
            "reason": "추천에 사용할 수 있는 운영 중 도서관이 아직 없어요.",
            "priority_tags": result["priority_tags"],
            "fallback_used": result["fallback_used"],
            "provider": result["provider"],
            "mode": result["mode"],
            "items": [],
        }
    return {
        "available": True,
        "reason": reason,
        **result,
    }


def build_personal_recommendations_v4(
    libraries,
    stat_max,
    purpose_codes,
    region_values,
    tag_codes,
    behavior_tag_scores,
    context,
    reason,
):
    fallback_used = False
    provider_code = None
    try:
        if not getattr(settings, "AI_RECOMMENDATION_ENABLED", True):
            raise RecommendationProviderError("AI recommendation is disabled.")
        provider_code = getattr(settings, "AI_RECOMMENDATION_PROVIDER", "mock")
        provider = get_provider(provider_code)
        plan = validate_preference_plan(
            provider.plan_preferences(context),
            valid_purpose_codes=get_valid_profile_purpose_codes(),
            valid_tag_codes=get_valid_tag_codes(),
        )
        public_candidates, candidate_by_id = retrieve_personal_candidates(
            libraries,
            stat_max,
            purpose_codes,
            region_values,
            tag_codes,
            behavior_tag_scores,
            plan,
            reason,
        )
        rerank_result = validate_rerank_result(
            provider.rerank_libraries({"plan": plan, "candidates": public_candidates}),
            candidate_by_id=candidate_by_id,
            valid_tag_codes=get_valid_tag_codes(),
        )
        items = apply_rerank_result(rerank_result, candidate_by_id)
        if not items:
            raise RecommendationProviderError("Provider returned no valid recommendation items.")
        return build_personal_result(plan, items, fallback_used, provider_code, "ai")
    except (RecommendationProviderError, RecommendationSchemaError, TypeError, ValueError):
        fallback_used = True

    fallback_provider_code = getattr(settings, "AI_RECOMMENDATION_FALLBACK_PROVIDER", "rule_based")
    try:
        fallback_provider = get_provider(fallback_provider_code)
        fallback_plan = validate_preference_plan(
            fallback_provider.plan_preferences(context),
            valid_purpose_codes=get_valid_profile_purpose_codes(),
            valid_tag_codes=get_valid_tag_codes(),
        )
        fallback_public_candidates, fallback_candidate_by_id = retrieve_personal_candidates(
            libraries,
            stat_max,
            purpose_codes,
            region_values,
            tag_codes,
            behavior_tag_scores,
            fallback_plan,
            reason,
        )
        fallback_rerank_result = validate_rerank_result(
            fallback_provider.rerank_libraries({"plan": fallback_plan, "candidates": fallback_public_candidates}),
            candidate_by_id=fallback_candidate_by_id,
            valid_tag_codes=get_valid_tag_codes(),
        )
        fallback_items = apply_rerank_result(fallback_rerank_result, fallback_candidate_by_id)
        return build_personal_result(fallback_plan, fallback_items, fallback_used, fallback_provider_code, "fallback")
    except (RecommendationProviderError, RecommendationSchemaError, TypeError, ValueError):
        return build_personal_result(
            {"priority_tags": []},
            [],
            True,
            fallback_provider_code or "unavailable",
            "fallback_failed",
        )


def build_preference_planning_context(preferred_purposes, preferred_regions, preferred_tags, behavior_items):
    return {
        "user_summary": {
            "signal_count": len(behavior_items),
            "top_behavior_tags": [
                {
                    "code": item.tag.code,
                    "label": item.tag.label,
                    "score": float(item.score or 0),
                }
                for item in behavior_items[:BEHAVIOR_ITEM_LIMIT]
                if item.tag_id and item.tag
            ],
        },
        "manual_preferences": {
            "purposes": [preference.purpose.code for preference in preferred_purposes],
            "regions": [preference.sigungu for preference in preferred_regions if preference.sigungu],
            "tags": [preference.tag.code for preference in preferred_tags],
        },
        "available_tag_codes": sorted(get_valid_tag_codes()),
    }


def retrieve_personal_candidates(
    libraries,
    stat_max,
    purpose_codes,
    region_values,
    tag_codes,
    behavior_tag_scores,
    plan,
    reason,
):
    candidate_limit = max(1, int(getattr(settings, "AI_RECOMMENDATION_CANDIDATE_LIMIT", 20)))
    scored_candidates = []
    plan_tag_codes = [item["code"] for item in plan.get("priority_tags", [])]
    plan_region_values = {
        item["sigungu"] for item in plan.get("preferred_regions", []) if item.get("sigungu")
    }

    for library in libraries:
        if not library.is_active:
            continue
        operation_status = resolve_library_operation_status(library)
        if operation_status["open_today"] is not True:
            continue
        baseline_score = score_personal_with_behavior(
            library,
            purpose_codes,
            region_values,
            tag_codes,
            behavior_tag_scores,
            stat_max,
        )
        baseline_score += score_plan_tags(library, plan_tag_codes, stat_max)
        if library.sigungu in plan_region_values:
            baseline_score += 1
        if baseline_score <= 0:
            continue
        scored_candidates.append(
            (
                -baseline_score,
                library.name,
                library.id,
                build_candidate_feature(library, baseline_score, plan_tag_codes, plan_region_values, reason),
            )
        )

    scored_candidates.sort()
    internal_candidates = [candidate for _, _, _, candidate in scored_candidates[:candidate_limit]]
    return (
        [candidate["public"] for candidate in internal_candidates],
        {candidate["public"]["library_id"]: candidate for candidate in internal_candidates},
    )


def build_candidate_feature(library, baseline_score, plan_tag_codes, plan_region_values, reason):
    feature_tags = get_library_feature_tag_codes(library)
    matched_plan_tags = [code for code in feature_tags if code in plan_tag_codes]
    statistic = get_current_statistic(library)
    book_count_bucket = number_bucket(statistic.book_count if statistic else None)
    reading_seat_count_bucket = number_bucket(statistic.reading_seat_count if statistic else None)
    allowed_evidence_codes, evidence_labels = build_allowed_evidence(
        library,
        feature_tags,
        book_count_bucket,
        reading_seat_count_bucket,
    )
    public_candidate = {
        "library_id": library.id,
        "name": library.name,
        "sigungu": library.sigungu,
        "baseline_score": baseline_score,
        "feature_tags": feature_tags[:20],
        "matched_plan_tags": matched_plan_tags[:5],
        "matched_region": library.sigungu in plan_region_values,
        "stats": {
            "book_count_bucket": book_count_bucket,
            "reading_seat_count_bucket": reading_seat_count_bucket,
        },
        "operation": {
            "open_today": True,
        },
        "allowed_evidence_codes": allowed_evidence_codes,
        "evidence_labels": evidence_labels,
        "fallback_reason": reason,
    }
    return {
        "public": public_candidate,
        "_library": library,
    }


def build_allowed_evidence(library, feature_tags, book_count_bucket, reading_seat_count_bucket):
    evidence_labels = {}
    evidence_codes = []

    for tag_code in feature_tags[:20]:
        evidence_code = f"tag:{tag_code}"
        evidence_codes.append(evidence_code)
        evidence_labels[evidence_code] = tag_label(tag_code)

    if book_count_bucket in {"medium", "large"}:
        evidence_codes.append("metric:book_count_high")
        evidence_labels["metric:book_count_high"] = "장서 규모"
    if reading_seat_count_bucket in {"medium", "large"}:
        evidence_codes.append("metric:reading_seat_count_high")
        evidence_labels["metric:reading_seat_count_high"] = "좌석 규모"

    evidence_codes.append("operation:open_today")
    evidence_labels["operation:open_today"] = "오늘 운영"

    if library.sigungu:
        region_code = f"region:{library.sigungu}"
        evidence_codes.append(region_code)
        evidence_labels[region_code] = f"{library.sigungu} 지역"

    return dedupe(evidence_codes), evidence_labels


def apply_rerank_result(rerank_result, candidate_by_id):
    items = []
    for item in rerank_result["items"][:PERSONAL_ITEM_LIMIT]:
        candidate = candidate_by_id.get(item["library_id"])
        if not candidate:
            continue
        library = candidate["_library"]
        library.ai_rank = item["rank"]
        library.ai_confidence = item["confidence"]
        library.matched_priority_tags = build_tag_payloads(item["matched_priority_tags"])
        library.evidence_codes = item.get("evidence_codes", [])
        set_reason(library, item["recommendation_reason"] or candidate["fallback_reason"])
        items.append(library)
    return items


def build_personal_result(plan, items, fallback_used, provider_code, mode):
    return {
        "priority_tags": build_priority_tag_payloads(plan.get("priority_tags", [])),
        "fallback_used": fallback_used,
        "provider": provider_code,
        "mode": mode,
        "items": items,
    }


def get_library_feature_tag_codes(library):
    links = getattr(library, "active_tag_links", None)
    if links is None:
        links = library.tag_links.filter(is_active=True).select_related("tag")
    codes = []
    for link in links:
        if link.is_active and link.tag and link.tag.is_active and link.tag.code not in codes:
            codes.append(link.tag.code)
    return codes


def score_plan_tags(library, plan_tag_codes, stat_max):
    return sum(score_preferred_tag(library, tag_code, stat_max) for tag_code in plan_tag_codes)


def build_priority_tag_payloads(priority_tags):
    tag_by_code = get_tag_payload_by_code()
    payloads = []
    for item in priority_tags:
        tag_payload = tag_by_code.get(item["code"])
        if not tag_payload:
            continue
        payloads.append({**tag_payload, "weight": item["weight"]})
    return payloads


def build_tag_payloads(tag_codes):
    tag_by_code = get_tag_payload_by_code()
    return [tag_by_code[code] for code in tag_codes if code in tag_by_code]


def tag_label(tag_code):
    return get_tag_payload_by_code().get(tag_code, {}).get("label", tag_code)


def get_tag_payload_by_code():
    return {
        tag.code: {"code": tag.code, "label": tag.label}
        for tag in Tag.objects.filter(is_active=True)
    }


def get_valid_tag_codes():
    return set(Tag.objects.filter(is_active=True).values_list("code", flat=True))


def get_valid_profile_purpose_codes():
    return set(
        Purpose.objects.filter(is_active=True, is_profile_selectable=True).values_list("code", flat=True)
    )


def score_daily_theme(library, theme_code, stat_max):
    if theme_code == "large_space":
        return normalized_stat(library, "building_area", stat_max) * 0.6 + normalized_stat(library, "site_area", stat_max) * 0.4
    if theme_code == "rich_collection":
        return normalized_stat(library, "book_count", stat_max)
    if theme_code == "mood_space":
        return score_purpose(library, "mood", stat_max, None, None)
    if theme_code == "study_seats":
        return score_purpose(library, "study", stat_max, None, None)
    if theme_code == "family_outing":
        return score_purpose(library, "kids", stat_max, None, None)
    if theme_code == "restful_space":
        return score_facility(library, "has_lounge") * 1.5 + score_purpose(library, "mood", stat_max, None, None)
    return normalized_stat(library, "book_count", stat_max) * 0.5 + normalized_stat(library, "reading_seat_count", stat_max) * 0.5


def score_purpose(library, purpose_code, stat_max, lat=None, lng=None):
    if purpose_code == "study":
        return normalized_stat(library, "reading_seat_count", stat_max) * 2 + score_facility(library, "has_reading_room") * 1.5
    if purpose_code == "book":
        return normalized_stat(library, "book_count", stat_max) * 2
    if purpose_code == "kids":
        library_type_score = 2 if library.library_type == "children" else 0
        return library_type_score + score_facility(library, "has_children_room") * 2
    if purpose_code == "mood":
        return (
            normalized_stat(library, "building_area", stat_max)
            + normalized_stat(library, "site_area", stat_max)
            + score_facility(library, "has_lounge")
            + score_facility(library, "has_cafe") * 0.8
            + score_facility(library, "has_outdoor_space")
        )
    if purpose_code == "nearby":
        if lat is not None and lng is not None and library.latitude is not None and library.longitude is not None:
            return 1 / (1 + distance_km(lat, lng, float(library.latitude), float(library.longitude)))
        return 1 if library.latitude is not None and library.longitude is not None else 0
    return 0


def score_personal(library, purpose_codes, region_values, tag_codes, stat_max):
    score = 0
    if library.sigungu in region_values:
        score += 4
    for purpose_code in purpose_codes:
        if purpose_code == "program":
            continue
        score += score_purpose(library, purpose_code, stat_max, None, None)
    for tag_code in tag_codes:
        score += score_preferred_tag(library, tag_code, stat_max)
    return score


def score_personal_with_behavior(library, purpose_codes, region_values, tag_codes, behavior_tag_scores, stat_max):
    manual_score = score_personal(library, purpose_codes, region_values, tag_codes, stat_max)
    behavior_score = score_behavior_tags(library, behavior_tag_scores)
    return manual_score * MANUAL_PERSONAL_WEIGHT + behavior_score * BEHAVIOR_PERSONAL_WEIGHT


def build_behavior_tag_scores(behavior_items):
    if not behavior_items:
        return {}
    max_score = max(float(item.score or 0) for item in behavior_items)
    if max_score <= 0:
        return {}
    return {
        item.tag_id: float(item.score or 0) / max_score
        for item in behavior_items
        if item.tag_id
    }


def score_behavior_tags(library, behavior_tag_scores):
    if not behavior_tag_scores:
        return 0
    links = getattr(library, "active_tag_links", None)
    if links is None:
        links = library.tag_links.filter(is_active=True).select_related("tag")
    return sum(behavior_tag_scores.get(link.tag_id, 0) for link in links if getattr(link, "is_active", True))


def personal_reason(has_manual_preference, has_behavior_preference):
    if has_manual_preference and has_behavior_preference:
        return "선호 설정과 나들이 활동을 함께 반영했어요."
    if has_behavior_preference:
        return "저장과 후기 활동을 바탕으로 골랐어요."
    return "선호 설정을 바탕으로 골랐어요."


def score_preferred_tag(library, tag_code, stat_max):
    facility_code_map = {
        "facility_reading_room": "has_reading_room",
        "facility_children_room": "has_children_room",
        "facility_digital_room": "has_digital_room",
        "facility_parking": "has_parking",
        "facility_cafe": "has_cafe",
        "facility_wifi": "has_wifi",
        "facility_nursing_room": "has_nursing_room",
        "facility_accessible": "has_accessible_facility",
        "facility_elevator": "has_elevator",
        "facility_lounge": "has_lounge",
        "facility_outdoor_space": "has_outdoor_space",
    }
    library_type_code_map = {
        "public_library": "public",
        "small_library": "small",
        "children_library": "children",
    }
    if tag_code in facility_code_map:
        return score_facility(library, facility_code_map[tag_code]) * 1.5
    if tag_code in library_type_code_map:
        return 1.5 if library.library_type == library_type_code_map[tag_code] else 0
    if tag_code == "many_seats":
        return normalized_stat(library, "reading_seat_count", stat_max)
    if tag_code == "rich_collection":
        return normalized_stat(library, "book_count", stat_max)
    return 0


def rank_libraries(libraries, score_func, limit, reason):
    scored_libraries = []
    for library in libraries:
        score = score_func(library)
        scored_libraries.append((score, library.name, library.id, library))
    scored_libraries.sort(key=lambda item: (-item[0], item[1], item[2]))
    items = []
    for _, _, _, library in scored_libraries[:limit]:
        set_reason(library, reason)
        items.append(library)
    return items


def theme_payload(theme):
    return {
        "code": theme.code,
        "title": theme.label,
        "subtitle": theme.subtitle,
    }


def purpose_payload(purpose):
    return {
        "code": purpose.code,
        "label": purpose.label,
    }


def set_reason(library, reason):
    library.recommendation_reason = reason


def get_current_statistic(library):
    statistics = getattr(library, "current_statistic_snapshots", None)
    if statistics is not None:
        return statistics[0] if statistics else None
    return library.statistic_snapshots.filter(is_current=True).order_by("-reference_date", "-id").first()


def get_facility_profile(library):
    try:
        return library.facility_profile
    except LibraryFacilityProfile.DoesNotExist:
        return None


def score_facility(library, field):
    facility_profile = get_facility_profile(library)
    return 1 if facility_profile and getattr(facility_profile, field) is True else 0


def normalized_stat(library, field, stat_max):
    max_value = stat_max.get(field, 0)
    if max_value <= 0:
        return 0
    statistic = get_current_statistic(library)
    if not statistic:
        return 0
    return number(getattr(statistic, field, 0)) / max_value


def number(value):
    return float(value or 0)


def number_bucket(value):
    if value is None:
        return None
    value = number(value)
    if value <= 0:
        return "none"
    if value < 100:
        return "small"
    if value < 1000:
        return "medium"
    return "large"


def dedupe(values):
    deduped = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def parse_coordinate(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def distance_km(lat1, lng1, lat2, lng2):
    radius_km = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
