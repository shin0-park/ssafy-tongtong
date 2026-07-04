# 도서관 나들이 Django 개발 명세서

- 문서 버전: 2.0
- 작성 기준일: 2026-06-22
- 기준 ERD: `library_outing_ERD_v2.md`
- 대상: Django REST API 백엔드, 데이터 import·동기화 작업, 추천·개인화 서비스
- 1차 서비스 범위: 부산 지역 MVP, 전국 확장 가능한 코드 구조

---

## 1. 목적과 전제

이 문서는 다음 기능을 Django로 구현하기 위한 개발 기준이다.

1. 날짜별 추천 테마에 따른 홈 TOP 1~3
2. 6개 방문 목적별 도서관 추천
3. 도서관 검색·상세·일자별 운영 여부 조회
4. 도서 검색과 소장 도서관·대출 가능 여부 조회
5. 전국·부산·특정 도서관 인기 대출 도서 목록
6. 문화 프로그램과 개최 도서관 통합 조회
7. 도서관 기반 후기 커뮤니티와 관련 책·프로그램 연결
8. 도서관·책·프로그램·후기 저장과 작성 후기 조회
9. 프로필·프로필 설정, 선호 지역·선호 태그 체크리스트
10. 공통 태그를 기준으로 한 행동 기반 사용자 성향 집계
11. 도서관 유형·프로그램 분류·후기 상태별 대체 이미지
12. 공휴일·도서관·프로그램·인기 도서 데이터의 예약 갱신과 파생 데이터 생성

서비스 내부 프로그램 신청·예약·결제·참여 이력, 실시간 열람실 잔여좌석, 후기 자동 텍스트 태깅, AI가 직접 정하는 추천 순위는 범위에 포함하지 않는다.

### 1.1 고정 정책

- 가입 시 이메일·닉네임·비밀번호만 입력받는다.
- `User`에 기본 지역이나 현재 좌표를 저장하지 않는다.
- 프로필 표시정보와 프로필 설정을 화면·API 책임상 구분한다.
- 사용자가 직접 고른 선호 지역·태그는 프로필 설정에서 관리한다.
- 수동 선호는 행동 신호 수가 적어도 추천 보너스로 사용할 수 있다.
- 행동 기반 개인화는 설정된 최소 신호 수를 충족하고 `UserPreference.status=ready`일 때만 사용한다.
- 태그는 도서관 전용 필드가 아니라 도서관·책·프로그램·후기의 공통 선호 집계 기준이다.
- `nearby`, `open_now`, `loan_available`, 현재 인기 순위는 영구 태그로 저장하지 않는다.
- 실시간 열람실 API와 관련 모델·캐시·endpoint를 구현하지 않는다.
- 전국도서관표준데이터의 `열람좌석수`는 정적 통계로 사용한다.
- 프로그램은 한 원천 게시물 또는 한 운영기간을 한 행으로 저장하며 `ProgramSession`을 만들지 않는다.
- 같은 이름의 프로그램이라도 날짜나 원천 게시물이 다르면 별도 프로그램이다.
- 사용자가 저장한 후기는 `UserReviewSave`, 사용자가 작성한 후기는 `UserReview.user`로 구분한다.
- 공식·시스템 이미지와 사용자 업로드 이미지를 구분한다.
- 대체 이미지는 엔터티별 실제 이미지 관계로 저장하지 않고 응답 시 규칙으로 해석한다.
- 브라우저 좌표는 현재 요청에서만 거리 계산에 사용하고 DB·분석 로그에 원문을 저장하지 않는다.
- 홈 추천은 매일 생성한 기본 후보를 사용하며 실시간 좌석이나 방문자 수를 사용하지 않는다.

---

## 2. 권장 기술 스택

프로젝트 제공 환경과의 호환성을 우선한다.

| 항목 | 권장안 | 비고 |
|---|---|---|
| Python | 3.11 | 프로젝트 명세 기준 |
| Django | `>=5.2,<5.3` | 5.2 계열 |
| Django REST Framework | `>=3.16,<3.17` | REST API |
| PostgreSQL | 16 이상 권장 | JSONB, 조건부 인덱스, trigram 검색 |
| Redis | 7 이상 권장 | 응답 캐시, 분산락, Celery broker |
| Celery | `>=5.6,<5.7` | 예약 수집·추천·성향 계산 |
| Vue | 3 | SPA를 선택하는 경우 |

### 2.1 주요 패키지

```text
Django>=5.2,<5.3
djangorestframework>=3.16,<3.17
djangorestframework-simplejwt>=5.3,<6
django-filter>=25,<26
drf-spectacular>=0.28,<1
psycopg[binary]>=3.2,<4
celery[redis]>=5.6,<5.7
redis>=5,<7
httpx>=0.28,<1
Pillow>=11,<13
django-cors-headers>=4.7,<5
django-environ>=0.12,<1
pytest>=8,<10
pytest-django>=4.10,<5
respx>=0.22,<1
factory-boy>=3.3,<4
```

선택 패키지:

- 객체 스토리지: `django-storages`, `boto3`
- 주소·문자열 정제: `rapidfuzz`, `python-dateutil`
- 운영 모니터링: Sentry SDK
- PostgreSQL 검색: `pg_trgm`

---

## 3. 프로젝트 구조

```text
library_outing/
├─ manage.py
├─ pyproject.toml
├─ config/
│  ├─ settings/
│  │  ├─ base.py
│  │  ├─ local.py
│  │  ├─ test.py
│  │  └─ production.py
│  ├─ urls.py
│  ├─ celery.py
│  ├─ asgi.py
│  └─ wsgi.py
├─ apps/
│  ├─ common/
│  ├─ tags/
│  ├─ accounts/
│  ├─ media_assets/
│  ├─ libraries/
│  ├─ books/
│  ├─ programs/
│  ├─ community/
│  ├─ myoutings/
│  ├─ preferences/
│  ├─ recommendations/
│  └─ integrations/
├─ tests/
│  ├─ fixtures/
│  │  ├─ library_standard/
│  │  ├─ data4library/
│  │  ├─ programs/
│  │  ├─ holidays/
│  │  └─ media/
│  └─ contract/
└─ scripts/
```

### 3.1 앱 책임

| 앱 | 책임 |
|---|---|
| `common` | 공통 추상 모델, 예외, 페이지네이션, 응답 포맷, 날짜·지역 유틸리티 |
| `tags` | 공통 `Tag` 어휘, seed fixture, 태그 조회 API |
| `accounts` | 이메일 인증 사용자, 프로필, 선호 지역·선호 태그 설정 |
| `media_assets` | 공식·시스템 이미지, 라이선스, 대체 이미지 규칙 |
| `libraries` | 도서관·운영시간·휴관·통계·시설·도서관 태그·이미지 연결 |
| `books` | 책·책 태그·소장·복본·대출 가능·인기 도서 |
| `programs` | 문화 프로그램·프로그램 태그·이미지 연결 |
| `community` | 후기·후기 이미지·후기 태그·관련 책·프로그램 |
| `myoutings` | 저장한 도서관·책·프로그램·후기와 나의 나들이 조회 service |
| `preferences` | 행동 기반 자동 성향 상태·태그 점수 |
| `recommendations` | 방문 목적, 일일 추천 규칙·결과, 개인화 재정렬 |
| `integrations` | 외부 API client, provider adapter, JSON/file loader, normalizer |

`integrations`에는 영속 모델을 두지 않는다. 별도 `sources` 앱과 `DataSource`, `SourceSyncRun`, `LibrarySourceRecord`도 만들지 않는다.

### 3.2 모델 소유권

공통 태그 정의는 `tags.Tag`가 소유하지만 연결 모델은 원천 엔터티를 소유한 앱에 둔다.

```text
tags.Tag
├─ libraries.LibraryTag
├─ books.BookTag
├─ programs.ProgramTag
└─ community.ReviewTag
```

이 구조는 각 연결 행의 생명주기를 도메인 서비스가 관리하게 하고, 불필요한 migration 순환을 줄인다.

### 3.3 앱 의존 방향

```text
common
  ├─ tags
  ├─ media_assets
  └─ accounts → tags

libraries → tags, media_assets
books → libraries, tags
programs → libraries, tags, media_assets
recommendations → libraries, tags
community → accounts, libraries, books, programs, tags, recommendations
myoutings → accounts, libraries, books, programs, community
preferences → accounts, tags
```

교차 앱 FK는 문자열(`"tags.Tag"`)로 선언한다. 모델 모듈을 서로 직접 import하지 않는다.

---

## 4. 환경변수

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,api.example.com
DATABASE_URL=postgresql://user:password@db:5432/library_outing
REDIS_URL=redis://redis:6379/0

DATA4LIBRARY_BASE_URL=http://data4library.kr/api
DATA4LIBRARY_AUTH_KEY=

PUBLIC_HOLIDAY_API_BASE_URL=http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService
PUBLIC_HOLIDAY_API_SERVICE_KEY=
PUBLIC_HOLIDAY_LOOKAHEAD_YEARS=2
LIBRARY_SCHEDULE_LOOKAHEAD_DAYS=180

