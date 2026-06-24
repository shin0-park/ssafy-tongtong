from dataclasses import dataclass
from datetime import date, timedelta, time

from django.db.models import Prefetch
from django.utils import timezone

from .models import (
    ClosureRuleType,
    Library,
    LibraryClosureRule,
    LibraryDailySchedule,
    LibraryOpeningHour,
    PublicHoliday,
    PublicHolidayCalendar,
    ScheduleDayType,
    ScheduleStatus,
)


DAILY_SCHEDULE_RULE_VERSION = "v1_opening_hour_closure_holiday"


@dataclass
class DailyScheduleBuildStats:
    target_library_count: int
    target_date_count: int
    planned_count: int
    written_count: int
    open_count: int
    closed_count: int
    unknown_count: int
    conflict_count: int
    dry_run: bool


def build_library_daily_schedules(start_date, end_date, *, library_id=None, dry_run=False, batch_size=1000):
    validate_complete_calendars(start_date, end_date)
    dates = list(iter_dates(start_date, end_date))
    holidays_by_date = load_public_holidays(start_date, end_date)
    libraries = list(load_libraries(library_id=library_id))

    schedules = []
    status_counts = {
        ScheduleStatus.OPEN: 0,
        ScheduleStatus.CLOSED: 0,
        ScheduleStatus.UNKNOWN: 0,
    }
    conflict_count = 0
    generated_at = timezone.now()

    for library in libraries:
        for target_date in dates:
            schedule = calculate_daily_schedule(
                library,
                target_date,
                holidays=holidays_by_date.get(target_date, []),
                generated_at=generated_at,
            )
            schedules.append(schedule)
            status_counts[schedule.status] += 1
            if schedule.has_source_conflict:
                conflict_count += 1

    if not dry_run and schedules:
        LibraryDailySchedule.objects.bulk_create(
            schedules,
            batch_size=batch_size,
            update_conflicts=True,
            update_fields=[
                "status",
                "open_time",
                "close_time",
                "closes_next_day",
                "reason_code",
                "reason_text",
                "calculation_basis",
                "has_source_conflict",
                "rule_version",
                "generated_at",
                "updated_at",
            ],
            unique_fields=["library", "date"],
        )

    return DailyScheduleBuildStats(
        target_library_count=len(libraries),
        target_date_count=len(dates),
        planned_count=len(schedules),
        written_count=0 if dry_run else len(schedules),
        open_count=status_counts[ScheduleStatus.OPEN],
        closed_count=status_counts[ScheduleStatus.CLOSED],
        unknown_count=status_counts[ScheduleStatus.UNKNOWN],
        conflict_count=conflict_count,
        dry_run=dry_run,
    )


