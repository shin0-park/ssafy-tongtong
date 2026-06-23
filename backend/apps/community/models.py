from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class ReviewModerationStatus(models.TextChoices):
    PENDING = "pending", "검토 대기"
    VISIBLE = "visible", "공개"
    HIDDEN = "hidden", "숨김"


class UserReview(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    content = models.CharField(max_length=200)
    view_count = models.PositiveBigIntegerField(default=0)
    like_count = models.PositiveBigIntegerField(default=0)
    moderation_status = models.CharField(
        max_length=16,
        choices=ReviewModerationStatus.choices,
        default=ReviewModerationStatus.VISIBLE,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(content=""), name="review_content_not_empty"),
            models.CheckConstraint(condition=Q(view_count__gte=0), name="review_view_count_gte_0"),
            models.CheckConstraint(condition=Q(like_count__gte=0), name="review_like_count_gte_0"),
        ]
        indexes = [
            models.Index(fields=["moderation_status", "-created_at"], name="idx_review_recent"),
            models.Index(
                fields=["moderation_status", "-view_count", "-created_at"],
                name="idx_review_views",
            ),
            models.Index(
                fields=["moderation_status", "-like_count", "-created_at"],
                name="idx_review_likes",
            ),
            models.Index(
                fields=["library", "moderation_status", "-created_at"],
                name="idx_review_library_recent",
            ),
            models.Index(fields=["user", "-created_at"], name="idx_review_user_recent"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.library_id}:{self.created_at:%Y-%m-%d}"


class UserReviewLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_likes",
    )
    review = models.ForeignKey(
        "community.UserReview",
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "review"], name="uq_user_review_like")
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_review_like_user"),
            models.Index(fields=["review", "-created_at"], name="idx_review_like_review"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.review_id}"


class UserReviewImage(models.Model):
    review = models.ForeignKey(
        "community.UserReview",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="reviews/")
    alt_text = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["review", "display_order"], name="idx_review_image_order")
        ]

    def __str__(self):
        return f"{self.review_id}:{self.display_order}"


class ReviewBookReference(models.Model):
    review = models.ForeignKey(
        "community.UserReview",
        on_delete=models.CASCADE,
        related_name="book_references",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="review_references",
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review", "book"], name="uq_review_book_reference"
            )
        ]
        indexes = [
            models.Index(fields=["review", "display_order"], name="idx_review_book_order")
        ]

    def __str__(self):
        return f"{self.review_id}:{self.book_id}"


class ReviewProgramReference(models.Model):
    review = models.ForeignKey(
        "community.UserReview",
        on_delete=models.CASCADE,
        related_name="program_references",
    )
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.PROTECT,
        related_name="review_references",
        help_text="program.library_id == review.library_id 검증은 serializer/service에서 수행합니다.",
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review", "program"], name="uq_review_program_reference"
            )
        ]
        indexes = [
            models.Index(fields=["review", "display_order"], name="idx_review_program_order")
        ]

    def __str__(self):
        return f"{self.review_id}:{self.program_id}"


class ReviewTag(models.Model):
    review = models.ForeignKey(
        "community.UserReview",
        on_delete=models.CASCADE,
        related_name="tag_links",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="review_links",
        help_text="후기 선택 가능 경험 태그 여부는 serializer/service에서 검증합니다.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["review", "tag"], name="uq_review_tag")
        ]
        indexes = [
            models.Index(fields=["review", "created_at"], name="idx_review_tag_created")
        ]

    def __str__(self):
        return f"{self.review_id}:{self.tag_id}"
