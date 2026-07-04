import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.recommendations.models import Purpose, PurposeTagRule

from .models import (
    ClosureRuleType,
    LibraryDailySchedule,
    LibraryTag,
    LibraryTagSourceMethod,
    PublicHoliday,
    ScheduleDayType,
    ScheduleStatus,
)


FACILITY_FIELDS = (
    "has_reading_room",
    "has_children_room",
    "has_digital_room",
    "has_parking",
    "has_cafe",
    "has_wifi",
    "has_nursing_room",
    "has_accessible_facility",
    "has_elevator",
    "has_lounge",
    "has_outdoor_space",
)

FACILITY_FILTER_PARAMS = set(FACILITY_FIELDS)
FACILITY_TAG_CODES = {
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

SUPPORTED_PURPOSES = {"study", "book", "kids", "mood", "nearby"}
UNSUPPORTED_LIBRARY_FILTERS = {
    "radius_km",
}
OPERATION_FILTER_PARAMS = {"open_today", "open_now", "weekend_open"}
HOLIDAY_STATUS_VALUES = {ScheduleStatus.OPEN, ScheduleStatus.CLOSED, ScheduleStatus.UNKNOWN}
ALLOWED_ORDERING = {"name", "-book_count", "-reading_seat_count", "purpose_score"}

TAG_DIRECT_SOURCES = {
    LibraryTagSourceMethod.FIELD_RULE,
    LibraryTagSourceMethod.FACILITY_RULE,
    LibraryTagSourceMethod.MANUAL,
}


library_tag_prefetch = Prefetch(
    "tag_links",
    queryset=LibraryTag.objects.filter(is_active=True).select_related("tag").order_by("tag_id", "id"),
    to_attr="active_tag_links",
)


def validate_library_filter_params(params):
    unsupported = [param for param in UNSUPPORTED_LIBRARY_FILTERS if param in params]
    if unsupported:
        raise ValidationError({unsupported[0]: "This query parameter is not supported yet."})

    for field in FACILITY_FILTER_PARAMS:
        if field in params and params.get(field) != "true":
            raise ValidationError({field: "Only true facility filters are supported."})

    for field in OPERATION_FILTER_PARAMS:
        if field in params and params.get(field) != "true":
            raise ValidationError({field: "Only true operation filters are supported."})

    if "holiday_date" in params and "holiday_status" not in params:
        raise ValidationError({"holiday_date": "holiday_date requires holiday_status."})
    if "holiday_status" in params:
        validate_holiday_status_params(params)

    parse_non_negative_int(params.get("min_book_count"), "min_book_count")
    parse_non_negative_int(params.get("min_reading_seat_count"), "min_reading_seat_count")
    parse_time_param(params.get("late_open_after"), "late_open_after")

    purpose_code = params.get("purpose", "").strip()
    if purpose_code:
        validate_purpose_code(purpose_code)

    ordering = params.get("ordering", "").strip()
    if ordering:
        if ordering not in ALLOWED_ORDERING:
            raise ValidationError({"ordering": "Unsupported ordering value."})
        if ordering == "purpose_score" and not purpose_code:
            raise ValidationError({"ordering": "purpose_score ordering requires purpose."})

    lat = params.get("lat")
    lng = params.get("lng")
    if lat is not None or lng is not None:
        parse_coordinates(lat, lng)
    if purpose_code == "nearby" and (lat is None or lng is None):
        raise ValidationError({"purpose": "purpose=nearby requires lat and lng."})


def validate_purpose_code(purpose_code):
    if purpose_code not in SUPPORTED_PURPOSES:
        raise ValidationError({"purpose": "Unsupported purpose value."})
    if not Purpose.objects.filter(code=purpose_code, is_home_theme=True, is_active=True).exists():
        raise ValidationError({"purpose": "Unsupported purpose value."})


def parse_non_negative_int(value, field_name):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Enter a non-negative integer."})
    if parsed < 0:
        raise ValidationError({field_name: "Enter a non-negative integer."})
    return parsed


def parse_time_param(value, field_name):
    if value in (None, ""):
        return None
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Enter a valid time in HH:MM format."})


def parse_limit(value, default=3, maximum=10):
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({"limit": "Enter a positive integer."})
    if parsed < 1:
        raise ValidationError({"limit": "Enter a positive integer."})
    return min(parsed, maximum)


def parse_coordinates(lat, lng):
    if lat in (None, "") or lng in (None, ""):
        raise ValidationError({"lat": "lat and lng must be provided together."})
    try:
        parsed_lat = float(lat)
        parsed_lng = float(lng)
    except (TypeError, ValueError):
        raise ValidationError({"lat": "lat and lng must be numeric."})
    if not -90 <= parsed_lat <= 90:
        raise ValidationError({"lat": "Latitude must be between -90 and 90."})
    if not -180 <= parsed_lng <= 180:
        raise ValidationError({"lng": "Longitude must be between -180 and 180."})
    return parsed_lat, parsed_lng


def apply_advanced_library_filters(queryset, params):
    validate_library_filter_params(params)

    for field in FACILITY_FIELDS:
        if params.get(field) == "true":
            # 시설 필터는 미수집(NULL/행 없음)을 False로 단정하지 않고 명시적 True만 통과시킨다.
            queryset = queryset.filter(**{f"facility_profile__{field}": True})

    libraries = list(queryset)
    libraries = filter_by_minimum_statistics(libraries, params)
    libraries = filter_by_operation_status(libraries, params)

    lat_lng = None
    if params.get("lat") is not None or params.get("lng") is not None:
        lat_lng = parse_coordinates(params.get("lat"), params.get("lng"))
        annotate_distance(libraries, lat_lng)

    purpose_code = params.get("purpose", "").strip()
    if purpose_code:
        annotate_purpose_scores(libraries, purpose_code, lat_lng=lat_lng)
        if purpose_code == "nearby":
            libraries = [library for library in libraries if getattr(library, "distance_km", None) is not None]

    return order_libraries(libraries, params, purpose_code)


def filter_by_minimum_statistics(libraries, params):
    min_book_count = parse_non_negative_int(params.get("min_book_count"), "min_book_count")
    min_reading_seat_count = parse_non_negative_int(
        params.get("min_reading_seat_count"),
        "min_reading_seat_count",
    )
    if min_book_count is None and min_reading_seat_count is None:
        return libraries

    filtered = []
    for library in libraries:
        statistic = get_current_statistic(library)
        if min_book_count is not None and (not statistic or statistic.book_count is None or statistic.book_count < min_book_count):
            continue
        if (
            min_reading_seat_count is not None
            and (not statistic or statistic.reading_seat_count is None or statistic.reading_seat_count < min_reading_seat_count)
        ):
            continue
        filtered.append(library)
    return filtered


def order_libraries(libraries, params, purpose_code):
    ordering = params.get("ordering", "").strip()
    if ordering == "-book_count":
        return sorted(libraries, key=lambda library: (get_stat_value(library, "book_count"), library.name, library.id), reverse=True)
    if ordering == "-reading_seat_count":
        return sorted(
            libraries,
            key=lambda library: (get_stat_value(library, "reading_seat_count"), library.name, library.id),
            reverse=True,
        )
    if ordering == "purpose_score":
        return sorted(libraries, key=lambda library: (getattr(library, "purpose_score", 0), library.name, library.id), reverse=True)
    if purpose_code:
        return sorted(libraries, key=lambda library: (getattr(library, "purpose_score", 0), library.name, library.id), reverse=True)
    return sorted(libraries, key=lambda library: (library.name, library.id))


def filter_by_operation_status(libraries, params):
    if params.get("open_today") == "true":
        libraries = [
            library
            for library in libraries
            if resolve_library_operation_status(library)["open_today"] is True
        ]
    if params.get("open_now") == "true":
        libraries = [
            library
            for library in libraries
            if resolve_library_operation_status(library)["open_now"] is True
        ]
    if params.get("weekend_open") == "true":
        libraries = [library for library in libraries if is_weekend_open(library)]
    late_open_after = parse_time_param(params.get("late_open_after"), "late_open_after")
    if late_open_after:
        libraries = [library for library in libraries if is_open_after(library, late_open_after)]
    if params.get("holiday_status"):
        libraries = filter_by_holiday_status(libraries, params)
    return libraries


def resolve_library_operation_status(library, at=None, target_date=None):
    current_at = timezone.localtime(at) if at else timezone.localtime()
    operation_date = target_date or current_at.date()

    daily_schedule = get_daily_schedule_for_date(library, operation_date)
    if daily_schedule:
        return build_operation_payload_from_daily_schedule(
            daily_schedule,
            current_at=current_at,
            operation_date=operation_date,
        )

    closed_reason, reason = resolve_closure_reason(library, operation_date)
    if closed_reason:
        return build_operation_payload(
            open_today=False,
            open_now=False,
            today_hours=None,
            closed_reason=closed_reason,
            operation_status_reason=reason,
        )

    opening_hour = get_opening_hour_for_date(library, operation_date)
    if opening_hour is None:
        return build_operation_payload(
            open_today=None,
            open_now=None,
            today_hours=None,
            closed_reason="operation_unknown",
            operation_status_reason="no_opening_hour_for_date",
        )

    if opening_hour.schedule_status == ScheduleStatus.CLOSED:
        return build_operation_payload(
            open_today=False,
            open_now=False,
            today_hours=None,
            closed_reason="opening_hour_closed",
            operation_status_reason="opening_hour_status_closed",
        )
    if opening_hour.schedule_status != ScheduleStatus.OPEN:
        return build_operation_payload(
            open_today=None,
            open_now=None,
            today_hours=None,
            closed_reason="operation_unknown",
            operation_status_reason="opening_hour_status_unknown",
        )

    today_hours = build_today_hours(opening_hour)
    if today_hours is None:
        return build_operation_payload(
            open_today=True,
            open_now=None,
            today_hours=None,
            closed_reason=None,
            operation_status_reason="opening_hour_without_time",
        )

    open_now = is_open_at(opening_hour, current_at, operation_date) if operation_date == current_at.date() else None
    return build_operation_payload(
        open_today=True,
        open_now=open_now,
        today_hours=today_hours,
        closed_reason=None,
        operation_status_reason="weekly_opening_hour",
    )


def build_operation_payload(open_today, open_now, today_hours, closed_reason, operation_status_reason):
    return {
        "open_today": open_today,
        "open_now": open_now,
        "today_hours": today_hours,
        "closed_reason": closed_reason,
        "operation_status_reason": operation_status_reason,
    }


def build_operation_payload_from_daily_schedule(daily_schedule, *, current_at, operation_date):
    reason_code = daily_schedule.reason_code or "daily_schedule"
    operation_status_reason = f"daily_schedule:{reason_code}"
    if daily_schedule.status == ScheduleStatus.OPEN:
        today_hours = build_today_hours(daily_schedule)
        open_now = is_open_at(daily_schedule, current_at, operation_date) if today_hours and operation_date == current_at.date() else None
        return build_operation_payload(
            open_today=True,
            open_now=open_now,
            today_hours=today_hours,
            closed_reason=None,
            operation_status_reason=operation_status_reason,
        )
    if daily_schedule.status == ScheduleStatus.CLOSED:
        return build_operation_payload(
            open_today=False,
            open_now=False,
            today_hours=None,
            closed_reason=reason_code,
            operation_status_reason=operation_status_reason,
        )
    return build_operation_payload(
        open_today=None,
        open_now=None,
        today_hours=None,
        closed_reason=reason_code,
        operation_status_reason=operation_status_reason,
    )


def get_daily_schedule_for_date(library, operation_date):
    daily_schedules = getattr(library, "prefetched_daily_schedules", None)
    if daily_schedules is not None:
        for daily_schedule in daily_schedules:
            if daily_schedule.date == operation_date:
                return daily_schedule
    return library.daily_schedules.filter(date=operation_date).first()


def resolve_closure_reason(library, operation_date):
    closure_rules = get_current_closure_rules(library)
    for rule in closure_rules:
        if rule.rule_type == ClosureRuleType.FULL_CLOSURE:
            return "full_closure", "closure_rule"
    for rule in closure_rules:
        normalized_rule = rule.normalized_rule or {}
        if rule.rule_type == ClosureRuleType.WEEKLY and normalized_rule.get("day_of_week") == operation_date.weekday():
            return "weekly_closure", "closure_rule"
        if rule.rule_type == ClosureRuleType.NTH_WEEKDAY and matches_nth_weekday_rule(normalized_rule, operation_date):
            return "nth_weekday_closure", "closure_rule"
    return None, None


def matches_nth_weekday_rule(normalized_rule, operation_date):
    if normalized_rule.get("day_of_week") != operation_date.weekday():
        return False
    nth_values = normalized_rule.get("nth") or []
    nth_week = (operation_date.day - 1) // 7 + 1
    return nth_week in nth_values


def get_opening_hour_for_date(library, operation_date):
    opening_hours = get_current_opening_hours(library)
    matching_hours = [
        opening_hour
        for opening_hour in opening_hours
        if opening_hour.day_type == ScheduleDayType.DAY_OF_WEEK
        and opening_hour.day_of_week == operation_date.weekday()
    ]
    return matching_hours[0] if matching_hours else None


def build_today_hours(opening_hour):
    if not opening_hour.open_time or not opening_hour.close_time:
        return None
    if opening_hour.open_time == time(0, 0) and opening_hour.close_time == time(0, 0):
        # 원천의 00:00~00:00은 24시간 운영으로 확정하지 않고 시간 미상으로 둔다.
        return None
    return {
        "open": opening_hour.open_time.strftime("%H:%M"),
        "close": opening_hour.close_time.strftime("%H:%M"),
        "closes_next_day": opening_hour.closes_next_day,
    }


def is_open_at(opening_hour, current_at, operation_date):
    if not opening_hour.open_time or not opening_hour.close_time:
        return None
    if opening_hour.open_time == time(0, 0) and opening_hour.close_time == time(0, 0):
        return None

    opened_at = timezone.make_aware(datetime.combine(operation_date, opening_hour.open_time), current_at.tzinfo)
    closed_date = operation_date + timedelta(days=1) if opening_hour.closes_next_day else operation_date
    closed_at = timezone.make_aware(datetime.combine(closed_date, opening_hour.close_time), current_at.tzinfo)
    return opened_at <= current_at < closed_at


def is_weekend_open(library, at=None):
    current_at = timezone.localtime(at) if at else timezone.localtime()
    today = current_at.date()
    days_until_saturday = (5 - today.weekday()) % 7
    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)
    return any(
        resolve_library_operation_status(library, at=current_at, target_date=date)["open_today"] is True
        for date in (saturday, sunday)
    )