def calculate_daily_schedule(library, target_date, *, holidays, generated_at):
    is_public_holiday = bool(holidays)
    closure_rules = get_matching_closure_rules(library, target_date, holidays)
    opening_resolution = resolve_opening_hour(library, target_date, is_public_holiday=is_public_holiday)
    closure_resolution = resolve_closure(closure_rules, is_public_holiday=is_public_holiday)

    if closure_resolution["reason_code"] == "full_closure":
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.CLOSED,
            reason_code="full_closure",
            reason_text="Full closure rule applies.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            has_source_conflict=False,
            generated_at=generated_at,
        )

    if opening_resolution["has_conflict"] or closure_resolution["has_conflict"]:
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.UNKNOWN,
            reason_code="source_conflict",
            reason_text="Multiple source rules conflict.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            has_source_conflict=True,
            generated_at=generated_at,
        )

    opening_hour = opening_resolution["opening_hour"]
    closure_status = closure_resolution["status"]
    if closure_status == ScheduleStatus.CLOSED and opening_hour and opening_hour.schedule_status == ScheduleStatus.OPEN:
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.UNKNOWN,
            reason_code="source_conflict",
            reason_text="Opening hour and closure rule conflict.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            has_source_conflict=True,
            generated_at=generated_at,
        )

    if closure_status == ScheduleStatus.CLOSED:
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.CLOSED,
            reason_code=closure_resolution["reason_code"],
            reason_text="Closure rule applies.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            generated_at=generated_at,
        )

    if closure_status == ScheduleStatus.UNKNOWN:
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.UNKNOWN,
            reason_code=closure_resolution["reason_code"],
            reason_text="Closure rule is ambiguous.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            generated_at=generated_at,
        )

    if opening_hour is None:
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.UNKNOWN,
            reason_code=opening_resolution["reason_code"],
            reason_text="No matching opening hour rule.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            generated_at=generated_at,
        )

    if opening_hour.schedule_status == ScheduleStatus.CLOSED:
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.CLOSED,
            reason_code="opening_hour_closed",
            reason_text="Opening hour rule is closed.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            generated_at=generated_at,
        )

    if opening_hour.schedule_status != ScheduleStatus.OPEN:
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.UNKNOWN,
            reason_code="opening_hour_unknown",
            reason_text="Opening hour rule is unknown.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            generated_at=generated_at,
        )

    if opening_hour.open_time == time(0, 0) and opening_hour.close_time == time(0, 0):
        return build_schedule(
            library,
            target_date,
            ScheduleStatus.UNKNOWN,
            reason_code="zero_time_unknown",
            reason_text="00:00~00:00 is not treated as 24-hour open.",
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
            generated_at=generated_at,
        )

    return build_schedule(
        library,
        target_date,
        ScheduleStatus.OPEN,
        open_time=opening_hour.open_time,
        close_time=opening_hour.close_time,
        closes_next_day=opening_hour.closes_next_day,
        reason_code=opening_resolution["reason_code"],
        reason_text="Opening hour rule applies.",
        holidays=holidays,
        opening_resolution=opening_resolution,
        closure_resolution=closure_resolution,
        generated_at=generated_at,
    )


def resolve_opening_hour(library, target_date, *, is_public_holiday):
    opening_hours = get_current_opening_hours(library)
    if is_public_holiday:
        candidates = [
            opening_hour
            for opening_hour in opening_hours
            if opening_hour.day_type == ScheduleDayType.PUBLIC_HOLIDAY
            and is_rule_valid_for_date(opening_hour, target_date)
        ]
        reason_code = "public_holiday_opening_hour"
        missing_reason_code = "no_public_holiday_opening_hour"
    else:
        specific_candidates = [
            opening_hour
            for opening_hour in opening_hours
            if opening_hour.day_type == ScheduleDayType.SPECIFIC_DATE
            and opening_hour.specific_date == target_date
            and is_rule_valid_for_date(opening_hour, target_date)
        ]
        if specific_candidates:
            candidates = specific_candidates
            reason_code = "specific_date_opening_hour"
        else:
            candidates = [
                opening_hour
                for opening_hour in opening_hours
                if opening_hour.day_type == ScheduleDayType.DAY_OF_WEEK
                and opening_hour.day_of_week == target_date.weekday()
                and is_rule_valid_for_date(opening_hour, target_date)
            ]
            reason_code = "weekday_opening_hour"
        missing_reason_code = "no_matching_opening_hour"

    normalized = dedupe_opening_hours(candidates)
    if not normalized:
        return {
            "opening_hour": None,
            "reason_code": missing_reason_code,
            "has_conflict": False,
            "rule_ids": [],
        }
    if len(normalized) > 1:
        return {
            "opening_hour": None,
            "reason_code": "multiple_opening_hours_conflict",
            "has_conflict": True,
            "rule_ids": [opening_hour.id for opening_hour in candidates],
        }
    return {
        "opening_hour": normalized[0],
        "reason_code": reason_code,
        "has_conflict": False,
        "rule_ids": [opening_hour.id for opening_hour in candidates],
    }


