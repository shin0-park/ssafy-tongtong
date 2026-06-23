from django.contrib import admin

from .models import (
    DailyLibraryRecommendationItem,
    DailyLibraryRecommendationSet,
    DailyRecommendationMetricRule,
    DailyRecommendationTagRule,
    DailyRecommendationTheme,
    Purpose,
    PurposeMetricRule,
    PurposeTagRule,
)


@admin.register(Purpose)
class PurposeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "label", "is_home_theme", "is_profile_selectable", "analysis_axis", "display_order", "is_active")
    list_filter = ("is_home_theme", "is_profile_selectable", "analysis_axis", "requires_location", "is_active")
    search_fields = ("code", "label", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("display_order", "code")


@admin.register(PurposeTagRule)
class PurposeTagRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "purpose", "tag", "source_scope", "weight", "is_required")
    list_filter = ("source_scope", "is_required", "tag__semantic_kind", "tag__tag_group")
    search_fields = ("purpose__code", "purpose__label", "tag__code", "tag__label")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("purpose__code", "source_scope", "tag__code")


@admin.register(PurposeMetricRule)
class PurposeMetricRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "purpose", "metric_code", "weight", "is_required")
    list_filter = ("is_required",)
    search_fields = ("purpose__code", "purpose__label", "metric_code")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("purpose__code", "metric_code")


@admin.register(DailyRecommendationTheme)
class DailyRecommendationThemeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "label", "display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "label", "subtitle", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("display_order", "code")


@admin.register(DailyRecommendationMetricRule)
class DailyRecommendationMetricRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "theme", "metric_code", "weight", "is_required")
    list_filter = ("is_required",)
    search_fields = ("theme__code", "theme__label", "metric_code")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("theme__code", "metric_code")


@admin.register(DailyRecommendationTagRule)
class DailyRecommendationTagRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "theme", "tag", "source_scope", "weight", "is_required")
    list_filter = ("source_scope", "is_required", "tag__semantic_kind", "tag__tag_group")
    search_fields = ("theme__code", "theme__label", "tag__code", "tag__label")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("theme__code", "source_scope", "tag__code")


@admin.register(DailyLibraryRecommendationSet)
class DailyLibraryRecommendationSetAdmin(admin.ModelAdmin):
    list_display = ("id", "recommendation_date", "theme", "region_key", "sigungu", "algorithm_version", "candidate_count")
    list_filter = ("recommendation_date", "theme", "sido", "sigungu", "algorithm_version")
    search_fields = ("theme__code", "theme__label", "region_key", "sido", "sigungu", "algorithm_version")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-recommendation_date", "region_key", "theme__code")


@admin.register(DailyLibraryRecommendationItem)
class DailyLibraryRecommendationItemAdmin(admin.ModelAdmin):
    list_display = ("id", "recommendation_set", "rank", "library", "score")
    list_filter = ("recommendation_set__recommendation_date", "recommendation_set__theme")
    search_fields = ("library__name", "recommendation_set__region_key", "recommendation_set__theme__code")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("recommendation_set", "rank")
