from django.contrib import admin

from .models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "label",
        "semantic_kind",
        "tag_group",
        "is_profile_selectable",
        "is_review_selectable",
        "is_filterable",
        "is_active",
        "display_order",
    )
    list_filter = (
        "semantic_kind",
        "tag_group",
        "review_group",
        "is_profile_selectable",
        "is_review_selectable",
        "is_filterable",
        "is_active",
    )
    search_fields = ("code", "label", "review_label", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("tag_group", "display_order", "code")