def is_open_after(library, threshold):
    operation_status = resolve_library_operation_status(library)
    if operation_status["open_today"] is not True:
        return False
    today_hours = operation_status.get("today_hours") or {}
    if today_hours.get("closes_next_day"):
        return True
    close_time = parse_time_param(today_hours.get("close"), "late_open_after")
    return close_time is not None and close_time >= threshold


def validate_holiday_status_params(params, at=None):
    holiday_status = params.get("holiday_status")
    if holiday_status not in HOLIDAY_STATUS_VALUES:
        raise ValidationError({"holiday_status": "Unsupported holiday_status value."})
    get_holiday_status_target_date(params, at=at)


def filter_by_holiday_status(libraries, params, at=None):
    holiday_status = params.get("holiday_status")
    target_date = get_holiday_status_target_date(params, at=at)
    filtered = []
    for library in libraries:
        daily_schedule = get_daily_schedule_for_date(library, target_date)
        if daily_schedule and daily_schedule.status == holiday_status:
            filtered.append(library)
    return filtered


def get_holiday_status_target_date(params, at=None):
    holiday_date = params.get("holiday_date")
    if holiday_date:
        target_date = parse_iso_date(holiday_date, "holiday_date")
        if not is_complete_public_holiday(target_date):
            raise ValidationError({"holiday_date": "holiday_date must be a public holiday in a complete calendar."})
        return target_date

    current_at = timezone.localtime(at) if at else timezone.localtime()
    next_holiday = (
        PublicHoliday.objects.filter(
            calendar__is_complete=True,
            is_public_holiday=True,
            date__gte=current_at.date(),
        )
        .order_by("date", "source_seq", "id")
        .first()
    )
    if not next_holiday:
        raise ValidationError({"holiday_status": "No upcoming public holiday is available in a complete calendar."})
    return next_holiday.date


