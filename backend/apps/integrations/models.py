from django.db import models
from django.db.models import Q
from django.utils import timezone


class SourceType(models.TextChoices):
    FILE = "file", "파일"
    API = "api", "API"
    CRAWLER = "crawler", "크롤러"
    MANUAL = "manual", "수동"


class SourceSyncStatus(models.TextChoices):
    SUCCESS = "success", "성공"
    FAILED = "failed", "실패"
    PARTIAL = "partial", "부분 성공"


class SourceSyncRun(models.Model):
    source_name = models.CharField(max_length=80)
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    target_domain = models.CharField(max_length=40)
    target_year = models.PositiveSmallIntegerField(null=True, blank=True)
    target_month = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=SourceSyncStatus.choices,
        null=True,
        blank=True,
        db_index=True,
        help_text="실행 중 상태는 status=NULL, started_at 존재, finished_at=NULL로 해석합니다.",
    )
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="API 키, Authorization, serviceKey, authKey 등 민감 정보를 제거한 값만 저장합니다.",
    )
    summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="외부 원문 응답 전체가 아니라 민감 정보가 제거된 실행 요약만 저장합니다.",
    )
    error_message = models.TextField(blank=True)
    report_path = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(target_month__isnull=True)
                | (Q(target_month__gte=1) & Q(target_month__lte=12)),
                name="source_sync_month_range",
            )
        ]
        indexes = [
            models.Index(fields=["source_name", "-started_at"], name="idx_sync_source_started"),
            models.Index(fields=["status", "-started_at"], name="idx_sync_status_started"),
            models.Index(fields=["target_year", "target_month"], name="idx_sync_target_period"),
            models.Index(fields=["target_domain", "-started_at"], name="idx_sync_domain_started"),
        ]

    def __str__(self):
        return f"{self.source_name}:{self.target_domain}:{self.started_at:%Y-%m-%d %H:%M:%S}"
