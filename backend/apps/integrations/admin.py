from django.contrib import admin

from .models import SourceSyncRun


@admin.register(SourceSyncRun)
class SourceSyncRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source_name",
        "source_type",
        "target_domain",
        "status",
        "started_at",
        "finished_at",
        "total_count",
        "success_count",
        "failure_count",
        "warning_count",
    )
    list_filter = ("source_type", "target_domain", "status", "target_year", "target_month")
    search_fields = ("source_name", "target_domain", "error_message", "report_path")
    readonly_fields = ("started_at", "finished_at")
    ordering = ("-started_at",)