SERVICE_DEFAULT_SIDO=부산광역시
SERVICE_DEFAULT_SIGUNGU=
SERVICE_DEFAULT_REGION_CODE=21

PROGRAM_DATA_FILE=
PROGRAM_REFRESH_HOURS=24
LIBRARY_STANDARD_DATA_FILE=
LIBRARY_FACILITY_DATA_FILE=
LIBRARY_IMAGE_DATA_FILE=

PERSONALIZATION_MIN_SIGNALS=20
PERSONALIZATION_BEHAVIOR_MAX_BONUS_RATIO=0.25
PERSONALIZATION_MANUAL_TAG_MAX_BONUS_RATIO=0.15
PERSONALIZATION_MANUAL_REGION_MAX_BONUS_RATIO=0.10
PREFERENCE_REBUILD_DEBOUNCE_SECONDS=45
DAILY_RECOMMENDATION_CANDIDATE_LIMIT=20

MEDIA_STORAGE_BACKEND=local
MEDIA_MAX_UPLOAD_MB=10
REVIEW_IMAGE_MAX_COUNT=5
AWS_STORAGE_BUCKET_NAME=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_ENDPOINT_URL=
```

보안 규칙:

- API 인증키를 프론트엔드에 노출하지 않는다.
- 로그에서 `authKey`, `serviceKey`, `ServiceKey`를 마스킹한다.
- production 이미지에 `.env` 파일을 포함하지 않는다.
- 외부 원문 응답 전체를 무조건 DB에 저장하지 않는다.
- 현재 좌표와 사용자 업로드 원본 URL을 불필요한 분석 로그에 남기지 않는다.

---

## 5. Django 설정 기준

```python
# config/settings/base.py
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": (
        "apps.common.pagination.StandardPageNumberPagination"
    ),
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}
```

- 외부 날짜·시간은 파싱 즉시 aware datetime 또는 명시적 `date`로 변환한다.
- 한국 기준일 계산에는 `ZoneInfo("Asia/Seoul")`를 명시한다.
- 이미지 MIME allowlist와 최대 파일 크기를 설정한다.
- 업로드 파일명은 신뢰하지 않고 UUID 기반 객체 키를 사용한다.

---

## 6. 모델 구현 명세

### 6.1 공통 추상 모델

```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

soft delete가 필요한 모델만 `deleted_at`, `is_visible`, `is_active`를 명시적으로 사용한다. 전역 soft-delete manager는 사용하지 않는다.

---

### 6.2 tags

#### Tag

권장 필드:

```python
class Tag(TimeStampedModel):
    code = models.SlugField(max_length=80, unique=True)
    label = models.CharField(max_length=80)
    tag_group = models.CharField(max_length=40, choices=TagGroup.choices)
    description = models.TextField(blank=True)
    is_profile_selectable = models.BooleanField(default=False)
    is_review_selectable = models.BooleanField(default=False)
    is_filterable = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
```

인덱스:

```python
models.Index(fields=["tag_group", "is_active", "display_order"])
```

검증:

- `code`는 의미가 바뀌어도 재사용하지 않는다.
- 프로필 설정 API는 `is_profile_selectable=True`만 허용한다.
- 후기 작성 API는 `is_review_selectable=True`만 허용한다.
- `nearby`, `open_now`, `loan_available`, `current_popular` 같은 동적 상태 태그 seed를 금지한다.

---

### 6.3 accounts

#### User

가입 입력은 이메일·닉네임·비밀번호다. 이메일을 로그인 ID로 사용한다.

```python
class User(AbstractUser, TimeStampedModel):
    username = None
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
```

`BaseUserManager` 기반 커스텀 manager를 구현하여 `create_user(email, password, **extra_fields)`와 `create_superuser`를 제공한다.

금지 필드:

- `default_sido`
- `default_sigungu`
- 현재 위도·경도

#### UserProfile

- `user`: OneToOne, `CASCADE`
- `profile_image`: `ImageField(null=True, blank=True)`
- `profile_image_alt`: `CharField(max_length=200, blank=True)`
- `bio`: `CharField(max_length=300, blank=True)`

회원가입 transaction 안에서 profile을 함께 생성한다. signal에만 의존하지 않는다.

#### UserPreferredRegion

- `user`: FK `CASCADE`
- `region_key`: `CharField(max_length=30)`
- `sido`: `CharField(max_length=30)`
- `sigungu`: `CharField(max_length=30, blank=True)`
- `weight`: `DecimalField(max_digits=5, decimal_places=4, default=1)`
- `display_order`: `PositiveSmallIntegerField(default=0)`
- `is_active`: `BooleanField(default=True)`

제약:

```python
models.UniqueConstraint(
    fields=["user", "region_key"],
    name="uq_user_preferred_region",
)
```

프론트엔드는 숫자 weight를 직접 편집하지 않는다. 체크 여부와 순서만 전달하고 기본 weight는 서비스가 정한다.

#### UserPreferredTag

- `user`: FK `CASCADE`
- `tag`: FK `tags.Tag`, `PROTECT`
- `weight`: `DecimalField(max_digits=5, decimal_places=4, default=1)`
- `is_active`: `BooleanField(default=True)`

제약:

```python
models.UniqueConstraint(
    fields=["user", "tag"],
    name="uq_user_preferred_tag",
)
```

`clean()` 또는 serializer validation에서 `tag.is_profile_selectable`을 확인한다.

---

### 6.4 media_assets

#### MediaAsset

- `asset_origin`: `official_external|system_default|admin_upload`
- `original_url`: `URLField(blank=True)`
- `file`: `FileField(blank=True)`
- `source_name`, `source_page_url`, `source_asset_id`
- `checksum`, `mime_type`, `width`, `height`
- `license_code`, `attribution_text`
- `commercial_use_allowed`, `modification_allowed`: nullable boolean
- `license_verified_at`: nullable datetime
- `is_active`: boolean

`CheckConstraint` 또는 model validation으로 `original_url`과 `file` 중 하나 이상을 요구한다.

사용자 후기·프로필 업로드는 `MediaAsset`에 넣지 않는다. 해당 도메인의 `ImageField`에서 관리한다.

#### DefaultMediaAssetRule

- `target_domain`: `library|program|review|profile`
- `target_code`: `CharField(max_length=80, default="default")`
- `media_asset`: FK `PROTECT`
- `priority`: `PositiveSmallIntegerField(default=100)`
- `is_active`: boolean

조건부 unique:

```python
models.UniqueConstraint(
    fields=["target_domain", "target_code", "priority"],
    condition=Q(is_active=True),
    name="uq_active_default_media_rule",
)
```

관리자 seed에는 최소 다음 키가 있어야 한다.

```text
library/public
library/small
library/children
library/other
library/default
program/lecture_humanities
program/reading_writing
program/culture_art
program/experience_education
program/exhibition
program/other
program/default
review/default
profile/default
```

---

### 6.5 libraries

#### Library

- 좌표: `DecimalField(max_digits=10, decimal_places=7, null=True)`
- 홈페이지: `URLField(blank=True)`
- `library_type`: 정규화 코드
- `library_type_raw`: 원천 문구
- `is_active`: `BooleanField(default=True, db_index=True)`

인덱스:

```python
models.Index(fields=["sido", "sigungu", "library_type", "is_active"])
models.Index(fields=["normalized_name"])
```

`pg_trgm`을 사용하는 경우 `normalized_name`, `normalized_address`에 trigram GIN index를 추가한다.

#### LibraryExternalIdentifier

```python
models.UniqueConstraint(
    fields=["provider_code", "code_type", "external_code"],
    name="uq_library_external_identifier",
)
```

`provider_code`는 문자열 코드로 저장한다. 별도 DataSource FK를 사용하지 않는다.

#### LibraryOpeningHour

- `day_type`: `day_of_week|public_holiday|specific_date`
- `schedule_status`: `open|closed|unknown`
- `sequence`: 다중 운영 구간 지원
- `closes_next_day`: 익일 종료
- `provider_code`, `source_url`, `source_reference_date`, `fetched_at`

검증:

- `day_type=day_of_week`이면 `day_of_week` 필수, `specific_date`는 null
- `day_type=specific_date`이면 `specific_date` 필수
- `schedule_status=open`이면 open/close time 필수

#### LibraryClosureRule

`normalized_rule`은 JSON으로 보존하지만, rule parser는 version을 가진 순수 함수로 작성한다.

우선순위:

1. 특정 날짜 일정
2. 임시·장기 휴관
3. 명절·공휴일 휴관
4. 주차별·요일별 정기 휴관
5. 일반 운영시간

#### PublicHoliday

- `(date, holiday_code)` unique
- `provider_code`, `source_url`, `fetched_at`
- `date`, `is_public_holiday` 복합 인덱스

#### LibraryDailySchedule

- `(library, date)` unique
- `status=open|closed|unknown`
- 운영 규칙·공휴일이 바뀌면 해당 날짜 범위를 재생성
- 과거 행은 최근 30일 정도만 유지해도 된다.

