from django.contrib import admin

from .models import Program, ProgramImage, ProgramTag


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "library", "category_code", "application_status", "operation_status", "operation_start_date", "is_visible")
    list_filter = ("category_code", "application_status", "operation_status", "is_visible", "source_sido", "source_sigungu")
    search_fields = ("title", "library__name", "external_program_key", "source_library_name", "source_board", "source_url")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-operation_start_date", "title")


@admin.register(ProgramTag)
class ProgramTagAdmin(admin.ModelAdmin):
    list_display = ("id", "program", "tag", "source_method", "score", "confidence", "is_active")
    list_filter = ("source_method", "is_active", "tag__semantic_kind", "tag__tag_group")
    search_fields = ("program__title", "tag__code", "tag__label", "source_field")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("program__title", "tag__code")


@admin.register(ProgramImage)
class ProgramImageAdmin(admin.ModelAdmin):
    list_display = ("id", "program", "media_asset", "is_main", "is_active", "display_order")
    list_filter = ("is_main", "is_active")
    search_fields = ("program__title", "media_asset__original_url", "caption")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("program__title", "display_order")
