from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class LibraryType(models.TextChoices):
    PUBLIC = "public", "공공도서관"
    SMALL = "small", "작은도서관"
    CHILDREN = "children", "어린이도서관"
    OTHER = "other", "기타"


class AliasType(models.TextChoices):
    SOURCE_NAME = "source_name", "원천 명칭"
    SHORT_NAME = "short_name", "약칭"
    LEGACY_NAME = "legacy_name", "이전 명칭"
    CORRECTION = "correction", "오타 교정"
    DUPLICATE_MERGE = "duplicate_merge", "중복 병합"


class ScheduleDayType(models.TextChoices):
    DAY_OF_WEEK = "day_of_week", "요일"
    PUBLIC_HOLIDAY = "public_holiday", "공휴일"
    SPECIFIC_DATE = "specific_date", "특정일"


class ScheduleStatus(models.TextChoices):
    OPEN = "open", "개관"
    CLOSED = "closed", "휴관"
    UNKNOWN = "unknown", "미확인"


class ClosureRuleType(models.TextChoices):
    WEEKLY = "weekly", "매주"
    NTH_WEEKDAY = "nth_weekday", "n번째 요일"
    PUBLIC_HOLIDAY = "public_holiday", "공휴일"
    NAMED_HOLIDAY = "named_holiday", "명절"
    TEMPORARY = "temporary", "임시 휴관"
    FULL_CLOSURE = "full_closure", "전체 휴관"
    UNKNOWN = "unknown", "미확인"


class LibraryTagSourceMethod(models.TextChoices):
    FIELD_RULE = "field_rule", "필드 규칙"
    FACILITY_RULE = "facility_rule", "시설 규칙"
    PROGRAM_ROLLUP = "program_rollup", "프로그램 집계"
    REVIEW_ROLLUP = "review_rollup", "후기 집계"
    BOOK_ROLLUP = "book_rollup", "도서 집계"
    MANUAL = "manual", "수동"


class LibraryImageType(models.TextChoices):
    MAIN = "main", "대표"
    EXTERIOR = "exterior", "외관"
    INTERIOR = "interior", "내부"
    CHILDREN_ROOM = "children_room", "어린이자료실"
    FACILITY = "facility", "시설"
    OTHER = "other", "기타"


class Library(TimeStampedModel):
    name = models.CharField(max_length=120)
    normalized_name = models.CharField(max_length=120, db_index=True)
    sido = models.CharField(max_length=40)
    sigungu = models.CharField(max_length=40)
    library_type = models.CharField(max_length=24, choices=LibraryType.choices)
    library_type_raw = models.CharField(max_length=80, blank=True)
    road_address = models.CharField(max_length=255)
    normalized_address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    homepage_url = models.URLField(max_length=500, blank=True)
    operating_agency = models.CharField(max_length=120, blank=True)
    short_description = models.CharField(max_length=160, blank=True)
    standard_provider_agency_code = models.CharField(max_length=40, blank=True)
    standard_provider_agency_name = models.CharField(max_length=120, blank=True)
    standard_reference_date = models.DateField(null=True, blank=True)
    standard_row_hash = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["sido", "sigungu", "library_type", "is_active"],
                name="idx_library_region_type",
            ),
            models.Index(fields=["latitude", "longitude"], name="idx_library_coordinates"),
        ]

    def __str__(self):
        return self.name


class LibraryAlias(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    alias_name = models.CharField(max_length=120)
    normalized_alias_name = models.CharField(max_length=120)
    sigungu = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="빈 문자열은 nullable unique 중복을 피하기 위한 미지정 sentinel입니다.",
    )
    alias_type = models.CharField(max_length=32, choices=AliasType.choices)
    provider_code = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="빈 문자열은 nullable unique 중복을 피하기 위한 미지정 sentinel입니다.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "normalized_alias_name", "sigungu", "provider_code"],
                name="uq_library_alias_identity",
            )
        ]
        indexes = [
            models.Index(
                fields=["normalized_alias_name", "sigungu", "is_active"],
                name="idx_library_alias_lookup",
            )
        ]

    def __str__(self):
        return self.alias_name


class LibraryExternalIdentifier(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="external_identifiers",
    )
    provider_code = models.CharField(max_length=40)
    code_type = models.CharField(max_length=40)
    external_code = models.CharField(max_length=120)
    external_name = models.CharField(max_length=120, blank=True)
    external_address = models.CharField(max_length=255, blank=True)
    match_method = models.CharField(max_length=80, blank=True)
    match_confidence = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    first_seen_at = models.DateTimeField(null=True, blank=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider_code", "code_type", "external_code"],
                name="uq_library_external_code",
            )
        ]
        indexes = [
            models.Index(fields=["library", "is_active"], name="idx_library_external_active")
        ]

    def __str__(self):
        return f"{self.provider_code}:{self.external_code}"


