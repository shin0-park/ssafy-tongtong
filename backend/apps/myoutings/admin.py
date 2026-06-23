from django.contrib import admin

from .models import UserBookSave, UserLibrarySave, UserProgramSave


@admin.register(UserLibrarySave)
class UserLibrarySaveAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "library", "memo", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__nickname", "library__name", "memo")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(UserBookSave)
class UserBookSaveAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "memo", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__nickname", "book__title", "book__isbn13", "memo")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(UserProgramSave)
class UserProgramSaveAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "program", "memo", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__nickname", "program__title", "memo")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