def parse_iso_date(value, field_name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: "Enter a valid date in YYYY-MM-DD format."})


def is_complete_public_holiday(target_date):
    return PublicHoliday.objects.filter(
        calendar__year=target_date.year,
        calendar__is_complete=True,
        is_public_holiday=True,
        date=target_date,
    ).exists()


def collect_operation_prefetch_dates(params=None, at=None):
    current_at = timezone.localtime(at) if at else timezone.localtime()
    dates = {current_at.date()}
    today = current_at.date()
    days_until_saturday = (5 - today.weekday()) % 7
    saturday = today + timedelta(days=days_until_saturday)
    dates.add(saturday)
    dates.add(saturday + timedelta(days=1))
    if params and params.get("holiday_status"):
        dates.add(get_holiday_status_target_date(params, at=current_at))
    return dates


def get_current_opening_hours(library):
    opening_hours = getattr(library, "current_opening_hours", None)
    if opening_hours is not None:
        return opening_hours
    return list(
        library.opening_hours.filter(is_current=True).order_by("day_type", "day_of_week", "specific_date", "sequence", "id")
    )


def get_current_closure_rules(library):
    closure_rules = getattr(library, "current_closure_rules", None)
    if closure_rules is not None:
        return closure_rules
    return list(library.closure_rules.filter(is_current=True).order_by("priority", "id"))


