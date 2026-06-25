import hashlib

from django.db.models import Q
from django.templatetags.static import static
from rest_framework import serializers

from .models import (
    Library,
    LibraryClosureRule,
    LibraryFacilityProfile,
    LibraryImage,
    LibraryOpeningHour,
    LibraryStatisticSnapshot,
)
from .services import get_daily_schedule_for_date, resolve_library_operation_status


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

LIBRARY_PLACEHOLDER_IMAGES = (
    "media_assets/placeholders/default_library_public.png",
    "media_assets/placeholders/default_library_small.png",
    "media_assets/placeholders/default_library_children.png",
    "media_assets/placeholders/libraries/library_fallback_01.png",
    "media_assets/placeholders/libraries/library_fallback_02.png",
    "media_assets/placeholders/libraries/library_fallback_03.png",
    "media_assets/placeholders/libraries/library_fallback_04.png",
    "media_assets/placeholders/libraries/library_fallback_05.png",
    "media_assets/placeholders/libraries/library_fallback_06.png",
    "media_assets/placeholders/libraries/library_fallback_07.png",
    "media_assets/placeholders/libraries/library_fallback_08.png",
    "media_assets/placeholders/libraries/library_fallback_09.png",
    "media_assets/placeholders/libraries/library_fallback_10.png",
    "media_assets/placeholders/libraries/library_fallback_11.png",
    "media_assets/placeholders/libraries/library_fallback_12.png",
    "media_assets/placeholders/libraries/library_fallback_13.png",
    "media_assets/placeholders/libraries/library_fallback_14.png",
    "media_assets/placeholders/libraries/library_fallback_15.png",
    "media_assets/placeholders/libraries/library_fallback_16.png",
    "media_assets/placeholders/libraries/library_fallback_17.png",
    "media_assets/placeholders/libraries/library_fallback_18.png",
    "media_assets/placeholders/libraries/library_fallback_19.png",
    "media_assets/placeholders/libraries/library_fallback_20.png",
)


