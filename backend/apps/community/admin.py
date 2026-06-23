from django.contrib import admin

from .models import (
    ReviewBookReference,
    ReviewProgramReference,
    ReviewTag,
    UserReview,
    UserReviewImage,
    UserReviewLike,
)


@admin.register(UserReview)
class UserReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "library", "moderation_status", "view_count", "like_count", "created_at")
    list_filter = ("moderation_status", "library", "created_at")
    search_fields = ("content", "user__email", "user__nickname", "library__name")
    readonly_fields = ("view_count", "like_count", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(UserReviewLike)
class UserReviewLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "review", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__nickname", "review__content", "review__library__name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(UserReviewImage)
class UserReviewImageAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "display_order", "created_at")
    list_filter = ("created_at",)
    search_fields = ("review__content", "review__library__name", "alt_text")
    readonly_fields = ("created_at",)
    ordering = ("review", "display_order")


@admin.register(ReviewBookReference)
class ReviewBookReferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "book", "display_order", "created_at")
    list_filter = ("created_at",)
    search_fields = ("review__content", "review__library__name", "book__title", "book__isbn13")
    readonly_fields = ("created_at",)
    ordering = ("review", "display_order")


@admin.register(ReviewProgramReference)
class ReviewProgramReferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "program", "display_order", "created_at")
    list_filter = ("created_at",)
    search_fields = ("review__content", "review__library__name", "program__title")
    readonly_fields = ("created_at",)
    ordering = ("review", "display_order")


@admin.register(ReviewTag)
class ReviewTagAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "tag", "created_at")
    list_filter = ("tag__semantic_kind", "tag__tag_group", "created_at")
    search_fields = ("review__content", "review__library__name", "tag__code", "tag__label")
    readonly_fields = ("created_at",)
    ordering = ("review", "tag__code")
