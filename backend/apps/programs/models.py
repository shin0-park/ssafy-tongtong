from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class ProgramCategory(models.TextChoices):
    LECTURE_HUMANITIES = "lecture_humanities", "인문 강좌"
    READING_WRITING = "reading_writing", "독서·글쓰기"
    CULTURE_ART = "culture_art", "문화·예술"
    EXPERIENCE_EDUCATION = "experience_education", "체험·교육"
    EXHIBITION = "exhibition", "전시"
    OTHER = "other", "기타"


class ApplicationStatus(models.TextChoices):
    AVAILABLE = "available", "신청가능"
    CLOSED = "closed", "신청마감"
    NOT_REQUIRED = "not_required", "신청없음"


class OperationStatus(models.TextChoices):
    UPCOMING = "upcoming", "예정"
    ONGOING = "ongoing", "진행중"
    ENDED = "ended", "종료"


class ProgramTagSourceMethod(models.TextChoices):
    CATEGORY_RULE = "category_rule", "분류 규칙"
    TARGET_RULE = "target_rule", "대상 규칙"
    METADATA_RULE = "metadata_rule", "메타데이터 규칙"
    MANUAL = "manual", "수동"


class Program(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.PROTECT,
        related_name="programs",
    )
    source_sido = models.CharField(max_length=40, blank=True)
    source_sigungu = models.CharField(max_length=40, blank=True)
    source_library_name = models.CharField(max_length=120, blank=True)
    provider_code = models.CharField(max_length=40)
    external_program_key = models.CharField(
        max_length=160,
        help_text="원천 ID가 없으면 도서관, 제목, 기간, 원문 URL을 정규화한 안정 해시를 저장합니다.",
    )
    title = models.CharField(max_length=255)
    category_code = models.CharField(max_length=32, choices=ProgramCategory.choices)
    target_text = models.CharField(max_length=255, blank=True)
    target_codes = models.JSONField(default=list, blank=True)
    application_required = models.BooleanField(null=True, blank=True)
    application_start_date = models.DateField(null=True, blank=True)
    application_end_date = models.DateField(null=True, blank=True)
    application_status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        blank=True,
        default="",
        help_text="조회 전 날짜 기준으로 재계산 가능한 신청 상태 캐시입니다.",
    )
    operation_start_date = models.DateField(null=True, blank=True)
    operation_end_date = models.DateField(null=True, blank=True)
    operation_status = models.CharField(
        max_length=20,
        choices=OperationStatus.choices,
        blank=True,
        default="",
        help_text="조회 전 날짜 기준으로 재계산 가능한 운영 상태 캐시입니다.",
    )
    source_board = models.CharField(max_length=120, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    post_date = models.DateField(null=True, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    content_hash = models.CharField(max_length=128, blank=True)
    is_visible = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider_code", "external_program_key"],
                name="uq_program_external_key",
            ),
            models.CheckConstraint(
                condition=(
                    Q(application_start_date__isnull=True)
                    | Q(application_end_date__isnull=True)
                    | Q(application_end_date__gte=models.F("application_start_date"))
                ),
                name="program_application_period_order",
            ),
            models.CheckConstraint(
                condition=(
                    Q(operation_start_date__isnull=True)
                    | Q(operation_end_date__isnull=True)
                    | Q(operation_end_date__gte=models.F("operation_start_date"))
                ),
                name="program_operation_period_order",
            ),
        ]
        indexes = [
            models.Index(fields=["library", "is_visible"], name="idx_program_library_visible"),
            models.Index(
                fields=["is_visible", "operation_status", "operation_start_date"],
                name="idx_program_status_start",
            ),
            models.Index(fields=["category_code", "is_visible"], name="idx_program_category"),
        ]

    def __str__(self):
        return self.title


class ProgramTag(TimeStampedModel):
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="tag_links",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="program_links",
    )
    source_method = models.CharField(max_length=24, choices=ProgramTagSourceMethod.choices)
    source_field = models.CharField(max_length=80, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["program", "tag", "source_method"],
                name="uq_program_tag_source",
            )
        ]
        indexes = [
            models.Index(fields=["program", "is_active"], name="idx_program_tag_active"),
            models.Index(
                fields=["tag", "source_method", "is_active"],
                name="idx_program_tag_source",
            ),
        ]

    def __str__(self):
        return f"{self.program_id}:{self.tag_id}:{self.source_method}"


class ProgramImage(TimeStampedModel):
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="images",
    )
    media_asset = models.ForeignKey(
        "media_assets.MediaAsset",
        on_delete=models.PROTECT,
        related_name="program_usages",
    )
    is_main = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    caption = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["program", "media_asset"],
                name="uq_program_media_asset",
            ),
            models.UniqueConstraint(
                fields=["program"],
                condition=Q(is_active=True, is_main=True),
                name="uq_program_active_main_image",
            ),
        ]
        indexes = [
            models.Index(
                fields=["program", "is_active", "display_order"],
                name="idx_program_image_order",
            )
        ]

    def __str__(self):
        return f"{self.program_id}:{self.media_asset_id}"
