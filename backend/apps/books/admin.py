from django.contrib import admin

from .models import Book, BookTag, LibraryHolding, PopularBookItem, PopularBookSnapshot


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "authors_text", "publisher", "publication_year", "isbn13", "is_active")
    list_filter = ("publication_year", "provider_code", "is_active")
    search_fields = ("title", "authors_text", "publisher", "isbn13", "kdc_class_no", "kdc_class_name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("title",)


@admin.register(BookTag)
class BookTagAdmin(admin.ModelAdmin):
    list_display = ("id", "book", "tag", "source_method", "score", "confidence", "is_active")
    list_filter = ("source_method", "is_active", "tag__semantic_kind", "tag__tag_group")
    search_fields = ("book__title", "tag__code", "tag__label", "source_field")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("book__title", "tag__code")


@admin.register(LibraryHolding)
class LibraryHoldingAdmin(admin.ModelAdmin):
    list_display = ("id", "library", "book", "provider_code", "is_active", "last_fetched_at")
    list_filter = ("provider_code", "is_active")
    search_fields = ("library__name", "book__title", "book__isbn13")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("library__name", "book__title")


@admin.register(PopularBookSnapshot)
class PopularBookSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "provider_code", "scope_type", "region_code", "period_start", "period_end", "result_count")
    list_filter = ("provider_code", "scope_type", "region_code", "period_end")
    search_fields = ("provider_code", "query_hash", "region_code", "detail_region_code")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-period_end", "provider_code", "scope_type")


@admin.register(PopularBookItem)
class PopularBookItemAdmin(admin.ModelAdmin):
    list_display = ("id", "snapshot", "rank", "book", "loan_count")
    list_filter = ("snapshot__scope_type", "snapshot__provider_code")
    search_fields = ("book__title", "book__isbn13", "snapshot__query_hash")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("snapshot", "rank")
