from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class UserPreferenceStatus(models.TextChoices):
    COLLECTING = "collecting", "수집 중"
    PENDING = "pending", "계산 대기"
    READY = "ready", "계산 완료"
    FAILED = "failed", "계산 실패"


class UserPreference(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preference",
    )
    status = models.CharField(
        max_length=16,
        choices=UserPreferenceStatus.choices,
        default=UserPreferenceStatus.COLLECTING,
        db_index=True,
    )
    signal_count = models.PositiveIntegerField(default=0)
    library_signal_count = models.PositiveIntegerField(default=0)
    book_signal_count = models.PositiveIntegerField(default=0)
    program_signal_count = models.PositiveIntegerField(default=0)
    written_review_signal_count = models.PositiveIntegerField(default=0)
    liked_review_signal_count = models.PositiveIntegerField(default=0)
    algorithm_version = models.CharField(max_length=40, blank=True)
    eligible_since = models.DateTimeField(null=True, blank=True)
    calculated_at = models.DateTimeField(null=True, blank=True)
    failure_message = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "calculated_at"], name="idx_user_pref_status")
        ]

    def __str__(self):
        return f"{self.user_id}:{self.status}"


class UserPreferenceItem(TimeStampedModel):
    user_preference = models.ForeignKey(
        "preferences.UserPreference",
        on_delete=models.CASCADE,
        related_name="items",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="preference_items",
    )
    score = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    count = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=0,
        help_text="최근성 가중 관측 횟수라 소수 값을 허용합니다.",
    )
    rank = models.PositiveIntegerField(
        default=0,
        help_text="0은 아직 순위가 부여되지 않은 상태입니다.",
    )
    source_count_library = models.PositiveIntegerField(default=0)
    source_count_book = models.PositiveIntegerField(default=0)
    source_count_program = models.PositiveIntegerField(default=0)
    source_count_review_written = models.PositiveIntegerField(default=0)
    source_count_review_liked = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_preference", "tag"],
                name="uq_user_pref_item_tag",
            ),
            models.UniqueConstraint(
                fields=["user_preference", "rank"],
                condition=Q(rank__gt=0),
                name="uq_user_pref_item_rank",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=0),
                name="user_pref_item_score_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(count__gte=0),
                name="user_pref_item_count_gte_0",
            ),
        ]
        indexes = [
            models.Index(fields=["user_preference", "rank"], name="idx_user_pref_item_rank"),
            models.Index(fields=["tag"], name="idx_user_pref_item_tag"),
        ]

    def __str__(self):
        return f"{self.user_preference_id}:{self.tag_id}"
