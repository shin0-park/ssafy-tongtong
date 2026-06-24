from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.integrations.models import SourceSyncRun, SourceSyncStatus, SourceType
from apps.integrations.public_holidays import (
    PublicHolidayAPIError,
    PublicHolidayClient,
    PublicHolidayConfigurationError,
)

from .models import PublicHoliday, PublicHolidayCalendar


PUBLIC_HOLIDAY_PROVIDER_CODE = "data_go_kr"
PUBLIC_HOLIDAY_SOURCE_NAME = "data_go_kr_public_holidays"
PUBLIC_HOLIDAY_TARGET_DOMAIN = "public_holidays"


@dataclass
class PublicHolidayYearSyncResult:
    year: int
    is_complete: bool
    synced_month_count: int
    holiday_count: int
    created_count: int
    updated_count: int
    deleted_count: int
    failed_months: dict
    sync_run_id: int | None


def sync_public_holiday_year(year, *, client=None):
    sync_run = create_sync_run(year)
    fetched_items = []
    failed_months = {}
    now = timezone.now()

    try:
        holiday_client = client or PublicHolidayClient()
        for month in range(1, 13):
            try:
                fetched_items.extend(holiday_client.fetch_month(year, month))
            except (PublicHolidayConfigurationError, PublicHolidayAPIError, ValueError) as exc:
                failed_months[month] = build_safe_error_summary(exc)
    except Exception as exc:
        failed_months = {month: build_safe_error_summary(exc) for month in range(1, 13)}

    synced_month_count = 12 - len(failed_months)
    is_complete = synced_month_count == 12

    if is_complete:
        result_counts = upsert_complete_year(year, fetched_items, now=now)
    else:
        mark_incomplete_year(year, synced_month_count, now=now)
        result_counts = {
            "created_count": 0,
            "updated_count": 0,
            "deleted_count": 0,
        }

    finish_sync_run(
        sync_run,
        is_complete=is_complete,
        synced_month_count=synced_month_count,
        holiday_count=len(fetched_items),
        failed_months=failed_months,
        result_counts=result_counts,
    )

    return PublicHolidayYearSyncResult(
        year=year,
        is_complete=is_complete,
        synced_month_count=synced_month_count,
        holiday_count=len(fetched_items),
        failed_months=failed_months,
        sync_run_id=sync_run.id,
        **result_counts,
    )


def create_sync_run(year):
    return SourceSyncRun.objects.create(
        source_name=PUBLIC_HOLIDAY_SOURCE_NAME,
        source_type=SourceType.API,
        target_domain=PUBLIC_HOLIDAY_TARGET_DOMAIN,
        target_year=year,
        parameters={
            "year": year,
            "months": list(range(1, 13)),
            "provider_code": PUBLIC_HOLIDAY_PROVIDER_CODE,
            "api_base_url": settings.PUBLIC_HOLIDAY_API_BASE_URL,
            "api_operation": settings.PUBLIC_HOLIDAY_API_OPERATION,
            "num_of_rows": settings.PUBLIC_HOLIDAY_API_NUM_OF_ROWS,
        },
    )


@transaction.atomic
def upsert_complete_year(year, holiday_items, *, now):
    calendar, _ = PublicHolidayCalendar.objects.select_for_update().get_or_create(
        year=year,
        defaults={
            "provider_code": PUBLIC_HOLIDAY_PROVIDER_CODE,
            "is_complete": False,
            "synced_month_count": 0,
        },
    )
    calendar.provider_code = PUBLIC_HOLIDAY_PROVIDER_CODE
    calendar.is_complete = True
    calendar.synced_month_count = 12
    calendar.last_attempted_at = now
    calendar.last_completed_at = now
    calendar.save(
        update_fields=[
            "provider_code",
            "is_complete",
            "synced_month_count",
            "last_attempted_at",
            "last_completed_at",
            "updated_at",
        ]
    )

    created_count = 0
    updated_count = 0
    kept_ids = []
    for item in dedupe_holiday_items(holiday_items):
        holiday, created = PublicHoliday.objects.update_or_create(
            calendar=calendar,
            date=item.date,
            source_seq=item.source_seq,
            defaults={
                "date_kind": item.date_kind,
                "name": item.name,
                "holiday_code": item.holiday_code,
                "is_public_holiday": item.is_public_holiday,
                "fetched_at": now,
            },
        )
        kept_ids.append(holiday.id)
        if created:
            created_count += 1
        else:
            updated_count += 1

    stale_queryset = PublicHoliday.objects.filter(calendar=calendar)
    if kept_ids:
        stale_queryset = stale_queryset.exclude(id__in=kept_ids)
    deleted_count, _ = stale_queryset.delete()

    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "deleted_count": deleted_count,
    }


@transaction.atomic
def mark_incomplete_year(year, synced_month_count, *, now):
    calendar, _ = PublicHolidayCalendar.objects.select_for_update().get_or_create(
        year=year,
        defaults={
            "provider_code": PUBLIC_HOLIDAY_PROVIDER_CODE,
            "is_complete": False,
            "synced_month_count": 0,
        },
    )
    calendar.provider_code = PUBLIC_HOLIDAY_PROVIDER_CODE
    calendar.is_complete = False
    calendar.synced_month_count = synced_month_count
    calendar.last_attempted_at = now
    calendar.save(
        update_fields=[
            "provider_code",
            "is_complete",
            "synced_month_count",
            "last_attempted_at",
            "updated_at",
        ]
    )


def dedupe_holiday_items(holiday_items):
    deduped = {}
    for item in holiday_items:
        deduped[(item.date, item.source_seq)] = item
    return sorted(deduped.values(), key=lambda item: (item.date, item.source_seq))


def finish_sync_run(sync_run, *, is_complete, synced_month_count, holiday_count, failed_months, result_counts):
    if is_complete:
        status = SourceSyncStatus.SUCCESS
    elif synced_month_count > 0:
        status = SourceSyncStatus.PARTIAL
    else:
        status = SourceSyncStatus.FAILED

    sync_run.status = status
    sync_run.finished_at = timezone.now()
    sync_run.total_count = 12
    sync_run.success_count = synced_month_count
    sync_run.failure_count = len(failed_months)
    sync_run.summary = {
        "is_complete": is_complete,
        "synced_month_count": synced_month_count,
        "holiday_count": holiday_count,
        "created_count": result_counts["created_count"],
        "updated_count": result_counts["updated_count"],
        "deleted_count": result_counts["deleted_count"],
        "failed_months": {
            str(month): error_summary for month, error_summary in sorted(failed_months.items())
        },
    }
    sync_run.error_message = build_error_message(failed_months)
    sync_run.save(
        update_fields=[
            "status",
            "finished_at",
            "total_count",
            "success_count",
            "failure_count",
            "summary",
            "error_message",
        ]
    )


def build_safe_error_summary(exc):
    summary = {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }
    request_preview = getattr(exc, "request_preview", None)
    if request_preview:
        summary["request_preview"] = request_preview
    status_code = getattr(exc, "status_code", None)
    if status_code:
        summary["status_code"] = status_code
    reason = getattr(exc, "reason", None)
    if reason:
        summary["reason"] = reason
    body_preview = getattr(exc, "body_preview", None)
    if body_preview:
        summary["body_preview"] = body_preview
    return summary


def build_error_message(failed_months):
    if not failed_months:
        return ""
    months = ", ".join(f"{month:02d}" for month in sorted(failed_months))
    return f"Public holiday sync failed for month(s): {months}"
