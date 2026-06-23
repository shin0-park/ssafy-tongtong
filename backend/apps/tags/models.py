from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class TagSemanticKind(models.TextChoices):
    OBJECTIVE = "objective", "객관 사실"
    EXPERIENCE = "experience", "사용자 경험"
    CLASSIFICATION = "classification", "분류"
    CONTENT = "content", "콘텐츠 주제"


class TagGroup(models.TextChoices):
    LIBRARY_TYPE = "library_type", "도서관 유형"
    OPERATION = "operation", "운영 조건"
    STUDY_READING = "study_reading", "공부·열람"
    FACILITY = "facility", "시설"
    SPACE_ATMOSPHERE = "space_atmosphere", "공간·분위기"
    COLLECTION = "collection", "책·자료"
    BOOK_SUBJECT = "book_subject", "책 주제"
    PROGRAM_TYPE = "program_type", "프로그램 유형"
    PROGRAM_TARGET = "program_target", "프로그램 대상"
    KIDS_FAMILY = "kids_family", "아이·가족"
    ACCESS_CONVENIENCE = "access_convenience", "접근·편의"
    GUIDANCE_MANAGEMENT = "guidance_management", "안내·관리"


class ReviewGroup(models.TextChoices):
    STUDY_READING = "study_reading", "공부·열람"
    SPACE_ATMOSPHERE = "space_atmosphere", "공간·분위기"
    COLLECTION = "collection", "책·자료"
    PROGRAM = "program", "프로그램"
    KIDS_FAMILY = "kids_family", "아이·가족"
    ACCESS_CONVENIENCE = "access_convenience", "접근·편의"
    GUIDANCE_MANAGEMENT = "guidance_management", "안내·관리"


class Tag(TimeStampedModel):
    code = models.SlugField(max_length=100, unique=True)
    label = models.CharField(max_length=100)
    semantic_kind = models.CharField(max_length=24, choices=TagSemanticKind.choices)
    tag_group = models.CharField(max_length=40, choices=TagGroup.choices)
    description = models.TextField(blank=True)
    is_profile_selectable = models.BooleanField(default=False)
    is_review_selectable = models.BooleanField(default=False)
    review_label = models.CharField(max_length=120, blank=True)
    review_group = models.CharField(max_length=40, choices=ReviewGroup.choices, blank=True)
    is_filterable = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    review_display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(is_review_selectable=False)
                    | (
                        Q(semantic_kind=TagSemanticKind.EXPERIENCE)
                        & ~Q(review_label="")
                        & ~Q(review_group="")
                        & Q(review_display_order__gt=0)
                    )
                ),
                name="tag_review_metadata_required",
            )
        ]
        indexes = [
            models.Index(
                fields=["semantic_kind", "tag_group", "is_active", "display_order"],
                name="idx_tag_kind_group_active",
            ),
            models.Index(
                fields=["review_group", "is_review_selectable", "review_display_order"],
                name="idx_tag_review_options",
            ),
        ]

    def __str__(self):
        return self.label
