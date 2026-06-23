from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class AnalysisAxis(models.TextChoices):
    STUDY = "study", "공부형"
    BOOK = "book", "책 탐색형"
    PROGRAM = "program", "프로그램형"
    REST = "rest", "휴식형"


class SourceScope(models.TextChoices):
    ANY = "any", "전체"
    DIRECT = "direct", "직접"
    REVIEW_ROLLUP = "review_rollup", "후기 집계"
    PROGRAM_ROLLUP = "program_rollup", "프로그램 집계"
    BOOK_ROLLUP = "book_rollup", "도서 집계"


class Purpose(TimeStampedModel):
    code = models.SlugField(max_length=40, unique=True)
    label = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_home_theme = models.BooleanField(default=False, db_index=True)
    is_profile_selectable = models.BooleanField(default=False)
    analysis_axis = models.CharField(
        max_length=20,
        choices=AnalysisAxis.choices,
        blank=True,
        default="",
        help_text="빈 문자열은 나의 나들이 분석축 없음 상태를 뜻합니다.",
    )
    requires_location = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis_axis"],
                condition=~Q(analysis_axis="") & Q(is_active=True),
                name="uq_active_purpose_analysis_axis",
            )
        ]
        indexes = [
            models.Index(
                fields=["is_home_theme", "is_active", "display_order"],
                name="idx_purpose_home_active",
            )
        ]

    def __str__(self):
        return self.label


class PurposeTagRule(TimeStampedModel):
    purpose = models.ForeignKey(
        "recommendations.Purpose",
        on_delete=models.CASCADE,
        related_name="tag_rules",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="purpose_rules",
    )
    source_scope = models.CharField(max_length=24, choices=SourceScope.choices)
    weight = models.DecimalField(max_digits=6, decimal_places=4, default=1)
    is_required = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purpose", "tag", "source_scope"],
                name="uq_purpose_tag_scope",
            )
        ]
        indexes = [
            models.Index(fields=["purpose", "is_required"], name="idx_purpose_tag_required"),
            models.Index(fields=["tag", "source_scope"], name="idx_purpose_tag_scope"),
        ]

    def __str__(self):
        return f"{self.purpose_id}:{self.tag_id}:{self.source_scope}"


class PurposeMetricRule(TimeStampedModel):
    purpose = models.ForeignKey(
        "recommendations.Purpose",
        on_delete=models.CASCADE,
        related_name="metric_rules",
    )
    metric_code = models.CharField(max_length=80)
    weight = models.DecimalField(max_digits=6, decimal_places=4, default=1)
    is_required = models.BooleanField(default=False)
    normalization_rule = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purpose", "metric_code"],
                name="uq_purpose_metric",
            )
        ]
        indexes = [
            models.Index(fields=["purpose", "is_required"], name="idx_purpose_metric_required")
        ]

    def __str__(self):
        return f"{self.purpose_id}:{self.metric_code}"


class DailyRecommendationTheme(TimeStampedModel):
    code = models.SlugField(max_length=40, unique=True)
    label = models.CharField(max_length=80)
    subtitle = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active", "display_order"], name="idx_daily_theme_active")
        ]

    def __str__(self):
        return self.code


class DailyRecommendationMetricRule(TimeStampedModel):
    theme = models.ForeignKey(
        "recommendations.DailyRecommendationTheme",
        on_delete=models.CASCADE,
        related_name="metric_rules",
    )
    metric_code = models.CharField(max_length=80)
    weight = models.DecimalField(max_digits=6, decimal_places=4, default=1)
    is_required = models.BooleanField(default=False)
    normalization_rule = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["theme", "metric_code"],
                name="uq_daily_theme_metric",
            )
        ]
        indexes = [
            models.Index(fields=["theme", "is_required"], name="idx_daily_metric_required")
        ]

    def __str__(self):
        return f"{self.theme_id}:{self.metric_code}"


class DailyRecommendationTagRule(TimeStampedModel):
    theme = models.ForeignKey(
        "recommendations.DailyRecommendationTheme",
        on_delete=models.CASCADE,
        related_name="tag_rules",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="daily_theme_rules",
    )
    source_scope = models.CharField(max_length=24, choices=SourceScope.choices)
    weight = models.DecimalField(max_digits=6, decimal_places=4, default=1)
    is_required = models.BooleanField(default=False)
    normalization_rule = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["theme", "tag", "source_scope"],
                name="uq_daily_theme_tag_scope",
            )
        ]
        indexes = [
            models.Index(fields=["theme", "is_required"], name="idx_daily_tag_required"),
            models.Index(fields=["tag", "source_scope"], name="idx_daily_tag_scope"),
        ]

    def __str__(self):
        return f"{self.theme_id}:{self.tag_id}:{self.source_scope}"


class DailyLibraryRecommendationSet(TimeStampedModel):
    recommendation_date = models.DateField()
    theme = models.ForeignKey(
        "recommendations.DailyRecommendationTheme",
        on_delete=models.PROTECT,
        related_name="recommendation_sets",
    )
    region_key = models.CharField(max_length=30)
    sido = models.CharField(max_length=40)
    sigungu = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="빈 문자열은 시군구 미지정 지역 범위 sentinel입니다.",
    )
    algorithm_version = models.CharField(max_length=40)
    candidate_count = models.PositiveIntegerField(default=0)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recommendation_date", "region_key", "algorithm_version"],
                name="uq_daily_recommendation_set",
            )
        ]
        indexes = [
            models.Index(
                fields=["recommendation_date", "region_key"],
                name="idx_daily_set_region_date",
            )
        ]

    def __str__(self):
        return f"{self.recommendation_date}:{self.region_key}:{self.algorithm_version}"


class DailyLibraryRecommendationItem(TimeStampedModel):
    recommendation_set = models.ForeignKey(
        "recommendations.DailyLibraryRecommendationSet",
        on_delete=models.CASCADE,
        related_name="items",
    )
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.PROTECT,
        related_name="daily_recommendation_items",
    )
    rank = models.PositiveSmallIntegerField()
    score = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    score_detail = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recommendation_set", "rank"],
                name="uq_daily_item_rank",
            ),
            models.UniqueConstraint(
                fields=["recommendation_set", "library"],
                name="uq_daily_item_library",
            ),
        ]
        indexes = [
            models.Index(
                fields=["recommendation_set", "rank"],
                name="idx_daily_item_rank",
            )
        ]

    def __str__(self):
        return f"{self.recommendation_set_id}:{self.rank}:{self.library_id}"