def annotate_distance(libraries, lat_lng):
    for library in libraries:
        library.distance_km = calculate_distance_km(lat_lng[0], lat_lng[1], library.latitude, library.longitude)


def annotate_purpose_scores(libraries, purpose_code, lat_lng=None):
    tag_rule_weights = load_purpose_tag_weights(purpose_code)
    for library in libraries:
        score = calculate_purpose_score(library, purpose_code, tag_rule_weights)
        if lat_lng and purpose_code in {"study", "book", "kids", "mood"}:
            score += calculate_distance_bonus(getattr(library, "distance_km", None)) * Decimal("0.15")
        if purpose_code == "nearby":
            score = calculate_distance_bonus(getattr(library, "distance_km", None))
        library.purpose_score = round_decimal(score)


def load_purpose_tag_weights(purpose_code):
    rules = PurposeTagRule.objects.filter(
        purpose__code=purpose_code,
        purpose__is_home_theme=True,
        purpose__is_active=True,
    ).select_related("tag")
    return {rule.tag_id: Decimal(rule.weight) for rule in rules}


def calculate_purpose_score(library, purpose_code, tag_rule_weights):
    statistic = get_current_statistic(library)
    facilities = get_true_facility_set(library)
    tag_score = calculate_tag_rule_bonus(library, tag_rule_weights)

    if purpose_code == "study":
        score = Decimal("0.45") * normalize_stat(statistic, "reading_seat_count", 500)
        score += Decimal("0.25") * facility_ratio(facilities, {"has_reading_room", "has_digital_room", "has_wifi"})
    elif purpose_code == "book":
        score = Decimal("0.55") * normalize_stat(statistic, "book_count", 100000)
        score += Decimal("0.10") * library_type_bonus(library, {"public"})
    elif purpose_code == "kids":
        score = Decimal("0.35") * facility_ratio(facilities, {"has_children_room", "has_nursing_room", "has_outdoor_space"})
        score += Decimal("0.25") * library_type_bonus(library, {"children"})
    elif purpose_code == "mood":
        score = Decimal("0.35") * facility_ratio(facilities, {"has_lounge", "has_outdoor_space", "has_cafe"})
        score += Decimal("0.15") * normalize_stat(statistic, "building_area", 10000)
    else:
        score = Decimal("0")

    return min(Decimal("1"), score + Decimal("0.20") * tag_score)