def get_prefetched_first(instance, attr_name, fallback_queryset):
    prefetched = getattr(instance, attr_name, None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None
    return fallback_queryset.first()


def get_current_statistic(library):
    return get_prefetched_first(
        library,
        "current_statistic_snapshots",
        library.statistic_snapshots.filter(is_current=True).order_by("-reference_date", "-id"),
    )


def library_thumbnail_image_queryset(queryset):
    return (
        queryset.filter(media_asset__is_active=True)
        .filter(Q(media_asset__original_url__gt="") | Q(media_asset__file__gt=""))
        .select_related("media_asset")
        .order_by("-is_active", "-is_main", "display_order", "id")
    )


def get_library_thumbnail_images(library):
    prefetched = getattr(library, "thumbnail_images", None)
    if prefetched is not None:
        return prefetched
    return library_thumbnail_image_queryset(library.images.all())


def resolve_media_asset_payload(media_asset):
    if not media_asset or not media_asset.is_active:
        return None

    image_url = media_asset.original_url
    if not image_url and media_asset.file:
        try:
            image_url = media_asset.file.url
        except ValueError:
            image_url = ""

    if not image_url:
        return None

    return {
        "url": image_url,
        "is_fallback": False,
        "fallback_key": None,
        "license_code": media_asset.license_code or None,
        "attribution_text": media_asset.attribution_text or None,
    }


def resolve_library_placeholder_payload(library):
    seed = str(library.id or library.normalized_name or library.name)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    placeholder_index = int(digest, 16) % len(LIBRARY_PLACEHOLDER_IMAGES)
    return {
        "url": static(LIBRARY_PLACEHOLDER_IMAGES[placeholder_index]),
        "is_fallback": True,
        "fallback_key": f"library/random/{placeholder_index + 1:02d}",
        "license_code": "internal",
        "attribution_text": None,
    }


def resolve_library_thumbnail_payload(library):
    for image in get_library_thumbnail_images(library):
        media_asset_payload = resolve_media_asset_payload(image.media_asset)
        if media_asset_payload:
            return media_asset_payload
    return resolve_library_placeholder_payload(library)


class LibraryStatisticSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryStatisticSnapshot
        fields = ("book_count", "reading_seat_count")


class LibraryStatisticDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryStatisticSnapshot
        fields = (
            "reference_date",
            "reading_seat_count",
            "book_count",
            "serial_count",
            "non_book_count",
            "loan_limit_count",
            "loan_period_days",
            "site_area",
            "building_area",
        )


class LibraryFacilityProfileSerializer(serializers.ModelSerializer):
    confirmed_facilities = serializers.SerializerMethodField()

    class Meta:
        model = LibraryFacilityProfile
        fields = (*FACILITY_FIELDS, "confirmed_facilities")

    def get_confirmed_facilities(self, obj):
        return [field for field in FACILITY_FIELDS if getattr(obj, field) is True]


class LibraryOpeningHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryOpeningHour
        fields = (
            "day_type",
            "day_of_week",
            "specific_date",
            "sequence",
            "schedule_status",
            "open_time",
            "close_time",
            "closes_next_day",
            "raw_text",
        )


class LibraryClosureRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryClosureRule
        fields = ("rule_type", "normalized_rule", "raw_text", "priority")


class LibraryListSerializer(serializers.ModelSerializer):
    book_count = serializers.SerializerMethodField()
    reading_seat_count = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    purpose_score = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    open_today = serializers.SerializerMethodField()
    open_now = serializers.SerializerMethodField()
    today_hours = serializers.SerializerMethodField()
    closed_reason = serializers.SerializerMethodField()
    operation_status_reason = serializers.SerializerMethodField()

    class Meta:
        model = Library
        fields = (
            "id",
            "name",
            "library_type",
            "sido",
            "sigungu",
            "road_address",
            "latitude",
            "longitude",
            "book_count",
            "reading_seat_count",
            "thumbnail",
            "purpose_score",
            "distance_km",
            "open_today",
            "open_now",
            "today_hours",
            "closed_reason",
            "operation_status_reason",
        )

    def get_book_count(self, obj):
        statistic = get_current_statistic(obj)
        return statistic.book_count if statistic else None

    def get_reading_seat_count(self, obj):
        statistic = get_current_statistic(obj)
        return statistic.reading_seat_count if statistic else None

    def get_thumbnail(self, obj):
        return resolve_library_thumbnail_payload(obj)

    def get_purpose_score(self, obj):
        purpose_score = getattr(obj, "purpose_score", None)
        return str(purpose_score) if purpose_score is not None else None

    def get_distance_km(self, obj):
        return getattr(obj, "distance_km", None)

    def get_operation_status(self, obj):
        operation_status = getattr(obj, "_operation_status", None)
        if operation_status is None:
            operation_status = resolve_library_operation_status(obj)
            obj._operation_status = operation_status
        return operation_status

    def get_open_today(self, obj):
        return self.get_operation_status(obj)["open_today"]

    def get_open_now(self, obj):
        return self.get_operation_status(obj)["open_now"]

    def get_today_hours(self, obj):
        return self.get_operation_status(obj)["today_hours"]

    def get_closed_reason(self, obj):
        return self.get_operation_status(obj)["closed_reason"]

    def get_operation_status_reason(self, obj):
        return self.get_operation_status(obj)["operation_status_reason"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        holiday_operation_date = self.context.get("holiday_operation_date")
        if holiday_operation_date:
            data["holiday_operation_status"] = self.get_holiday_operation_status(instance, holiday_operation_date)
        return data

    def get_holiday_operation_status(self, obj, holiday_operation_date):
        daily_schedule = get_daily_schedule_for_date(obj, holiday_operation_date)
        if not daily_schedule:
            return None
        return {
            "date": daily_schedule.date.isoformat(),
            "status": daily_schedule.status,
            "open_time": daily_schedule.open_time.strftime("%H:%M") if daily_schedule.open_time else None,
            "close_time": daily_schedule.close_time.strftime("%H:%M") if daily_schedule.close_time else None,
            "closes_next_day": daily_schedule.closes_next_day,
            "reason_code": daily_schedule.reason_code or None,
        }


class LibraryDetailSerializer(LibraryListSerializer):
    statistics = serializers.SerializerMethodField()
    facility_profile = serializers.SerializerMethodField()
    opening_hours = serializers.SerializerMethodField()
    closure_rules = serializers.SerializerMethodField()

    class Meta(LibraryListSerializer.Meta):
        fields = LibraryListSerializer.Meta.fields + (
            "phone",
            "homepage_url",
            "operating_agency",
            "short_description",
            "statistics",
            "facility_profile",
            "opening_hours",
            "closure_rules",
        )

    def get_statistics(self, obj):
        statistic = get_current_statistic(obj)
        if not statistic:
            return None
        return LibraryStatisticDetailSerializer(statistic).data

    def get_facility_profile(self, obj):
        try:
            facility_profile = obj.facility_profile
        except LibraryFacilityProfile.DoesNotExist:
            return None
        return LibraryFacilityProfileSerializer(facility_profile).data

    def get_opening_hours(self, obj):
        opening_hours = getattr(obj, "current_opening_hours", None)
        if opening_hours is None:
            opening_hours = obj.opening_hours.filter(is_current=True).order_by("day_type", "day_of_week", "specific_date", "sequence", "id")
        return LibraryOpeningHourSerializer(opening_hours, many=True).data

    def get_closure_rules(self, obj):
        closure_rules = getattr(obj, "current_closure_rules", None)
        if closure_rules is None:
            closure_rules = obj.closure_rules.filter(is_current=True).order_by("priority", "id")
        return LibraryClosureRuleSerializer(closure_rules, many=True).data


class SimilarLibrarySerializer(LibraryListSerializer):
    similarity_score = serializers.SerializerMethodField()
    similarity_reasons = serializers.SerializerMethodField()

    class Meta(LibraryListSerializer.Meta):
        fields = LibraryListSerializer.Meta.fields + (
            "similarity_score",
            "similarity_reasons",
        )

    def get_similarity_score(self, obj):
        similarity_score = getattr(obj, "similarity_score", None)
        return str(similarity_score) if similarity_score is not None else None

    def get_similarity_reasons(self, obj):
        return getattr(obj, "similarity_reasons", [])