#### LibraryStatisticSnapshot

- `reading_seat_count`는 정적 총 좌석 수
- `book_count`, `serial_count`, `non_book_count`, 대출 정책, 면적은 nullable
- unique `(library, provider_code, reference_date)`
- 도서관별 `is_current=True` 조건부 unique 권장

#### LibraryFacility

```python
class FacilityStatus(models.TextChoices):
    AVAILABLE = "available", "이용 가능"
    UNAVAILABLE = "unavailable", "이용 불가"
    UNKNOWN = "unknown", "미확인"
```

- unique `(library, facility_type)`
- 검색 필터는 `status=available`, `is_active=True`만 사용
- 원천 필드 누락을 `unavailable`로 변환하지 않음

#### LibraryTag

- FK: `library`, `tag`
- `source_method`: `field_rule|facility_rule|program_rollup|review_rollup|book_rollup|manual`
- `source_field`, `score`, `confidence`, `evidence_url`, `is_active`
- unique `(library, tag, source_method)`

`program_rollup`, `review_rollup`, `book_rollup`은 배치 또는 이벤트 기반으로 재계산한다.

#### LibraryImage

- FK: `library`, `media_asset`
- `image_type`, `is_main`, `display_order`, `caption`
- 활성 대표 이미지는 도서관당 하나만 허용

fallback asset을 `LibraryImage`로 생성하지 않는다.

---

### 6.6 books

#### Book

- `isbn13`: `CharField(max_length=13, null=True, blank=True)`
- 숫자형 ISBN 금지
- ISBN이 있는 행에 조건부 unique
- KDC 번호와 명칭 보존
- `provider_code`, `metadata_fetched_at`

#### BookTag

- `source_method`: `kdc_rule|metadata_rule|manual`
- unique `(book, tag, source_method)`
- KDC 기반 태그 생성은 idempotent service로 구현
- 인기 순위는 태그로 생성하지 않음

#### LibraryHolding

- unique `(library, book)`
- `provider_code`, `first_seen_at`, `last_verified_at`, `is_active`

#### LibraryHoldingCopy

- unique `(holding, provider_code, external_copy_key)`
- 복본·청구기호 API를 사용하지 않는 배포에서는 테이블을 비워 둘 수 있음

#### BookAvailabilitySnapshot

- 인덱스 `(library, book, -fetched_at)`
- `source_effective_date`, `fetched_at`, `fresh_until`을 모두 응답 가능하게 보존
- `holding`이 있으면 holding의 library/book과 일치하는지 service에서 검증

#### PopularBookSnapshot, PopularBookItem

- snapshot query condition을 정규화한 `query_hash` 사용
- item unique `(snapshot, rank)`, `(snapshot, book)`
- 동일 조건의 최신 fresh snapshot을 우선 반환

---

### 6.7 programs

#### Program

- `provider_code`: 제공처 문자열
- `external_program_key`: 외부 ID 또는 안정적 해시
- unique `(provider_code, external_program_key)`
- 날짜 필드는 `DateField`를 우선 사용
- 분류 코드:
  - `lecture_humanities`
  - `reading_writing`
  - `culture_art`
  - `experience_education`
  - `exhibition`
  - `other`
- `target_codes`: JSON list
- `application_status_raw`: 원천 표시 문구만 보존
- `is_canceled`: 원천에서 명시된 취소만 true
- `is_visible`, `deleted_at`: soft delete

외부 ID가 없을 때 해시 입력:

```text
normalized_library_id
+ normalized_title
+ operation_start_date
+ operation_end_date
+ normalized_source_url
```

`ProgramSession` 모델은 만들지 않는다. 같은 제목이 반복되어도 운영기간·게시물이 다르면 별도 `Program`이다.

#### ProgramTag

- `source_method`: `category_rule|target_rule|metadata_rule|manual`
- unique `(program, tag, source_method)`

#### ProgramImage

- FK: `program`, `media_asset`
- 프로그램별 활성 대표 이미지 하나
- 이미지가 없으면 `category_code` 기반 fallback 해석

---

### 6.8 community

#### UserReview

- FK: `user`, `library`, nullable `purpose`
- `rating`: 1~5 `CheckConstraint`
- `content`: 필수
- `moderation_status`: `pending|visible|hidden`
- 인덱스:
  - `(library, moderation_status, -created_at)`
  - `(user, -created_at)`

#### UserReviewImage

- 사용자 업로드 `ImageField`
- 후기당 최대 이미지 수는 service에서 제한
- 삭제 시 storage 객체 정리 task 실행
- 이미지가 0개면 review fallback을 응답에서 해석

#### ReviewBookReference

- unique `(review, book)`
- 한 후기의 관련 책 수에 상한을 둔다. MVP 권장 최대 5권.

#### ReviewProgramReference

- unique `(review, program)`
- 한 후기의 관련 프로그램 수에 상한을 둔다. MVP 권장 최대 5개.

#### ReviewTag

- `source_method`: `user_selected|moderator`
- unique `(review, tag)`
- MVP에서 자동 텍스트 모델 값은 저장하지 않는다.
- serializer에서 `tag.is_review_selectable=True` 검증

후기 저장 transaction 순서:

1. `UserReview` 생성·수정
2. 관련 책·프로그램 관계 replace
3. 선택 태그 replace
4. 이미지 검증·저장
5. commit 후 preference rebuild 예약
6. 필요 시 대상 도서관의 review rollup tag 재계산 예약

---

### 6.9 myoutings

#### 저장 모델

```text
UserLibrarySave(user, library, memo)
UserBookSave(user, book, memo)
UserProgramSave(user, program, memo)
UserReviewSave(user, review, memo)
```

각 모델은 `(user, 대상)` unique를 가진다.

업무 규칙:

- PUT은 idempotent upsert로 구현한다.
- DELETE는 저장 행을 제거한다.
- 프로그램 저장은 신청·참여 상태가 아니다.
- hidden 후기의 신규 저장은 금지하고, 이미 저장된 후기가 hidden 처리되면 목록에서 비노출 또는 상태 표시한다.
- 자신의 후기를 `UserReviewSave`로 저장하는 요청은 409 또는 validation error로 거절하는 것을 권장한다.
- 작성 후기는 별도 저장 모델 없이 `UserReview.objects.filter(user=request.user)`로 조회한다.
- 저장 생성·삭제는 `transaction.on_commit()`에서 preference rebuild를 예약한다.

---

### 6.10 preferences

#### UserPreference

- OneToOne `user`
- `status`: `collecting|pending|ready|failed`
- `signal_count`
- `library_signal_count`, `book_signal_count`, `program_signal_count`, `review_signal_count`
- `algorithm_version`, `eligible_since`, `calculated_at`, `failure_message`

행동 신호 정의:

```text
현재 UserLibrarySave 수
+ 현재 UserBookSave 수
+ 현재 UserProgramSave 수
+ 현재 UserReviewSave 수
+ 공개 가능한 본인 UserReview 수
```

자신의 후기 저장을 막아 중복 신호를 줄인다. 수동 선호 지역·태그는 `signal_count`에 포함하지 않는다.

#### UserPreferenceItem

- FK: `user_preference`, `tag`
- `score`, `count`, `rank`
- `source_count_library`, `source_count_book`, `source_count_program`, `source_count_review`
- unique `(user_preference, tag)`

문자열 `item_type`, `item_code`, `item_label`은 사용하지 않는다. 표시명과 그룹은 `Tag`에서 조회한다.

상태 전이:

```text
signal_count < threshold           → collecting
signal_count >= threshold, 예약됨  → pending
계산 성공                          → ready
계산 실패                          → failed
```

신호가 threshold 아래로 내려가면 자동 성향 항목을 제거하거나 비활성화하고 `collecting`으로 되돌린다. 프로필에서 직접 고른 선호는 그대로 유지한다.

---

### 6.11 recommendations

#### Purpose, PurposeTagRule, PurposeMetricRule

- `Purpose.code` unique
- `PurposeTagRule` unique `(purpose, tag)`
- `PurposeMetricRule` unique `(purpose, metric_code)`
- 규칙의 normalization JSON schema를 코드에서 검증

#### DailyRecommendationTheme, DailyRecommendationMetricRule

- theme code unique
- theme별 metric unique
- 날짜 순환에 사용되는 `display_order`

#### DailyLibraryRecommendationSet, DailyLibraryRecommendationItem

- set unique `(recommendation_date, theme, region_key, algorithm_version)`
- item unique `(set, rank)`, `(set, library)`
- 사용자별 결과 행은 저장하지 않음

---

## 7. 태그 파이프라인 명세

### 7.1 기본 원칙

태그 파이프라인은 다음 세 층을 분리한다.

```text
원천 필드·관계
→ 도메인별 태그 연결
→ 사용자 행동 기반 UserPreferenceItem
```

도메인 엔터티의 원천값과 사용자 선호 점수를 같은 테이블에 저장하지 않는다.

### 7.2 도메인 태그 생성 서비스

권장 service 함수:

