from django.contrib import admin

from .models import DefaultMediaAssetRule, MediaAsset


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("id", "asset_origin", "source_name", "license_code", "is_active", "updated_at")
    list_filter = ("asset_origin", "is_active", "license_code")
    search_fields = ("original_url", "source_name", "source_page_url", "source_asset_id", "attribution_text")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("asset_origin", "-updated_at")


@admin.register(DefaultMediaAssetRule)
class DefaultMediaAssetRuleAdmin(admin.ModelAdmin):
    list_display = ("id", "target_domain", "target_code", "media_asset", "priority", "is_active")
    list_filter = ("target_domain", "is_active")
    search_fields = ("target_code", "media_asset__original_url", "media_asset__source_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("target_domain", "target_code", "priority")