def calculate_tag_rule_bonus(library, tag_rule_weights):
    if not tag_rule_weights:
        return Decimal("0")
    matched = Decimal("0")
    total = sum(tag_rule_weights.values(), Decimal("0"))
    for tag_id in get_library_tag_ids(library):
        matched += tag_rule_weights.get(tag_id, Decimal("0"))
    if total <= 0:
        return Decimal("0")
    return min(Decimal("1"), matched / total)


def library_type_bonus(library, matching_types):
    return Decimal("1") if library.library_type in matching_types else Decimal("0")


def normalize_stat(statistic, field_name, cap):
    if not statistic:
        return Decimal("0")
    value = getattr(statistic, field_name, None)
    if value is None:
        return Decimal("0")
    return min(Decimal("1"), Decimal(value) / Decimal(cap))


def facility_ratio(facilities, target_facilities):
    if not target_facilities:
        return Decimal("0")
    return Decimal(len(facilities & target_facilities)) / Decimal(len(target_facilities))


def calculate_distance_bonus(distance_km):
    if distance_km is None:
        return Decimal("0")
    return Decimal("1") / (Decimal("1") + Decimal(str(distance_km)))


def calculate_similar_libraries(base_library, candidates, limit):
    base_facilities = get_true_facility_set(base_library)
    base_tags = get_library_tag_ids(base_library)
    base_purpose_scores = calculate_purpose_vector(base_library)

    scored = []
    for candidate in candidates:
        if candidate.id == base_library.id:
            continue
        score, reasons = calculate_similarity(
            base_library,
            candidate,
            base_facilities,
            base_tags,
            base_purpose_scores,
        )
        if score <= 0:
            continue
        candidate.similarity_score = round_decimal(score)
        candidate.similarity_reasons = reasons
        scored.append(candidate)

    return sorted(scored, key=lambda library: (library.similarity_score, library.name, library.id), reverse=True)[:limit]