```text
libraries.services.tags.rebuild_library_direct_tags(library_id)
libraries.services.tags.rebuild_library_program_rollup(library_id)
libraries.services.tags.rebuild_library_review_rollup(library_id)
books.services.tags.rebuild_book_tags(book_id)
programs.services.tags.rebuild_program_tags(program_id)
community.services.tags.replace_review_tags(review_id, tag_ids)
```

모든 rebuild 함수는 같은 입력에 여러 번 실행해도 결과가 같아야 한다.

### 7.3 직접 태그 예시

| 원천 | 규칙 | 태그 |
|---|---|---|
| 도서관 유형 | `public` | `public_library` |
| 정적 좌석 수 | percentile/구간 | `many_seats` |
| 장서 수 | percentile/구간 | `rich_collection` |
| 운영 종료시간 | 설정 기준 이상 | `late_open` |
| 시설 available | children room | `children_room`, `children_friendly` |
| 책 KDC | 문학 | `book_literature` |
| 책 KDC | 과학 | `book_science` |
| 프로그램 분류 | 독서/글쓰기 | `program_reading_writing` |
| 프로그램 대상 | 가족 | `for_family` |
| 후기 선택 | 조용함 | `quiet` |

### 7.4 도서관 rollup

도서관 추천 후보가 여러 도메인 태그와 비교될 수 있도록 다음 rollup을 지원한다.

- 노출 중인 프로그램의 `ProgramTag` → `LibraryTag(source_method=program_rollup)`
- 공개 후기의 `ReviewTag` → `LibraryTag(source_method=review_rollup)`
- 충분한 소장·인기 데이터가 있을 때 `BookTag` → `LibraryTag(source_method=book_rollup)`

rollup 계산에는 최소 표본수, decay, 상한을 둔다. 후기 1건의 태그가 도서관 전체 특징으로 과대해석되지 않게 한다.

### 7.5 사용자 행동 태그 집계

입력별 기본 기여 원천:

| 행동 | 태그 원천 |
|---|---|
| 도서관 저장 | `LibraryTag` |
| 책 저장 | `BookTag` |
| 프로그램 저장 | `ProgramTag` |
| 후기 저장 | `ReviewTag` + 관련 책·프로그램 태그 + 대상 도서관 태그 |
| 후기 작성 | 선택 `ReviewTag` + 관련 책·프로그램 태그 + 대상 도서관 태그 |

가중치는 코드 상수 또는 버전 관리 설정으로 둔다. 사용자에게 임의 숫자 입력 UI를 제공하지 않는다.

동일 상호작용에서 같은 태그가 여러 경로로 도달하면 deduplicate 후 한 번만 기여시키거나 경로별 합계 상한을 적용한다.

---

## 8. 이미지·대체 이미지 처리

### 8.1 해석 서비스

권장 interface:

```python
@dataclass(frozen=True)
class ResolvedImage:
    url: str | None
    is_fallback: bool
    fallback_key: str | None
    attribution_text: str | None
    license_code: str | None


def resolve_library_image(library) -> ResolvedImage: ...
def resolve_program_image(program) -> ResolvedImage: ...
def resolve_review_image(review) -> ResolvedImage: ...
def resolve_profile_image(profile) -> ResolvedImage: ...
```

### 8.2 해석 순서

도서관:

```text
활성 대표 LibraryImage
→ library/{library_type}
→ library/default
→ null
```

프로그램:

```text
활성 대표 ProgramImage
→ program/{category_code}
→ program/default
→ null
```

후기:

```text
첫 UserReviewImage
→ review/default
→ null
```

프로필:

```text
UserProfile.profile_image
→ profile/default
→ null
```

### 8.3 응답 규칙

```json
{
  "url": "/media/defaults/library-public.webp",
  "is_fallback": true,
  "fallback_key": "library/public",
  "attribution_text": null,
  "license_code": "internal"
}
```

fallback을 실제 `LibraryImage`나 `ProgramImage`로 오인하지 않도록 `is_fallback`을 명시한다.

### 8.4 라이선스

- 공식 이미지에는 source page, attribution, license를 보존한다.
- 변경 불가 라이선스는 임의 crop을 금지한다.
- 시스템 기본 이미지는 프로젝트 내부 사용권을 확인한 파일만 사용한다.
- 사용자 후기·프로필 이미지는 공식 이미지 attribution UI에 섞지 않는다.

---

## 9. 외부 데이터 통합 구조

뷰와 serializer는 외부 API를 직접 호출하지 않는다.

```text
API View
→ domain service
→ integrations client/loader
→ normalizer
→ domain model upsert
```

### 9.1 공통 HTTP client 정책

- connect/read timeout 분리
- 최대 재시도와 지수 backoff
- 429 `Retry-After` 준수
- provider별 concurrency 제한
- 인증키 마스킹
- XML/JSON content type 검증
- 응답 schema 검증
- request ID와 provider code를 구조화 로그에 기록

### 9.2 Data4LibraryClient

권장 메서드:

```python
search_books(...)
get_book_detail(isbn13: str)
find_libraries_by_book(isbn13: str, region: str, detail_region: str | None)
get_book_availability(lib_code: str, isbn13: str)
get_library_items(lib_code: str, isbn13: str)
get_popular_books(...)
get_popular_books_by_library(...)
search_libraries(...)
```

검증:

- ISBN은 문자열로 받는다.
- search 조건이 비어 전체 검색이 되는 요청은 명시적으로 허용한 경우만 보낸다.
- `dtl_region`을 쓰는 경우 region 다중선택 규칙을 검증한다.
- API key는 cache key에서 제외한다.

normalizer 반환 객체는 Django model이 아닌 dataclass 또는 TypedDict로 둔다.

### 9.3 프로그램 loader/provider

현재 JSON 데이터 형식에 맞는 loader를 우선 구현한다.

```python
class ProgramProvider(Protocol):
    def fetch(self) -> Iterable[RawProgram]: ...

class JsonFileProgramProvider:
    ...
```

정규화:

- `program_type` → `category_code`
- `target` → `target_text`, `target_codes`
- 날짜 문자열 → `date`
- `application_status` → `application_status_raw`
- 외부 ID가 없으면 안정적 해시 생성

프로그램 upsert 뒤 `ProgramTag`와 개최 도서관의 program rollup을 재계산한다.

### 9.4 PublicHolidayClient

- 연도별 공식 특일 정보를 수집
- `(date, holiday_code)` upsert
- 변경된 연도의 `LibraryDailySchedule` 재생성 예약

### 9.5 파일 import

별도 raw staging DB 모델을 사용하지 않는다.

```text
파일 읽기
→ schema validation
→ 부산 필터
→ 정규화
→ domain upsert
→ reject report 파일
→ 구조화 로그·통계 출력
→ 관련 태그·운영표 재생성
```

### 9.6 공식 이미지 import

- URL, 출처 페이지, license code를 검증
- `MediaAsset` upsert
- 도서관·프로그램에 실제 관계가 있을 때 연결 모델 생성
- 이미지가 없는 엔터티에는 연결 행 대신 기본 규칙 사용

---

## 10. REST API 명세

기본 prefix: `/api/v1`

### 10.1 공통 응답

목록:

```json
{
  "count": 24,
  "next": "/api/v1/libraries?page=2",
  "previous": null,
  "results": []
}
```