def resolve_closure(closure_rules, *, is_public_holiday):
    if not closure_rules:
        return {
            "status": None,
            "reason_code": None,
            "has_conflict": False,
            "rule_ids": [],
        }

    full_closure_rules = [rule for rule in closure_rules if rule.rule_type == ClosureRuleType.FULL_CLOSURE]
    if full_closure_rules:
        return {
            "status": ScheduleStatus.CLOSED,
            "reason_code": "full_closure",
            "has_conflict": False,
            "rule_ids": [rule.id for rule in full_closure_rules],
        }

    unknown_rules = [rule for rule in closure_rules if rule.rule_type == ClosureRuleType.UNKNOWN]
    strong_unknown_rules = [
        rule for rule in unknown_rules if not (rule.normalized_rule or {}).get("always_open")
    ]
    if strong_unknown_rules:
        return {
            "status": ScheduleStatus.UNKNOWN,
            "reason_code": "unknown_closure_rule",
            "has_conflict": False,
            "rule_ids": [rule.id for rule in strong_unknown_rules],
        }

    closed_rules = [
        rule
        for rule in closure_rules
        if rule.rule_type
        in {
            ClosureRuleType.WEEKLY,
            ClosureRuleType.NTH_WEEKDAY,
            ClosureRuleType.PUBLIC_HOLIDAY,
            ClosureRuleType.NAMED_HOLIDAY,
            ClosureRuleType.TEMPORARY,
        }
    ]
    if not closed_rules:
        return {
            "status": None,
            "reason_code": None,
            "has_conflict": False,
            "rule_ids": [],
        }
    if is_public_holiday and any(rule.rule_type == ClosureRuleType.PUBLIC_HOLIDAY for rule in closed_rules):
        reason_code = "public_holiday_closure"
    elif any(rule.rule_type == ClosureRuleType.NAMED_HOLIDAY for rule in closed_rules):
        reason_code = "named_holiday_closure"
    elif any(rule.rule_type == ClosureRuleType.TEMPORARY for rule in closed_rules):
        reason_code = "temporary_closure"
    elif any(rule.rule_type == ClosureRuleType.NTH_WEEKDAY for rule in closed_rules):
        reason_code = "nth_weekday_closure"
    else:
        reason_code = "weekly_closure"
    return {
        "status": ScheduleStatus.CLOSED,
        "reason_code": reason_code,
        "has_conflict": False,
        "rule_ids": [rule.id for rule in closed_rules],
    }


def get_matching_closure_rules(library, target_date, holidays):
    holidays = holidays or []
    holiday_names = {holiday.name for holiday in holidays}
    is_public_holiday = bool(holidays)
    matching_rules = []
    for rule in get_current_closure_rules(library):
        if not is_rule_valid_for_date(rule, target_date):
            continue
        normalized_rule = rule.normalized_rule or {}
        if rule.rule_type in {ClosureRuleType.FULL_CLOSURE, ClosureRuleType.UNKNOWN}:
            matching_rules.append(rule)
        elif rule.rule_type == ClosureRuleType.TEMPORARY:
            matching_rules.append(rule)
        elif rule.rule_type == ClosureRuleType.WEEKLY and normalized_rule.get("day_of_week") == target_date.weekday():
            matching_rules.append(rule)
        elif rule.rule_type == ClosureRuleType.NTH_WEEKDAY and matches_nth_weekday_rule(normalized_rule, target_date):
            matching_rules.append(rule)
        elif rule.rule_type == ClosureRuleType.PUBLIC_HOLIDAY and is_public_holiday:
            matching_rules.append(rule)
        elif rule.rule_type == ClosureRuleType.NAMED_HOLIDAY and matches_named_holiday_rule(normalized_rule, holiday_names):
            matching_rules.append(rule)
    return matching_rules


def build_schedule(
    library,
    target_date,
    status,
    *,
    open_time=None,
    close_time=None,
    closes_next_day=False,
    reason_code,
    reason_text,
    holidays,
    opening_resolution,
    closure_resolution,
    has_source_conflict=False,
    generated_at,
):
    if status != ScheduleStatus.OPEN:
        open_time = None
        close_time = None
        closes_next_day = False
    return LibraryDailySchedule(
        library=library,
        date=target_date,
        status=status,
        open_time=open_time,
        close_time=close_time,
        closes_next_day=closes_next_day,
        reason_code=reason_code,
        reason_text=reason_text,
        calculation_basis=build_calculation_basis(
            holidays=holidays,
            opening_resolution=opening_resolution,
            closure_resolution=closure_resolution,
        ),
        has_source_conflict=has_source_conflict,
        rule_version=DAILY_SCHEDULE_RULE_VERSION,
        generated_at=generated_at,
    )


