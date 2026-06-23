from django.contrib import admin

from .models import (
    Library,
    LibraryAlias,
    LibraryClosureRule,
    LibraryDailySchedule,
    LibraryExternalIdentifier,
    LibraryFacilityProfile,
    LibraryImage,
    LibraryOpeningHour,
    LibraryStatisticSnapshot,
    LibraryTag,
    PublicHoliday,
    PublicHolidayCalendar,
)


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sido", "sigungu", "library_type", "is_active")
    list_filter = ("sido", "sigungu", "library_type", "is_active")
    search_fields = ("name", "normalized_name", "road_address", "normalized_address", "phone")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("sido", "sigungu", "name")


@admin.register(LibraryAlias)
class LibraryAliasAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "alias_name", "sigungu", "alias_type", "provider_code", "is_active")
    list_filter = ("alias_type", "provider_code", "sigungu", "is_active")
    search_fields = ("library__name", "alias_name", "normalized_alias_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("normalized_alias_name", "sigungu")


@admin.register(LibraryExternalIdentifier)
class LibraryExternalIdentifierAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "provider_code", "code_type", "external_code", "is_active")
    list_filter = ("provider_code", "code_type", "is_active")
    search_fields = ("library__name", "external_code", "external_name", "external_address")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("provider_code", "code_type", "external_code")


@admin.register(LibraryOpeningHour)
class LibraryOpeningHourAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "provider_code", "day_type", "day_of_week", "specific_date", "schedule_status", "is_current")
    list_filter = ("provider_code", "day_type", "schedule_status", "is_current")
    search_fields = ("library__name", "provider_code", "raw_text", "source_field")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("library__name", "day_type", "day_of_week", "sequence")


@admin.register(LibraryClosureRule)
class LibraryClosureRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "provider_code", "rule_type", "priority", "is_current", "valid_from", "valid_to")
    list_filter = ("provider_code", "rule_type", "is_current")
    search_fields = ("library__name", "provider_code", "name", "raw_text")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("library__name", "rule_type", "priority")


@admin.register(PublicHolidayCalendar)
class PublicHolidayCalendarAdmin(admin.ModelAdmin):
    list_display = ("id", "year", "provider_code", "is_complete", "synced_month_count", "last_completed_at")
    list_filter = ("provider_code", "is_complete", "year")
    search_fields = ("provider_code",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-year", "provider_code")


@admin.register(PublicHoliday)
class PublicHolidayAdmin(admin.ModelAdmin):
    list_display = ("id", "calendar", "date", "name", "date_kind", "is_public_holiday")
    list_filter = ("calendar__year", "date_kind", "is_public_holiday")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-date", "name")


@admin.register(LibraryDailySchedule)
class LibraryDailyScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "date", "status", "open_time", "close_time", "rule_version")
    list_filter = ("status", "date", "rule_version", "has_source_conflict")
    search_fields = ("library__name", "reason_code", "reason_text")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-date", "library__name")


@admin.register(LibraryStatisticSnapshot)
class LibraryStatisticSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "reference_date", "book_count", "reading_seat_count", "loan_limit_count", "provider_code", "is_current")
    list_filter = ("reference_date", "provider_code", "is_current")
    search_fields = ("library__name", "provider_code")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-reference_date", "library__name")


@admin.register(LibraryFacilityProfile)
class LibraryFacilityProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "has_reading_room", "has_children_room", "has_parking", "has_wifi", "source_name")
    list_filter = ("has_reading_room", "has_children_room", "has_parking", "has_wifi", "source_name")
    search_fields = ("library__name", "source_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("library__name",)


@admin.register(LibraryTag)
class LibraryTagAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "tag", "source_method", "score", "confidence", "is_active")
    list_filter = ("source_method", "is_active", "tag__semantic_kind", "tag__tag_group")
    search_fields = ("library__name", "tag__code", "tag__label", "source_field")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("library__name", "tag__code", "source_method")


@admin.register(LibraryImage)
class LibraryImageAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "media_asset", "image_type", "is_main", "is_active", "display_order")
    list_filter = ("image_type", "is_main", "is_active")
    search_fields = ("library__name", "media_asset__original_url", "caption")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("library__name", "display_order")