오류:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "요청 값을 확인해 주세요.",
  "details": {},
  "request_id": "01J..."
}
```

주요 오류 코드:

- `VALIDATION_ERROR`
- `AUTHENTICATION_REQUIRED`
- `PERMISSION_DENIED`
- `NOT_FOUND`
- `CONFLICT`
- `UPSTREAM_UNAVAILABLE`
- `UPSTREAM_RATE_LIMITED`
- `EXTERNAL_MAPPING_MISSING`
- `STALE_DATA_ONLY`

---

### 10.2 인증

| Method | URL | 인증 | 설명 |
|---|---|---|---|
| POST | `/auth/signup/` | 없음 | 이메일·닉네임·비밀번호 가입 |
| POST | `/auth/token/` | 없음 | JWT 발급 |
| POST | `/auth/token/refresh/` | 없음 | access 갱신 |

회원가입 body:

```json
{
  "email": "user@example.com",
  "password": "...",
  "nickname": "책소풍"
}
```

가입 API에서 지역·태그·프로필 이미지를 필수로 받지 않는다.

---

### 10.3 프로필 화면과 프로필 설정

#### 프로필 화면

| Method | URL | 설명 |
|---|---|---|
| GET | `/profile/me/` | 닉네임·프로필 이미지·자기소개·활동 요약 |
| PATCH | `/profile/me/` | 닉네임·프로필 이미지·자기소개 수정 |

`PATCH`는 `multipart/form-data`를 허용한다.

응답 예시:

```json
{
  "email": "user@example.com",
  "nickname": "책소풍",
  "bio": "주말마다 도서관에 갑니다.",
  "profile_image": {
    "url": "/media/defaults/profile.webp",
    "is_fallback": true,
    "fallback_key": "profile/default"
  },
  "activity_summary": {
    "saved_libraries": 4,
    "saved_books": 8,
    "saved_programs": 2,
    "saved_reviews": 3,
    "authored_reviews": 2
  }
}
```

#### 프로필 설정

| Method | URL | 설명 |
|---|---|---|
| GET | `/profile/me/preference-settings/` | 현재 선호 지역·태그와 선택 가능 목록 |
| PUT | `/profile/me/preferred-regions/` | 체크된 지역 목록 전체 교체 |
| PUT | `/profile/me/preferred-tags/` | 체크된 태그 목록 전체 교체 |

선호 태그 요청:

```json
{
  "tag_ids": [11, 24, 38]
}
```

선호 지역 요청:

```json
{
  "regions": [
    {"region_key": "21:21090", "display_order": 1},
    {"region_key": "21:21100", "display_order": 2}
  ]
}
```

사용자는 숫자 가중치를 직접 입력하지 않는다. 서버가 기본 가중치를 정한다.

프로필 설정 변경 뒤 일일 추천 세트를 재생성할 필요는 없다. 요청 시 개인화 재정렬에서 즉시 반영한다.

---

### 10.4 기준정보·태그

| Method | URL | 설명 |
|---|---|---|
| GET | `/purposes/` | 6개 방문 목적 |
| GET | `/tags/` | 공통 태그 목록 |
| GET | `/metadata/regions/` | 지역 체크리스트 |
| GET | `/metadata/library-types/` | 도서관 유형 |
| GET | `/metadata/facilities/` | 시설 코드 |
| GET | `/metadata/program-categories/` | 프로그램 분류 |

`/tags/` query:

- `group`
- `profile_selectable=true`
- `review_selectable=true`
- `filterable=true`

---

### 10.5 홈 추천

#### GET `/home/daily-recommendations/`

Query:

| 이름 | 필수 | 설명 |
|---|---|---|
| `sido`, `sigungu` | 아니오 | 명시적 검색 지역 |
| `lat`, `lng` | 아니오 | 거리 계산용 현재 좌표 |

기본 후보 지역 결정:

1. 요청의 `sido`, `sigungu`
2. 서비스 기본 지역

`UserPreferredRegion`은 검색 지역을 강제로 대체하지 않고 후보 점수 보너스로 사용한다.

처리:

1. 날짜·지역의 `DailyLibraryRecommendationSet` 조회
2. 없으면 최근 성공 세트 fallback 또는 동기 최소 계산
3. 기본 후보 상위 3개 선택
4. 인증 사용자의 수동 선호 태그·지역 보너스 적용
5. `UserPreference.status=ready`이면 행동 성향 보너스 적용
6. 같은 기본 후보 집합 안에서만 재정렬

응답 예시:

```json
{
  "recommendation_date": "2026-06-22",
  "theme": {
    "code": "late_open",
    "label": "오늘은 늦게까지 이용하기 좋은 도서관"
  },
  "region": {"sido": "부산광역시", "sigungu": null},
  "personalization": {
    "manual_preferences_applied": true,
    "behavior_preferences_applied": false,
    "behavior_status": "collecting",
    "signal_count": 12,
    "required_count": 20
  },
  "results": [
    {
      "rank": 1,
      "library": {
        "id": 101,
        "name": "연제도서관",
        "main_image": {
          "url": "/media/defaults/library-public.webp",
          "is_fallback": true
        }
      },
      "score": 88.4,
      "distance_m": 2310,
      "reasons": ["오늘 늦게까지 운영해요", "선호 태그와 잘 맞아요"]
    }
  ]
}
```

#### GET `/home/recommendations/`

Query:

- `purpose=study|book|kids|program|mood|nearby`
- `sido`, `sigungu`
- `lat`, `lng`
- `limit` 기본 6, 최대 20

목적 기본 점수 뒤 수동 선호와 준비 완료 행동 성향을 제한된 범위에서 더한다.

---

### 10.6 도서관

#### GET `/libraries/`

필터:

- `q`: 도서관명·주소
- `sido`, `sigungu`
- `library_type`: 다중값
- `facility`: 다중값
- `facility_mode=and|or`
- `tag`: 다중값
- `open_now=true`
- `weekend_open=true`
- `holiday_open=true`
- `late_open_after=21:00`
- `min_book_count`
- `min_seat_count`
- `lat`, `lng`, `radius_m`
- `ordering=distance|name|-book_count|-reading_seat_count|-review_rating`

`open_now`는 `LibraryDailySchedule`과 현재 시각으로 계산한다. 외부 API를 호출하지 않는다.

카드 응답:

```json
{
  "id": 101,
  "name": "연제도서관",
  "library_type": "public",
  "address": "부산광역시 ...",
  "coordinates": {"latitude": 35.0, "longitude": 129.0},
  "today_hours": {"status": "open", "open": "09:00", "close": "21:00"},
  "is_open_now": true,
  "latest_statistics": {
    "reference_date": "2026-05-18",
    "reading_seat_count": 220,
    "book_count": 115000
  },
  "facilities": ["reading_room", "wifi", "parking"],
  "tags": [{"code": "many_seats", "label": "열람좌석이 많아요"}],
  "main_image": {
    "url": "/media/defaults/library-public.webp",
    "is_fallback": true,
    "fallback_key": "library/public"
  },
  "distance_m": 2310,
  "is_saved": false
}
```

#### GET `/libraries/{id}/`

포함:

- 기본정보
- 오늘·주간 운영표
- 휴관 원문과 판정 사유
- 최신 정적 통계와 기준일
- 시설과 도서관 태그
- 실제 또는 대체 이미지·출처
- 예정 프로그램
- 후기 요약
- 정보나루 외부 코드 연계 여부

실시간 열람실 잔여좌석 endpoint는 제공하지 않는다.

---

### 10.7 책

#### GET `/books/search/`

Query:

- `search_type=title|author|isbn|keyword|publisher`
- `q`
- `exact`
- `sort=loan|title|author|pub|pubYear|isbn`
- `order=asc|desc`
- `page`, `page_size`

동일 쿼리는 Redis에 캐시하고 결과 도서를 bulk upsert한다. 검색 카드에 모든 소장 도서관을 강제로 붙이지 않는다.

#### GET `/books/{isbn13}/`

- fresh 메타데이터가 있으면 DB 반환
- 오래되었거나 상세가 없으면 정보나루 호출 후 갱신
- upstream 실패 시 기존 데이터가 있으면 stale 표시
- `BookTag`를 함께 반환 가능

#### GET `/books/{isbn13}/libraries/`

Query:

- `region` 기본 `21`
- `detail_region`
- `lat`, `lng`
- `include_availability=true|false`
- `availability_limit`

대출 가능 여부를 조회한 경우 기준일과 확인시각을 함께 반환한다.

#### GET `/popular-books/`

- `scope=national|region|library`
- 범위별 필수 파라미터 검증
- 최근 24시간 fresh snapshot 우선

---

### 10.8 프로그램

#### GET `/programs/`

필터:

- `q`: 프로그램명·도서관명
- `sido`, `sigungu`
- `library_id`
- `category`
- `target`
- `start_from`, `start_to`
- `ongoing_on`
- `tag`
- `ordering=operation_start_date|-operation_start_date|title`

응답 예시:

```json
{
  "id": 501,
  "title": "책 소풍 가는 날",
  "category": "reading_writing",
  "library": {"id": 101, "name": "부산진구어린이청소년도서관"},
  "target_text": "성인",
  "target_codes": ["adult"],
  "operation_start_date": "2026-06-10",
  "operation_end_date": "2026-06-24",
  "schedule_status": "ongoing",
  "application_status_raw": "신청가능",
  "source_url": "...",
  "image": {
    "url": "/media/defaults/program-reading-writing.webp",
    "is_fallback": true,
    "fallback_key": "program/reading_writing"
  },
  "is_saved": false
}
```

#### GET `/programs/{id}/`

프로그램 상세, 개최 도서관, 태그, 실제 또는 대체 이미지, 공식 원문 URL, 수집 시각을 반환한다. 회차 배열과 내부 신청 이력은 반환하지 않는다.

---

### 10.9 커뮤니티

#### GET `/reviews/`

필터:

- `library_id`
- `book_id`
- `program_id`
- `tag`
- `rating`
- `q`
- `ordering=-created_at|created_at|-rating`

기본 정렬은 최신순이다.

#### POST `/reviews/`

인증 필요. `multipart/form-data` 지원.

```json
{
  "library_id": 101,
  "purpose_id": 3,
  "rating": 5,
  "title": "아이와 가기 좋았어요",
  "content": "어린이자료실이 편했습니다.",
  "visited_at": "2026-06-20",
  "book_ids": [301],
  "program_ids": [501],
  "tag_ids": [41, 42]
}
```

- 후기당 도서관은 하나
- 관련 책·프로그램은 선택
- 태그는 `is_review_selectable=True`만 허용
- 이미지 최대 5장

#### GET/PATCH/DELETE `/reviews/{id}/`

- GET: 공개 후기
- PATCH/DELETE: 작성자 또는 관리자
- hidden 후기 저장·노출 정책 적용

#### PUT/DELETE `/my-outings/saved-reviews/{review_id}/`

후기 저장·해제. 자신의 후기 저장 요청은 거절한다.

후기 응답은 이미지가 없을 때 review fallback을 포함한다.

---

### 10.10 나의 나들이

| Method | URL | 설명 |
|---|---|---|
| GET | `/my-outings/saved-libraries/` | 저장 도서관 |
| PUT/DELETE | `/my-outings/saved-libraries/{library_id}/` | 저장·메모/해제 |
| GET | `/my-outings/saved-books/` | 저장 책 |
| PUT/DELETE | `/my-outings/saved-books/{book_id}/` | 저장·메모/해제 |
| GET | `/my-outings/saved-programs/` | 저장 프로그램 |
| PUT/DELETE | `/my-outings/saved-programs/{program_id}/` | 저장·메모/해제 |
| GET | `/my-outings/saved-reviews/` | 저장 후기 |
| PUT/DELETE | `/my-outings/saved-reviews/{review_id}/` | 저장·메모/해제 |
| GET | `/my-outings/authored-reviews/` | 작성 후기 |
| GET | `/my-outings/preference/` | 자동 성향 상태와 상위 태그 |
| GET | `/my-outings/summary/` | 전체 저장·작성 수 요약 |

`authored-reviews`는 `community.UserReview`를 조회하며 별도 모델을 만들지 않는다.

`/my-outings/preference/` 응답:

```json
{
  "behavior": {
    "status": "collecting",
    "enabled": false,
    "signal_count": 13,
    "required_count": 20,
    "breakdown": {
      "libraries": 3,
      "books": 5,
      "programs": 2,
      "reviews": 3
    },
    "calculated_at": null,
    "items": []
  },
  "manual": {
    "preferred_regions": ["21:21090"],
    "preferred_tags": [
      {"code": "quiet", "label": "조용한 곳"}
    ]
  }
}
```

나의 나들이는 설정 수정 화면이 아니다. 설정 링크를 제공할 수 있지만 실제 변경은 프로필 설정 API가 담당한다.

---

## 11. 추천 로직 명세

### 11.1 공통 후보군

```text
활성 도서관
∩ 요청 지역
∩ 추천 규칙의 필수 조건
∩ 좌표가 필요한 목적이면 좌표 보유 도서관
```

사용 데이터:

- `Library`
- `LibraryDailySchedule`
- 최신 `LibraryStatisticSnapshot`
- available `LibraryFacility`
- 활성 `LibraryTag`
- 향후 프로그램 수
- 후기 평균·개수
- 실제·대체 이미지 상태
- 요청 좌표와 거리
- `UserPreferredRegion`, `UserPreferredTag`
- 준비 완료된 `UserPreferenceItem`

사용하지 않는 데이터:

- 실시간 좌석·방문자 수
- 특정 도서 한 권의 대출 가능 여부
- 사용자의 영구 저장 현재 좌표

### 11.2 날짜별 TOP 1~3

활성 테마를 `display_order`로 정렬하고 날짜에 따라 결정한다.

```python
theme = active_themes[target_date.toordinal() % len(active_themes)]
```

무작위로 테마를 바꾸지 않는다.

Celery는 지역별 기본 후보를 최대 설정 수만큼 저장한다. 공개 응답은 상위 3개이며 사용자별 처리는 동일 후보 안의 재정렬만 수행한다.

### 11.3 목적별 기본 점수

```text
base_score = Σ(tag_rule.weight × candidate_tag_score)
           + Σ(metric_rule.weight × normalized_metric)
