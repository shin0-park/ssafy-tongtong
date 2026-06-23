from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    User,
    UserPreferredPurpose,
    UserPreferredRegion,
    UserPreferredTag,
    UserProfile,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("id", "email", "nickname", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("email", "nickname")
    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("nickname", "first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nickname", "password1", "password2"),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "bio", "updated_at")
    search_fields = ("user__email", "user__nickname", "bio")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("user__email",)


@admin.register(UserPreferredRegion)
class UserPreferredRegionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "region_key", "sido", "sigungu", "weight", "display_order", "is_active")
    list_filter = ("sido", "sigungu", "is_active")
    search_fields = ("user__email", "region_key", "sido", "sigungu")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("user__email", "display_order", "region_key")


@admin.register(UserPreferredTag)
class UserPreferredTagAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "tag", "weight", "display_order", "is_active")
    list_filter = ("is_active", "tag__semantic_kind", "tag__tag_group")
    search_fields = ("user__email", "tag__code", "tag__label")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("user__email", "display_order", "tag__code")


@admin.register(UserPreferredPurpose)
class UserPreferredPurposeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "purpose", "weight", "display_order", "is_active")
    list_filter = ("is_active", "purpose__is_home_theme", "purpose__is_profile_selectable")
    search_fields = ("user__email", "purpose__code", "purpose__label")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("user__email", "display_order", "purpose__code")