class LibraryOpeningHour(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="opening_hours",
    )
    provider_code = models.CharField(max_length=40)
    day_type = models.CharField(max_length=24, choices=ScheduleDayType.choices)
    day_of_week = models.PositiveSmallIntegerField(null=True, blank=True)
    specific_date = models.DateField(null=True, blank=True)
    sequence = models.PositiveSmallIntegerField(default=0)
    schedule_status = models.CharField(max_length=16, choices=ScheduleStatus.choices)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    closes_next_day = models.BooleanField(default=False)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    raw_text = models.TextField(blank=True)
    source_field = models.CharField(max_length=80, blank=True)
    quality_flags = models.JSONField(default=dict, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    source_reference_date = models.DateField(null=True, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "library",
                    "provider_code",
                    "day_type",
                    "day_of_week",
                    "specific_date",
                    "sequence",
                ],
                condition=Q(is_current=True),
                name="uq_current_opening_rule",
            ),
            models.CheckConstraint(
                condition=Q(day_of_week__isnull=True)
                | (Q(day_of_week__gte=0) & Q(day_of_week__lte=6)),
                name="opening_hour_weekday_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(day_type=ScheduleDayType.DAY_OF_WEEK)
                    & Q(day_of_week__isnull=False)
                    & Q(specific_date__isnull=True)
                )
                | (
                    Q(day_type=ScheduleDayType.PUBLIC_HOLIDAY)
                    & Q(day_of_week__isnull=True)
                    & Q(specific_date__isnull=True)
                )
                | (
                    Q(day_type=ScheduleDayType.SPECIFIC_DATE)
                    & Q(day_of_week__isnull=True)
                    & Q(specific_date__isnull=False)
                ),
                name="opening_hour_day_type_fields",
            ),
            models.CheckConstraint(
                condition=(
                    Q(open_time__isnull=True)
                    & Q(close_time__isnull=True)
                )
                | (
                    Q(open_time__isnull=False)
                    & Q(close_time__isnull=False)
                ),
                name="opening_hour_time_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["library", "is_current"], name="idx_opening_library_current")
        ]

    def __str__(self):
        return f"{self.library_id}:{self.day_type}:{self.sequence}"


class LibraryClosureRule(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="closure_rules",
    )
    provider_code = models.CharField(max_length=40)
    rule_type = models.CharField(max_length=24, choices=ClosureRuleType.choices)
    normalized_rule = models.JSONField(default=dict, blank=True)
    raw_text = models.TextField(blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    source_url = models.URLField(max_length=500, blank=True)
    source_reference_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True, db_index=True)
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["library", "is_current", "priority"], name="idx_closure_rule_current")
        ]

    def __str__(self):
        return f"{self.library_id}:{self.rule_type}"


class PublicHolidayCalendar(TimeStampedModel):
    year = models.PositiveSmallIntegerField(unique=True)
    provider_code = models.CharField(max_length=40)
    is_complete = models.BooleanField(default=False, db_index=True)
    synced_month_count = models.PositiveSmallIntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    last_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(synced_month_count__gte=0) & Q(synced_month_count__lte=12),
                name="holiday_calendar_month_range",
            ),
            models.CheckConstraint(
                condition=Q(is_complete=False) | Q(synced_month_count=12),
                name="holiday_calendar_complete_count",
            ),
        ]

    def __str__(self):
        return f"{self.year} {self.provider_code}"


class PublicHoliday(TimeStampedModel):
    calendar = models.ForeignKey(
        "libraries.PublicHolidayCalendar",
        on_delete=models.CASCADE,
        related_name="holidays",
    )
    date = models.DateField()
    source_seq = models.CharField(max_length=20)
    date_kind = models.CharField(max_length=20)
    name = models.CharField(max_length=80)
    holiday_code = models.CharField(max_length=80, blank=True)
    is_public_holiday = models.BooleanField(default=True)
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "date", "source_seq"],
                name="uq_public_holiday_source",
            )
        ]
        indexes = [
            models.Index(fields=["date", "is_public_holiday"], name="idx_public_holiday_date")
        ]

    def __str__(self):
        return f"{self.date} {self.name}"