```

목적별 대표 입력:

| 목적 | 대표 태그·지표 |
|---|---|
| study | 정적 좌석 수, 조용함, Wi-Fi, 열람실, 늦은 운영 |
| book | 장서 수, 책 주제 관련 태그, 자료실·디지털실 |
| kids | 어린이자료실, 수유실, 가족·어린이 프로그램, 후기 태그 |
| program | 향후 프로그램 수, 프로그램 분류·대상 태그 |
| mood | 카페, 라운지, 야외공간, 분위기 후기 태그, 이미지·평점 |
| nearby | 거리, 해당 날짜 운영, 주차·접근성 |

### 11.4 수동 선호 보너스

수동 설정은 행동 threshold와 무관하게 적용할 수 있다.

```text
manual_tag_bonus = 선택 태그와 후보 도서관 태그의 일치도
manual_region_bonus = 후보 도서관 지역이 선호 지역과 일치하는 정도
```

- 프로필 체크만으로 기본 추천을 완전히 뒤집지 않도록 상한을 둔다.
- 사용자가 선호 지역을 선택해도 검색 범위를 강제로 제한하지 않는다.
- 추천 사유에는 실제 일치한 항목만 표시한다.

### 11.5 행동 기반 성향 계산

활성화 조건:

```text
library saves
+ book saves
+ program saves
+ review saves
+ visible authored reviews
>= PERSONALIZATION_MIN_SIGNALS
```

`UserPreferenceItem` 계산 예시:

```text
raw_tag_score
= Σ(interaction_type_weight × entity_tag_score)

