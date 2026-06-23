from django.contrib import admin

from .models import UserPreference, UserPreferenceItem


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "signal_count", "algorithm_version", "calculated_at")
    list_filter = ("status", "algorithm_version", "calculated_at")
    search_fields = ("user__email", "user__nickname", "algorithm_version", "failure_message")
    readonly_fields = (
        "signal_count",
        "library_signal_count",
        "book_signal_count",
        "program_signal_count",
        "written_review_signal_count",
        "liked_review_signal_count",
        "created_at",
        "updated_at",
    )
    ordering = ("user__email",)


@admin.register(UserPreferenceItem)
class UserPreferenceItemAdmin(admin.ModelAdmin):
    list_display = ("id", "user_preference", "tag", "score", "count", "rank")
    list_filter = ("tag__semantic_kind", "tag__tag_group")
    search_fields = ("user_preference__user__email", "user_preference__user__nickname", "tag__code", "tag__label")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("user_preference__user__email", "rank", "tag__code")