def build_calculation_basis(*, holidays, opening_resolution, closure_resolution):
    opening_hour = opening_resolution.get("opening_hour")
    return {
        "rule_version": DAILY_SCHEDULE_RULE_VERSION,
        "holiday": [
            {
                "id": holiday.id,
                "date": holiday.date.isoformat(),
                "name": holiday.name,
                "source_seq": holiday.source_seq,
            }
            for holiday in holidays
        ],
        "opening": {
            "rule_ids": opening_resolution.get("rule_ids", []),
            "selected_rule_id": opening_hour.id if opening_hour else None,
            "reason_code": opening_resolution.get("reason_code"),
        },
        "closure": {
            "rule_ids": closure_resolution.get("rule_ids", []),
            "reason_code": closure_resolution.get("reason_code"),
        },
    }


def dedupe_opening_hours(opening_hours):
    deduped = {}
    for opening_hour in opening_hours:
        key = (
            opening_hour.schedule_status,
            opening_hour.open_time,
            opening_hour.close_time,
            opening_hour.closes_next_day,
        )
        deduped.setdefault(key, opening_hour)
    return list(deduped.values())


def matches_nth_weekday_rule(normalized_rule, target_date):
    if normalized_rule.get("day_of_week") != target_date.weekday():
        return False
    nth_values = normalized_rule.get("nth") or []
    nth_week = (target_date.day - 1) // 7 + 1
    return nth_week in nth_values


def matches_named_holiday_rule(normalized_rule, holiday_names):
    names = set(normalized_rule.get("names") or [])
    return bool(names & holiday_names)


def is_rule_valid_for_date(rule, target_date):
    if rule.valid_from and target_date < rule.valid_from:
        return False
    if rule.valid_to and target_date > rule.valid_to:
        return False
    return True


def load_libraries(*, library_id=None):
    queryset = Library.objects.filter(is_active=True).order_by("id")
    if library_id is not None:
        queryset = queryset.filter(id=library_id)
    return queryset.prefetch_related(
        Prefetch(
            "opening_hours",
            queryset=LibraryOpeningHour.objects.filter(is_current=True).order_by(
                "day_type",
                "day_of_week",
                "specific_date",
                "sequence",
                "id",
            ),
            to_attr="current_opening_hours",
        ),
        Prefetch(
            "closure_rules",
            queryset=LibraryClosureRule.objects.filter(is_current=True).order_by("priority", "id"),
            to_attr="current_closure_rules",
        ),
    )


def load_public_holidays(start_date, end_date):
    calendars = PublicHolidayCalendar.objects.filter(
        year__in=get_years(start_date, end_date),
        is_complete=True,
    )
    calendar_ids = list(calendars.values_list("id", flat=True))
    holidays = PublicHoliday.objects.filter(
        calendar_id__in=calendar_ids,
        is_public_holiday=True,
        date__gte=start_date,
        date__lte=end_date,
    ).order_by("date", "source_seq", "id")
    holidays_by_date = {}
    for holiday in holidays:
        holidays_by_date.setdefault(holiday.date, []).append(holiday)
    return holidays_by_date


def validate_complete_calendars(start_date, end_date):
    years = get_years(start_date, end_date)
    complete_years = set(
        PublicHolidayCalendar.objects.filter(year__in=years, is_complete=True).values_list("year", flat=True)
    )
    missing_years = sorted(set(years) - complete_years)
    if missing_years:
        raise ValueError(
            "Complete public holiday calendar is required for year(s): "
            + ", ".join(str(year) for year in missing_years)
        )


def get_years(start_date, end_date):
    return list(range(start_date.year, end_date.year + 1))


def iter_dates(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def get_current_opening_hours(library):
    opening_hours = getattr(library, "current_opening_hours", None)
    if opening_hours is not None:
        return opening_hours
    return list(library.opening_hours.filter(is_current=True))


def get_current_closure_rules(library):
    closure_rules = getattr(library, "current_closure_rules", None)
    if closure_rules is not None:
        return closure_rules
    return list(library.closure_rules.filter(is_current=True).order_by("priority", "id"))