normalized_tag_score
= group-aware normalization(raw_tag_score)
```

- 도서관·책·프로그램·후기 기여 수를 따로 보존한다.
- 한 종류의 신호만 많아도 그 신호에서 추론 가능한 태그만 생성한다.
- 데이터가 없는 태그를 임의로 추론하지 않는다.

### 11.6 최종 점수

모든 구성요소를 0~1 범위로 정규화한 뒤 각 보너스에 상한을 둔다.

```text
final_score
= base_score
+ capped_manual_tag_bonus
+ capped_manual_region_bonus
+ capped_behavior_bonus
```

행동 상태가 `ready`가 아니면 behavior bonus는 0이다. 수동 설정은 적용할 수 있다.

권장 상한:

- 수동 태그: 기본 점수의 최대 15%
- 수동 지역: 기본 점수의 최대 10%
- 행동 성향: 기본 점수의 최대 25%

실제 값은 algorithm version과 함께 관리한다.

### 11.7 추천 사유·동점

- 점수 기여도 상위 2~3개 규칙으로 사유 생성
- 수동·행동 개인화 사유를 구분 가능하게 내부 detail 보존
- 결측값은 0으로 단정하지 않고 규칙의 missing 정책 적용
- 큰 통계값은 log/percentile normalization
- 동점: 거리, 검증 데이터 충실도, 후기 수, 도서관명 순

### 11.8 Haversine

```python
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))
```

lat/lng 범위를 검증하고 원문 좌표를 저장하지 않는다.

---

## 12. 캐시·스냅샷 처리

### 12.1 도서 검색

- 정규화 검색조건 hash
- Redis TTL 권장 6시간
- API key 제외
- 실패 시 같은 조건의 stale 캐시를 선택적으로 반환

### 12.2 책 메타데이터

- 상세 정보 30~90일 후 재확인
- API 장애 시 기존 DB 데이터 반환 가능
- 응답에 `metadata_stale` 표시 가능

### 12.3 소장 관계

- ISBN·지역 조건 cache 7일 권장
- `last_verified_at` 갱신
- 원천에서 빠진 관계는 즉시 삭제보다 재확인 후 비활성화

### 12.4 대출 가능 여부

- 24시간 fresh
- 기준일·조회시각 표시
- 조회하지 않은 도서관과 unavailable을 구분

### 12.5 인기 도서

- 메인 노출 조건은 매일 미리 수집
- 최신 fresh snapshot 우선
- 집계 범위·기간·필터를 response에 포함

### 12.6 일자별 운영표

- 향후 180일 생성
- 운영시간·휴관·공휴일 변경 시 영향 범위 재생성
- 조회 중 행이 없으면 동기 계산 가능하되 외부 API 호출 금지

### 12.7 일일 추천

- 지역별 매일 생성
- 기본 후보 20개 내외
- 사용자별 결과는 캐시할 수 있으나 영속 테이블에 저장하지 않음
- profile setting 변경 시 사용자별 캐시만 무효화

### 12.8 이미지 해석

- 기본 규칙은 짧은 in-process 또는 Redis 캐시 가능
- `MediaAsset`·`DefaultMediaAssetRule` 변경 시 캐시 무효화
- 사용자 업로드 변경 시 해당 엔터티 응답 캐시 무효화

---

## 13. Celery 작업

| task | 주기·트리거 | 역할 |
|---|---|---|
| `libraries.import_standard_dataset` | 새 파일·수동 | 도서관·운영시간·휴관·통계 upsert |
| `libraries.import_facility_dataset` | 새 파일·수동 | 시설 상태 upsert |
| `libraries.sync_public_holidays` | 주 1회 | 현재·다음 연도 공휴일 갱신 |
| `libraries.rebuild_daily_schedules` | 매일·원천 변경 후 | 향후 운영표 생성 |
| `libraries.rebuild_library_tags` | 도서관 데이터 변경 후 | 직접 태그 재계산 |
| `libraries.rebuild_program_rollups` | 프로그램 변경 후 | 프로그램 태그 집계 |
| `libraries.rebuild_review_rollups` | 후기 변경 후 | 후기 태그 집계 |
| `books.refresh_popular_books` | 매일 | 인기 도서 snapshot |
| `books.refresh_book_metadata` | 필요 시 | stale 책 상세 갱신 |
| `programs.sync_programs` | 원천 주기 | 프로그램 upsert·soft delete |
| `media_assets.audit_external_links` | 월 1회 | 공식 이미지 링크·license 점검 |
| `recommendations.generate_daily_sets` | 매일 00:10 | 지역별 기본 추천 생성 |
| `preferences.rebuild_user_preference` | 행동 변경 후 debounce | 태그 기반 자동 성향 재계산 |
| `preferences.reconcile_states` | 매일 | 누락·실패·threshold 하락 보정 |
| `community.cleanup_deleted_images` | 삭제 후 | storage 객체 정리 |

모든 task는 idempotent하게 구현한다.

동일 대상 task 중복 실행 방지:

```text
preference:{user_id}
library-tags:{library_id}
daily-recommendation:{date}:{region_key}
```

Redis lock을 사용할 수 있다.

별도 `SourceSyncRun` DB 기록은 만들지 않는다. task ID, provider code, 입력 파일 checksum, 처리 건수, 실패 건수는 구조화 로그로 기록한다.

---

## 14. 전국도서관표준데이터 import

### 14.1 import 명령

```bash
python manage.py import_library_standard --file path/to/file.json --sido 부산광역시
```

옵션:

- `--dry-run`
- `--sido`
- `--reject-file`
- `--rebuild-schedules`
- `--rebuild-tags`

### 14.2 처리 단계

```text
파일 checksum 계산
→ JSON schema 확인
→ records 순회
→ 지역 필터
→ 문자열·숫자·좌표 정규화
→ Library 매칭/upsert
→ 운영시간 upsert
→ 휴관 규칙 parse/upsert
→ 통계 snapshot upsert
→ reject report 기록
→ 도서관 태그 재계산
→ 운영표 재생성
→ 처리 통계 로그
```

### 14.3 도서관 매칭 우선순위

1. 기존 외부 개별 도서관 코드가 있을 때 그 코드
2. 정규화 이름 + 정규화 도로명주소 exact
3. 정규화 이름 + 좌표 근접
4. 정규화 이름 + 시군구 + 전화번호
5. 그 외 신규 생성 또는 검수 대상

전국도서관표준데이터의 제공기관코드를 개별 도서관 ID로 사용하지 않는다.

### 14.4 필드 변환

- 빈 문자열 → nullable 필드는 null
- 숫자 문자열 → 안전한 정수·decimal 변환
- `0`은 실제 0인지 미제공인지 필드별 규칙 적용
- 좌표 범위 검증
- 전화번호 placeholder reject
- 행정구역 alias 정규화

### 14.5 운영시간·휴관

- `00:00~00:00`을 자동으로 24시간 운영으로 해석하지 않음
- 복합 휴관 문구는 raw text를 보존
- parser가 이해하지 못하면 `rule_type=unknown`
- unknown이 있어도 import 전체를 실패시키지 않음

### 14.6 시설 import

```bash
python manage.py import_library_facilities --file path/to/facilities.json
```

boolean 변환:

- 명시적 true → available
- 명시적 false가 부재를 보장하는 데이터셋 → unavailable
- 누락·해석 불가 → unknown

import 뒤 facility rule 기반 `LibraryTag`를 재계산한다.

---

## 15. 프로그램 import

```bash
python manage.py import_programs --file path/to/programs.json
```

처리:

1. `library_name`, `sigungu`로 개최 도서관 매칭
2. 분류·대상 코드 정규화
3. 날짜 파싱
4. 외부 key 생성
5. Program upsert
6. 이번 입력에 없는 기존 provider 행의 soft delete 정책 적용
7. ProgramTag 재계산
8. 개최 도서관 program rollup 재계산

같은 제목이라도 날짜가 다르면 하나로 병합하지 않는다.

원천 `application_status`는 `application_status_raw`에 보존하지만 서비스 내부 신청 상태 테이블로 확장하지 않는다.

---

## 16. 쿼리·성능 설계

### 16.1 도서관 목록

권장 queryset:

- `select_related`로 latest stat을 직접 가져오기 어렵다면 Subquery 또는 별도 current FK 고려
- 대표 이미지 `Prefetch`
- available 시설과 active LibraryTag만 `Prefetch`
- `Exists`로 사용자 저장 여부 annotate
- 리뷰 평균·수는 annotation 또는 집계 캐시

### 16.2 태그 필터

다중 태그 AND:

```text
filter(library_tags__tag_id__in=tag_ids)
→ annotate matched_count
→ matched_count = len(tag_ids)
```

rollup과 direct tag 중 중복으로 matched count가 부풀지 않도록 distinct tag 기준으로 계산한다.

### 16.3 프로그램·후기

- 프로그램: `(is_visible, operation_end_date)`, `(library, operation_start_date)`
- 후기: `(moderation_status, -created_at)`, `(library, -created_at)`
- 관련 책·프로그램·태그를 prefetch

### 16.4 나의 나들이

저장 목록은 각 대상의 카드 serializer를 재사용하되 queryset에서 필요한 관계를 선조회한다.

작성 후기와 저장 후기를 union하지 않고 별도 section으로 반환한다. 의미가 다르기 때문이다.

### 16.5 전문검색

MVP:

- 정규화 `icontains`
- PostgreSQL trigram

Phase 2:

- 한국어 형태소 검색 또는 별도 검색엔진

### 16.6 페이지 크기

- 기본 20
- 최대 100
- 인기 도서 endpoint 최대 50
- 추천 endpoint 최대 20
- 후기 이미지 최대 5

---

## 17. 권한·보안·개인정보

### 17.1 권한

- 공개 읽기: 도서관·책·프로그램·공개 후기·태그·추천
- 인증 필요: 프로필, 저장, 후기 작성, 나의 나들이, 선호 설정
- 작성자만: 후기 수정·삭제
- 관리자만: 태그 seed, 공식 이미지, 기본 이미지 규칙, 데이터 import 관리

### 17.2 이메일·닉네임

- 이메일 unique·소문자 정규화
- 이메일은 공개 프로필 응답에 노출하지 않음
- 닉네임 길이·금칙어·공백 정책 적용

### 17.3 현재 위치

- 요청 범위에서만 거리 계산
- DB 저장 금지
- 정밀 좌표를 application log에 기록하지 않음
- 좌표 제공 동의 실패 시 거리 없는 결과 반환

### 17.4 외부 URL

- 공식 이미지·홈페이지 링크는 scheme allowlist
- javascript/data URL 금지
- redirect 검증
- 서버 다운로드 시 SSRF 방어

### 17.5 이미지

- MIME sniffing
- 확장자만 신뢰하지 않음
- 픽셀 크기·용량 제한
- EXIF 위치정보 제거 권장
- storage 객체 키 랜덤화
- moderation 필요 시 업로드 후 비공개 상태 사용

### 17.6 후기

- XSS를 막기 위해 HTML 입력을 금지하거나 sanitize
- 신고·숨김 정책
- hidden 후기의 저장 목록 노출 제한
- 자기 후기 저장 금지 규칙
- 삭제된 후기의 preference 재계산

### 17.7 선호 정보

선호 지역·태그는 추천 설정 정보다. 공개 프로필에 기본 노출하지 않는다.

---

## 18. Django Admin 요구사항

### Accounts

- 사용자 email·nickname 검색
- profile image 미리보기
- 선호 지역·태그 inline
- 비밀번호 원문 노출 금지

### Tags

- group·선택 가능 여부 필터
- code 변경 경고
- 비활성화 시 연결 영향 확인

### Libraries

- 운영시간·휴관·통계·시설·태그·이미지 inline
- unknown 시설 필터
- 운영표 재생성 action
- 태그 재계산 action

### Media assets

- 원본/저장 이미지 미리보기
- license·attribution 필수 검증
- 기본 이미지 규칙 충돌 검사

### Books

- ISBN·제목 검색
- KDC·BookTag 확인
- holding·availability snapshot 조회

### Programs

- 분류·기간·도서관·노출 필터
- source URL 링크
- ProgramTag·ProgramImage inline
- 동일 제목을 자동 병합하는 action 금지

### Community

- moderation status·도서관·작성자 필터
- 관련 책·프로그램·태그 확인
- 이미지 미리보기

### Preferences

- 상태·signal count 필터
- 태그별 score·source count 확인
- 사용자 preference rebuild action

### Recommendations

- 목적별 규칙 편집
- 일일 테마·metric rule 편집
- 날짜·지역별 생성 결과 확인

---

## 19. 테스트 명세

### 19.1 User·프로필

- 이메일 중복 가입 거절
- username 없이 이메일 로그인
- 가입 시 UserProfile 생성
- User에 기본 지역 필드 없음
- 프로필 이미지 fallback
- profile-selectable이 아닌 태그 설정 거절
- 선호 지역·태그 PUT이 전체 교체로 동작

### 19.2 태그 모델·추출

- Tag code unique
- 각 domain tag unique constraint
- KDC→BookTag
- program_type/target→ProgramTag
- facility→LibraryTag
- 동적 상태 태그 생성 금지
- rebuild idempotency

### 19.3 이미지

- actual image가 fallback보다 우선
- 유형별 fallback
- 도메인 default fallback
- 없는 rule이면 null
- fallback이 연결 모델로 저장되지 않음
- 라이선스·attribution 응답

### 19.4 도서관 운영

- 단순 주간 휴관
- 첫째·셋째 요일 휴관
- 공휴일 휴관
- 특정일 예외 우선
- `00:00~00:00` unknown 처리
- 임시 휴관
- 180일 운영표 재생성

### 19.5 프로그램

- 같은 제목·다른 날짜는 별도 Program
- 같은 provider+external key는 upsert
- ProgramSession 모델 없음
- 분류·대상 태그 생성
- 분류별 fallback 이미지

### 19.6 커뮤니티

- 후기 도서관 필수
- 평점 1~5
- 관련 책·프로그램 중복 방지
- review-selectable 태그만 허용
- 이미지 최대 수
- 최신순 기본 정렬
- 자신의 후기 저장 거절
- hidden 후기 비노출

### 19.7 나의 나들이

- 네 종류 저장 unique
- PUT idempotency
- 저장·해제 후 preference task 예약
- 작성 후기와 저장 후기 구분
- 삭제 대상 처리

### 19.8 자동 성향

- threshold 미만 collecting
- threshold 충족 pending
- 계산 성공 ready
- 신호 감소 시 collecting 복귀
- `UserPreferenceItem`이 tag FK 중심
- library/book/program/review source count
- 수동 선호가 signal_count에 포함되지 않음
- 수동 선호는 threshold 미만에도 추천에 반영

### 19.9 추천

- 같은 날짜·지역의 기본 세트 재현성
- 실시간 좌석 데이터를 참조하지 않음
- 수동 태그·지역 보너스 상한
- behavior bonus는 ready에서만 적용
- 같은 후보 집합 내 재정렬
- 추천 사유는 실제 일치 항목만 포함

### 19.10 외부 API contract

- 정상·빈 응답
- XML/JSON 오류
- timeout·429·5xx
- 필드 누락
- ISBN 문자열 유지
- API key 로그 마스킹

### 19.11 데이터 품질

- 부산 필터
- 좌표 범위
- `00:00` 특수값
- 제공기관코드를 도서관 코드로 오사용하지 않음
- 시설 false/unknown 구분
- 프로그램 외부 key 안정성

---

## 20. 로깅·모니터링

구조화 로그 필드:

```text
request_id
user_id (필요한 경우 내부 ID)
provider_code
task_id
operation
entity_type
entity_id
input_checksum
fetched_count
inserted_count
updated_count
skipped_count
failed_count
duration_ms
error_code
```

금지:

- API key
- 비밀번호
- access/refresh token
- 정밀 현재 좌표
- 사용자 이미지 원본 binary
- 후기 본문 전체를 오류 로그에 그대로 남기기

모니터링 지표:

- 외부 API 성공률·latency·429
- import reject count
- 운영표 unknown 비율
- 도서관 이미지 fallback 비율
- 프로그램 이미지 fallback 비율
- preference task 성공률
- collecting/pending/ready/failed 사용자 수
- 추천 fallback 사용률

---

## 21. 배포 구성

권장 구성:

```text
Vue/static frontend
        ↓