class LibraryDailySchedule(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="daily_schedules",
    )
    date = models.DateField()
    status = models.CharField(max_length=16, choices=ScheduleStatus.choices)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    closes_next_day = models.BooleanField(default=False)
    reason_code = models.CharField(max_length=80, blank=True)
    reason_text = models.CharField(max_length=200, blank=True)
    calculation_basis = models.JSONField(default=dict, blank=True)
    has_source_conflict = models.BooleanField(default=False, db_index=True)
    rule_version = models.CharField(max_length=40)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["library", "date"], name="uq_library_daily_schedule"),
            models.CheckConstraint(
                condition=(
                    Q(open_time__isnull=True)
                    & Q(close_time__isnull=True)
                )
                | (
                    Q(open_time__isnull=False)
                    & Q(close_time__isnull=False)
                ),
                name="daily_schedule_time_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["date", "status"], name="idx_daily_schedule_status")
        ]

    def __str__(self):
        return f"{self.library_id}:{self.date}:{self.status}"


class LibraryStatisticSnapshot(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="statistic_snapshots",
    )
    provider_code = models.CharField(max_length=40)
    reference_date = models.DateField()
    reading_seat_count = models.PositiveIntegerField(null=True, blank=True)
    book_count = models.PositiveIntegerField(null=True, blank=True)
    serial_count = models.PositiveIntegerField(null=True, blank=True)
    non_book_count = models.PositiveIntegerField(null=True, blank=True)
    loan_limit_count = models.PositiveIntegerField(null=True, blank=True)
    loan_period_days = models.PositiveIntegerField(null=True, blank=True)
    site_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    building_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    quality_flags = models.JSONField(default=dict, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "provider_code", "reference_date"],
                name="uq_library_stat_snapshot",
            ),
            models.UniqueConstraint(
                fields=["library", "provider_code"],
                condition=Q(is_current=True),
                name="uq_current_library_stat",
            ),
        ]
        indexes = [
            models.Index(fields=["library", "is_current"], name="idx_library_stat_current")
        ]

    def __str__(self):
        return f"{self.library_id}:{self.provider_code}:{self.reference_date}"


class LibraryFacilityProfile(TimeStampedModel):
    library = models.OneToOneField(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="facility_profile",
    )
    has_reading_room = models.BooleanField(null=True, blank=True)
    has_children_room = models.BooleanField(null=True, blank=True)
    has_digital_room = models.BooleanField(null=True, blank=True)
    has_parking = models.BooleanField(null=True, blank=True)
    has_cafe = models.BooleanField(null=True, blank=True)
    has_wifi = models.BooleanField(null=True, blank=True)
    has_nursing_room = models.BooleanField(null=True, blank=True)
    has_accessible_facility = models.BooleanField(null=True, blank=True)
    has_elevator = models.BooleanField(null=True, blank=True)
    has_lounge = models.BooleanField(null=True, blank=True)
    has_outdoor_space = models.BooleanField(null=True, blank=True)
    source_name = models.CharField(max_length=80, default="facility_json")
    source_reference_date = models.DateField(null=True, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.library_id} facilities"


class LibraryTag(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="tag_links",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="library_links",
    )
    source_method = models.CharField(max_length=24, choices=LibraryTagSourceMethod.choices)
    source_field = models.CharField(max_length=80, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    evidence_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "tag", "source_method"],
                name="uq_library_tag_source",
            )
        ]
        indexes = [
            models.Index(fields=["library", "is_active"], name="idx_library_tag_active"),
            models.Index(
                fields=["tag", "source_method", "is_active"],
                name="idx_tag_source_active",
            ),
        ]

    def __str__(self):
        return f"{self.library_id}:{self.tag_id}:{self.source_method}"


class LibraryImage(TimeStampedModel):
    library = models.ForeignKey(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="images",
    )
    media_asset = models.ForeignKey(
        "media_assets.MediaAsset",
        on_delete=models.PROTECT,
        related_name="library_usages",
    )
    image_type = models.CharField(max_length=24, choices=LibraryImageType.choices)
    is_main = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    caption = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "media_asset"],
                name="uq_library_media_asset",
            ),
            models.UniqueConstraint(
                fields=["library"],
                condition=Q(is_active=True, is_main=True),
                name="uq_library_active_main_image",
            ),
        ]
        indexes = [
            models.Index(
                fields=["library", "is_active", "display_order"],
                name="idx_library_image_order",
            )
        ]

    def __str__(self):
        return f"{self.library_id}:{self.media_asset_id}"
