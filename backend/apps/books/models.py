from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class BookTagSourceMethod(models.TextChoices):
    KDC_RULE = "kdc_rule", "KDC 규칙"
    METADATA_RULE = "metadata_rule", "메타데이터 규칙"
    MANUAL = "manual", "수동"


class PopularBookScopeType(models.TextChoices):
    NATIONAL = "national", "전국"
    REGION = "region", "지역"


class Book(TimeStampedModel):
    isbn13 = models.CharField(
        max_length=13,
        blank=True,
        default="",
        help_text="문자열 ISBN입니다. 빈 문자열은 아직 ISBN 미확인 또는 미수집 상태를 뜻합니다.",
    )
    title = models.CharField(max_length=255)
    authors_text = models.CharField(max_length=255, blank=True)
    publisher = models.CharField(max_length=120, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)
    volume = models.CharField(max_length=80, blank=True)
    addition_symbol = models.CharField(max_length=20, blank=True)
    kdc_class_no = models.CharField(max_length=40, blank=True)
    kdc_class_name = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    cover_image_url = models.URLField(max_length=500, blank=True)
    source_detail_url = models.URLField(max_length=500, blank=True)
    provider_code = models.CharField(max_length=40, blank=True)
    metadata_fetched_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["isbn13"],
                condition=~Q(isbn13=""),
                name="uq_book_isbn13_present",
            )
        ]
        indexes = [
            models.Index(fields=["title"], name="idx_book_title"),
            models.Index(fields=["authors_text"], name="idx_book_authors"),
            models.Index(fields=["is_active", "title"], name="idx_book_active_title"),
        ]

    def __str__(self):
        return self.title


class BookTag(TimeStampedModel):
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="tag_links",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="book_links",
    )
    source_method = models.CharField(max_length=24, choices=BookTagSourceMethod.choices)
    source_field = models.CharField(max_length=80, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["book", "tag", "source_method"],
                name="uq_book_tag_source",
            )
        ]
        indexes = [
            models.Index(fields=["book", "is_active"], name="idx_book_tag_active"),
            models.Index(fields=["tag", "source_method", "is_active"], name="idx_book_tag_source"),
        ]

    def __str__(self):
        return f"{self.book_id}:{self.tag_id}:{self.source_method}"


class LibraryHolding(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    provider_code = models.CharField(max_length=40)
    first_seen_at = models.DateTimeField(null=True, blank=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "book"],
                name="uq_library_book_holding",
            )
        ]
        indexes = [
            models.Index(fields=["library", "is_active"], name="idx_holding_library_active"),
            models.Index(fields=["book", "is_active"], name="idx_holding_book_active"),
        ]

    def __str__(self):
        return f"{self.library_id}:{self.book_id}"


class PopularBookSnapshot(TimeStampedModel):
    provider_code = models.CharField(max_length=40)
    scope_type = models.CharField(max_length=16, choices=PopularBookScopeType.choices)
    region_code = models.CharField(max_length=40, blank=True)
    detail_region_code = models.CharField(max_length=40, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    query_params = models.JSONField(default=dict, blank=True)
    query_hash = models.CharField(max_length=128)
    result_count = models.PositiveIntegerField(default=0)
    fetched_at = models.DateTimeField(null=True, blank=True)
    fresh_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider_code", "query_hash", "period_start", "period_end"],
                name="uq_popular_snapshot_query",
            ),
            models.CheckConstraint(
                condition=Q(period_end__gte=models.F("period_start")),
                name="popular_snapshot_period_order",
            ),
        ]
        indexes = [
            models.Index(
                fields=["scope_type", "region_code", "period_end"],
                name="idx_popular_snapshot_scope",
            ),
            models.Index(fields=["fresh_until"], name="idx_popular_snapshot_fresh"),
        ]

    def __str__(self):
        return f"{self.provider_code}:{self.scope_type}:{self.period_start}-{self.period_end}"


class PopularBookItem(TimeStampedModel):
    snapshot = models.ForeignKey(
        "books.PopularBookSnapshot",
        on_delete=models.CASCADE,
        related_name="items",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="popular_items",
    )
    rank = models.PositiveIntegerField()
    loan_count = models.PositiveIntegerField(null=True, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "rank"],
                name="uq_popular_item_rank",
            ),
            models.UniqueConstraint(
                fields=["snapshot", "book"],
                name="uq_popular_item_book",
            ),
        ]
        indexes = [
            models.Index(fields=["snapshot", "rank"], name="idx_popular_item_rank")
        ]

    def __str__(self):
        return f"{self.snapshot_id}:{self.rank}:{self.book_id}"