Nginx / Load Balancer
        ↓
Django ASGI/WSGI
        ↓
PostgreSQL
Redis
Celery worker
Celery beat
Object storage
```

배포 전 확인:

- `.env`·API key 제외
- migration 실행
- tag fixture와 default media rule seed
- 부산 도서관 fixture/import
- 공휴일·운영표 생성
- 프로그램·인기 도서 초기 적재
- 정적·미디어 파일 설정
- CORS/CSRF/allowed hosts
- health check
- storage lifecycle와 백업

---

## 22. 구현 단계

### Phase 0: 기반

- 프로젝트·settings 분리
- custom User(email login)
- Tag seed
- MediaAsset·기본 이미지 규칙
- 공통 예외·API schema

### Phase 1: 도서관

- 표준데이터 import
- 운영시간·휴관·통계·시설
- 운영표 생성
- LibraryTag 생성
- 검색·상세·이미지 fallback

### Phase 2: 기본 추천

- Purpose·규칙 seed
- 일일 추천 세트
- 목적별 추천
- 추천 사유

### Phase 3: 책

- 정보나루 client
- 검색·상세
- BookTag
- 소장·대출 가능
- 인기 도서

### Phase 4: 프로그램

- JSON import
- ProgramTag
- ProgramImage·분류 fallback
- 목록·상세·저장

### Phase 5: 커뮤니티·나의 나들이

- 후기 CRUD
- 관련 책·프로그램
- ReviewTag·이미지
- 네 종류 저장
- 작성 후기·저장 후기 구분

### Phase 6: 프로필 설정·개인화

- 프로필 화면·설정 화면 API
- 선호 지역·태그 체크리스트
- UserPreference 상태
- tag 중심 UserPreferenceItem
- 수동+행동 보너스

### Phase 7: 운영 보강

- Celery beat
- admin actions
- 이미지 license audit
- 로깅·모니터링
- 배포·fixture·README

실시간 열람실 단계는 존재하지 않는다.

---

## 23. MVP 완료 조건

### 계정·프로필

- 이메일·닉네임·비밀번호 가입
- 프로필 이미지·자기소개 수정
- 프로필 표시와 설정 API가 분리됨
- 선호 지역·태그 체크리스트 저장

### 홈

- 같은 날짜에 재현 가능한 TOP 1~3
- 6개 목적 추천
- 수동 선호 즉시 반영
- 행동 성향은 ready 상태에서만 반영

### 도서관 찾기·상세

- 지역·유형·운영·시설·태그 필터
- 정적 좌석·장서 통계
- 운영표·거리 계산
- 실제 또는 유형별 기본 이미지
- 실시간 잔여좌석 기능 없음

### 책

- 검색·상세
- KDC 기반 BookTag
- 소장 도서관
- 대출 가능 기준일 표시
- 인기 도서

### 프로그램

- 분류·대상·도서관 검색
- ProgramSession 없이 날짜별 별도 행
- 분류 태그·기본 이미지
- 관심 저장

### 커뮤니티

- 도서관 기반 후기
- 최신순 목록
- 관련 책·프로그램
- 선택 후기 태그
- 이미지 또는 후기 기본 이미지

### 나의 나들이

- 저장 도서관·책·프로그램·후기
- 작성 후기 별도 목록
- 자동 성향 상태·상위 태그
- 설정 변경은 프로필 설정으로 연결

### 데이터 운영

- source 관리 테이블 없이 idempotent import
- reject report와 구조화 로그
- 운영표·태그·추천 재생성 task
- 공식 이미지 license 정보

---

## 24. 구현 시 최종 확인 항목

1. 실제 시설 JSON의 false가 명시적 부재인지 미확인인지 데이터 생성 규칙을 확인한다.
2. 프로그램 제공 파일에 안정적인 원천 ID가 있는지 확인하고 없으면 hash 구성 필드를 확정한다.
3. 후기에서 선택 가능한 태그 목록을 UX와 함께 확정한다.
4. 프로필 체크리스트에 노출할 태그 수와 그룹을 제한한다.
5. 행동 신호별 기본 가중치와 중복 태그 상한을 algorithm version으로 고정한다.
6. 후기 작성 신호와 후기 저장 신호의 상대 가중치를 확정한다.
7. 도서관 program/review rollup의 최소 표본수를 확정한다.
8. 공식 이미지의 공공누리 유형별 변형·썸네일 정책을 확인한다.
9. 대출 가능 API의 실제 기준일 의미를 화면 문구와 함께 검증한다.
10. MVP 배포 환경에서 Celery·Redis를 사용할지, management command 수동 실행으로 대체할지 팀이 결정한다.

---

## 25. 참고 문서

- 프로젝트 명세서: 첨부 `(26_0622) 관통템플릿_Python_자율_15기_13회차.pdf`
- 서비스 페이지 설명: 첨부 `메인페이지에 대한 간단한 서술.pdf`
- 데이터셋 명세: 첨부 `데이터셋 정보.pdf`
- Django 5.2 문서: https://docs.djangoproject.com/en/5.2/
- Django REST Framework: https://www.django-rest-framework.org/
- Celery: https://docs.celeryq.dev/en/stable/
- 도서관 정보나루: https://www.data4library.kr/apiUtilization
- 전국도서관표준데이터: https://www.data.go.kr/data/15013109/standard.do
- 한국천문연구원 특일 정보: https://www.data.go.kr/data/15012690/openapi.do
- 공공누리: https://www.kogl.or.kr/info/freeUse.do