def calculate_similarity(base_library, candidate, base_facilities, base_tags, base_purpose_scores):
    candidate_facilities = get_true_facility_set(candidate)
    candidate_tags = get_library_tag_ids(candidate)
    candidate_purpose_scores = calculate_purpose_vector(candidate)

    facility_score = jaccard_score(base_facilities, candidate_facilities)
    tag_score = jaccard_score(base_tags, candidate_tags)
    purpose_score = vector_similarity(base_purpose_scores, candidate_purpose_scores)
    region_type_score = Decimal("0")
    reasons = []

    if base_library.sigungu == candidate.sigungu:
        region_type_score += Decimal("0.60")
        reasons.append("same_sigungu")
    if base_library.library_type == candidate.library_type:
        region_type_score += Decimal("0.40")
        reasons.append("same_library_type")
    if facility_score > 0:
        reasons.append("shared_facilities")
    if tag_score > 0:
        reasons.append("shared_tags")
    if similar_stat(base_library, candidate, "book_count", tolerance=0.25):
        reasons.append("similar_collection")
    if similar_stat(base_library, candidate, "reading_seat_count", tolerance=0.25):
        reasons.append("similar_seats")

    score = (
        Decimal("0.30") * facility_score
        + Decimal("0.30") * tag_score
        + Decimal("0.25") * purpose_score
        + Decimal("0.15") * min(Decimal("1"), region_type_score)
    )
    return score, reasons


def calculate_purpose_vector(library):
    return {
        purpose_code: calculate_purpose_score(library, purpose_code, {})
        for purpose_code in ("study", "book", "kids", "mood")
    }


def jaccard_score(left, right):
    if not left and not right:
        return Decimal("0")
    union = left | right
    if not union:
        return Decimal("0")
    return Decimal(len(left & right)) / Decimal(len(union))


def vector_similarity(left, right):
    distance = sum(abs(left[key] - right[key]) for key in left)
    max_distance = Decimal(len(left))
    if max_distance <= 0:
        return Decimal("0")
    return max(Decimal("0"), Decimal("1") - (distance / max_distance))


def similar_stat(left_library, right_library, field_name, tolerance):
    left = get_stat_value(left_library, field_name)
    right = get_stat_value(right_library, field_name)
    if left <= 0 or right <= 0:
        return False
    return abs(left - right) / max(left, right) <= tolerance


def get_current_statistic(library):
    snapshots = getattr(library, "current_statistic_snapshots", None)
    if snapshots is not None:
        return snapshots[0] if snapshots else None
    return library.statistic_snapshots.filter(is_current=True).order_by("-reference_date", "-id").first()


def get_stat_value(library, field_name):
    statistic = get_current_statistic(library)
    value = getattr(statistic, field_name, None) if statistic else None
    return value or 0


def get_true_facility_set(library):
    try:
        facility_profile = library.facility_profile
    except Exception:
        return set()
    # 유사도와 목적 점수도 시설 미수집과 False를 섞지 않기 위해 True 필드만 사용한다.
    return {field for field in FACILITY_FIELDS if getattr(facility_profile, field) is True}


def get_library_tag_ids(library):
    tag_links = getattr(library, "active_tag_links", None)
    if tag_links is None:
        tag_links = library.tag_links.filter(is_active=True)
    return {tag_link.tag_id for tag_link in tag_links}


def calculate_distance_km(origin_lat, origin_lng, library_lat, library_lng):
    if library_lat is None or library_lng is None:
        return None
    lat1 = math.radians(float(origin_lat))
    lng1 = math.radians(float(origin_lng))
    lat2 = math.radians(float(library_lat))
    lng2 = math.radians(float(library_lng))
    delta_lat = lat2 - lat1
    delta_lng = lng2 - lng1
    haversine = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    distance = 2 * 6371.0088 * math.asin(math.sqrt(haversine))
    return round(distance, 3)


def round_decimal(value):
    return Decimal(value).quantize(Decimal("0.0001"))
