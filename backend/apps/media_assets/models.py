from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class AssetOrigin(models.TextChoices):
    OFFICIAL_EXTERNAL = "official_external", "공식 외부 이미지"
    SYSTEM_DEFAULT = "system_default", "시스템 대체 이미지"
    ADMIN_UPLOAD = "admin_upload", "관리자 업로드"


class DefaultMediaTargetDomain(models.TextChoices):
    LIBRARY = "library", "도서관"
    PROGRAM = "program", "프로그램"
    REVIEW = "review", "후기"
    PROFILE = "profile", "프로필"


class MediaAsset(TimeStampedModel):
    asset_origin = models.CharField(max_length=32, choices=AssetOrigin.choices)
    original_url = models.URLField(max_length=500, blank=True)
    file = models.ImageField(upload_to="media-assets/", null=True, blank=True)
    source_name = models.CharField(max_length=100, blank=True)
    source_page_url = models.URLField(max_length=500, blank=True)
    source_asset_id = models.CharField(max_length=120, blank=True)
    license_code = models.CharField(max_length=80, blank=True)
    attribution_text = models.TextField(blank=True)
    commercial_use_allowed = models.BooleanField(null=True, blank=True)
    modification_allowed = models.BooleanField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~(Q(original_url="") & Q(file="")),
                name="media_asset_url_or_file_required",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(asset_origin=AssetOrigin.OFFICIAL_EXTERNAL)
                    | Q(is_active=False)
                    | (~Q(license_code="") & ~Q(attribution_text=""))
                ),
                name="media_asset_official_attribution_required",
            ),
            models.UniqueConstraint(
                fields=["original_url"],
                condition=~Q(original_url=""),
                name="uq_media_asset_original_url",
            ),
        ]
        indexes = [
            models.Index(fields=["asset_origin", "is_active"], name="idx_media_origin_active")
        ]

    def __str__(self):
        return self.original_url or self.file.name


class DefaultMediaAssetRule(TimeStampedModel):
    target_domain = models.CharField(max_length=24, choices=DefaultMediaTargetDomain.choices)
    target_code = models.CharField(max_length=80)
    media_asset = models.ForeignKey(
        "media_assets.MediaAsset",
        on_delete=models.PROTECT,
        related_name="default_rules",
    )
    priority = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["target_domain", "target_code", "priority"],
                condition=Q(is_active=True),
                name="uq_active_default_media_rule",
            )
        ]
        indexes = [
            models.Index(
                fields=["target_domain", "target_code", "is_active", "priority"],
                name="idx_default_media_lookup",
            )
        ]

    def __str__(self):
        return f"{self.target_domain}:{self.target_code}"
