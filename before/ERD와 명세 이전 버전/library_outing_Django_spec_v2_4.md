# 도서관 나들이 Django 개발 명세서

- 문서 버전: 2.4
- 작성 기준일: 2026-06-23
- 기준 ERD: `library_outing_ERD_v2_4.md`
- 대상: Django REST API 백엔드, 데이터 import·동기화 작업, 추천·개인화 서비스
- 1차 서비스 범위: 부산 지역 MVP, 전국 확장 가능한 코드 구조

---

## 1. 목적과 전제

이 문서는 다음 기능을 Django로 구현하기 위한 개발 기준이다.

1. 모든 사용자에게 동일하게 제공되는 **오늘의 추천 도서관** 최대 3개
2. 개인화 입력이 있는 회원에게만 제공되는 **여기는 어때요?** 최대 3개
3. 사용자가 직접 선택하는 6개 **테마별 추천**
4. 도서관 검색·상세·일자별 운영 여부 조회
5. 도서 검색·상세, 소장 도서관, 다독자 기반 다음 책 추천 조회
6. 전국·부산·세부 지역 인기 대출 도서 목록
7. 문화 프로그램과 개최 도서관 통합 조회
8. 도서관 기반 후기 커뮤니티와 관련 책·프로그램 연결
9. 도서관·책·프로그램·후기 저장과 작성 후기 조회
10. 프로필·프로필 설정, 선호 지역·선호 태그 체크리스트
11. 공통 태그를 기준으로 한 행동 기반 사용자 성향 집계
12. 도서관 유형·프로그램 분류·후기 상태별 대체 이미지
13. 연초 12개월 공휴일 완전 수집, 도서관·프로그램·인기 도서 갱신과 운영표·추천 파생 데이터 생성
14. 실제 부산 표준 JSON·외관 이미지 CSV·작업 중 시설 파일과 정보나루 응답의 schema·매칭·품질 검수

서비스 내부 프로그램 신청·예약·결제·참여 이력, 실시간 열람실 잔여좌석, 후기 자동 텍스트 태깅, AI가 직접 정하는 추천 순위는 범위에 포함하지 않는다.

### 1.1 고정 정책

- 가입 시 이메일·닉네임·비밀번호만 입력받는다.
- `User`에 기본 지역이나 현재 좌표를 저장하지 않는다.
- 프로필 표시정보와 프로필 설정을 화면·API 책임상 구분한다.
- 사용자가 직접 고른 선호 지역·태그는 프로필 설정에서 관리한다.
- 수동 선호는 행동 신호 수가 적어도 개인화에 사용할 수 있다.
- 행동 신호가 1건 이상이면 임시 `UserPreferenceItem`을 계산할 수 있다. 최소 신호 수 미만에서는 신뢰도에 비례해 약하게 적용하고, `ready` 상태에서 전체 행동 가중치를 사용한다.
- 태그는 도서관 전용 필드가 아니라 도서관·책·프로그램·후기의 공통 선호 집계 기준이다.
- 후기 태그는 “어떤 점이 좋았나요?”에 대한 긍정 경험 선택지다. 후기 생성 시 활성 선택지 중 1~5개를 반드시 고른다.
- 공통 `Tag.label`과 후기 문장형 `Tag.review_label`을 분리하고, 후기 화면은 7개 `review_group`으로 묶어 표시한다.
- 후기 태그의 미선택을 부정 신호로 해석하지 않고, 후기 rollup으로 공식 시설 유무나 현재 상태를 확정하지 않는다.
- `nearby`, `open_now`, 현재 인기 순위는 영구 태그로 저장하지 않는다.
- 실시간 열람실 API와 관련 모델·캐시·endpoint를 구현하지 않는다.
- 전국도서관표준데이터의 `열람좌석수`는 정적 통계로 사용한다.
- 프로그램은 한 원천 게시물 또는 한 운영기간을 한 행으로 저장하며 `ProgramSession`을 만들지 않는다.
- 같은 이름의 프로그램이라도 날짜나 원천 게시물이 다르면 별도 프로그램이다.
- 사용자가 저장한 후기는 `UserReviewSave`, 사용자가 작성한 후기는 `UserReview.user`로 구분한다.
- 공식·시스템 이미지와 사용자 업로드 이미지를 구분한다.
- 대체 이미지는 엔터티별 실제 이미지 관계로 저장하지 않고 응답 시 규칙으로 해석한다.
- 브라우저 좌표는 현재 요청에서만 거리 계산에 사용하고 DB·분석 로그에 원문을 저장하지 않는다.
- 홈 섹션 순서는 **오늘의 추천 도서관 → 여기는 어때요? → 테마별 추천**으로 고정한다.
- 오늘의 추천 도서관 최대 3개와 테마별 추천은 공통 결과이며 개인화로 재정렬하지 않는다.
- 여기는 어때요?는 활성 수동 선호 또는 1건 이상의 유효 행동 신호가 있는 로그인 회원에게만 노출하고, 오늘의 추천과 중복되지 않는 최대 3개를 반환한다.
- 일반 시설 편의는 오늘의 공통 추천 기준에서 제외하고 검색 필터·상세 정보·개인화 가중치에 사용한다.
- 시설 데이터는 `LibraryFacilityProfile` 선택적 OneToOne과 nullable boolean 필드로 저장한다. 현재 작업 중 파일은 유효한 JSON 배열/JSONL로 정규화하고 기본 `draft`로 적재하며, `verified` 프로필의 `True`만 공식 긍정 시설 필터에 사용한다.
- 실제 외관 이미지 파일은 CSV다. 220개 행이 있어도 URL이 있는 도서관만 실제 이미지를 보유하며, 이용허락 미검증 asset은 비활성으로 두고 유형별 대체 이미지를 사용한다.
- 공휴일은 초기 배포 시 현재 연도를 적재하고, 이후 매년 초 `getRestDeInfo`를 1월부터 12월까지 반복 호출해 한 번에 완전 적재한다. 공휴일이 없는 달의 정상 빈 응답도 성공 월로 계산하며, 12개월 전체 성공 전에는 해당 연도를 완전한 공휴일 달력으로 보지 않는다.
- 운영시간과 휴관 문구가 충돌하면 해당 날짜는 `unknown`이다. 개관일은 확정되지만 정확한 시간이 없는 경우 `status=open`, 시간 null을 허용한다.
- `오늘의 추천 도서관`과 `여기는 어때요?`는 추천 날짜의 `LibraryDailySchedule.status=open`인 도서관만 사용한다. `closed`, `unknown`, 운영표 누락은 점수 fallback 대상이 아니다.
- 정보나루 MVP API는 `libSrch`, `srchBooks`, `srchDtlList`, `loanItemSrch`, `recommandList(type=reader)`, `libSrchByBook`이다. `libSrch`는 부산 도서관 코드 선연결용이며 표준데이터를 덮어쓰지 않는다. 복본·청구기호, 전날 기준 대출 가능 여부, 특정 도서관 인기 목록은 MVP에서 구현하지 않는다.
- `recommandList(type=reader)` 결과는 별도 추천 관계 테이블 없이 반환 책만 upsert하고 ISBN 입력 조합별 단기 캐시로 제공한다.
- GMS API 출력은 사실 데이터·운영 판정·시설 필드·추천 점수에 사용하지 않는다. 사용 시 Django 서버를 경유하는 표현 보조 기능으로만 둔다.

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
| `libraries` | 도서관·별칭·외부 코드·운영시간·휴관·공휴일 달력·운영표·통계·시설 프로필·도서관 태그·이미지 연결 |
| `books` | 책·책 태그·소장 도서관·전국/지역 인기 도서·다독자 기반 다음 책 추천 cache |
| `programs` | 문화 프로그램·프로그램 태그·이미지 연결 |
| `community` | 후기·후기 이미지·후기 태그·관련 책·프로그램 |
| `myoutings` | 저장한 도서관·책·프로그램·후기와 나의 나들이 조회 service |
| `preferences` | 행동 기반 자동 성향 상태·태그 점수 |
| `recommendations` | 오늘의 추천 도서관, 여기는 어때요?, 테마별 추천 규칙·결과 |
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

사용자가 구성한 키 이름을 프로젝트 표준으로 고정한다.

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,api.example.com
DATABASE_URL=postgresql://user:password@db:5432/library_outing
REDIS_URL=redis://redis:6379/0

GMS_API_KEY=
GMS_OPENAI_BASE_URL=https://gms.ssafy.io/gmsapi/api.openai.com/v1

DATA4LIBRARY_API_KEY=
DATA4LIBRARY_BASE_URL=http://data4library.kr/api

DATA_GO_KR_API_KEY=
PUBLIC_HOLIDAY_API_BASE_URL=http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService
PUBLIC_HOLIDAY_API_OPERATION=getRestDeInfo
PUBLIC_HOLIDAY_NUM_OF_ROWS=20
PUBLIC_HOLIDAY_ANNUAL_SYNC_MONTH=1
PUBLIC_HOLIDAY_ANNUAL_SYNC_DAY=2

LIBRARY_SCHEDULE_LOOKAHEAD_DAYS=180
LIBRARY_HOME_RECOMMENDATION_REQUIRE_OPEN=true
LIBRARY_ALIAS_OVERRIDES_FILE=
LIBRARY_STANDARD_DATA_FILE=
LIBRARY_IMAGE_DATA_FILE=
LIBRARY_FACILITY_DATA_FILE=
LIBRARY_FACILITY_DEFAULT_STATUS=draft
PROGRAM_DATA_FILE=

SERVICE_DEFAULT_SIDO=부산광역시
SERVICE_DEFAULT_SIGUNGU=
SERVICE_DEFAULT_REGION_CODE=21

PROGRAM_REFRESH_HOURS=24
PERSONALIZATION_HOME_MIN_SIGNALS=1
PERSONALIZATION_MIN_SIGNALS=20
PERSONALIZATION_COLLECTING_MAX_CONFIDENCE=0.95
PERSONALIZATION_BEHAVIOR_MAX_BONUS_RATIO=0.25
PERSONALIZATION_MANUAL_TAG_MAX_BONUS_RATIO=0.15
PERSONALIZATION_MANUAL_REGION_MAX_BONUS_RATIO=0.10
PREFERENCE_REBUILD_DEBOUNCE_SECONDS=45
TODAY_RECOMMENDATION_LIMIT=3
PERSONALIZED_HOME_RECOMMENDATION_LIMIT=3
DAILY_RECOMMENDATION_CANDIDATE_LIMIT=20
DAILY_RECOMMENDATION_MIN_RESULT_COUNT=3
THEME_RECOMMENDATION_DEFAULT_LIMIT=6
POPULAR_BOOK_REFRESH_DAYS=7
READER_RECOMMENDATION_CACHE_SECONDS=86400

MEDIA_STORAGE_BACKEND=local
MEDIA_MAX_UPLOAD_MB=10
REVIEW_IMAGE_MAX_COUNT=5
REVIEW_TAG_MIN_SELECT=1
REVIEW_TAG_MAX_SELECT=5
AWS_STORAGE_BUCKET_NAME=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_ENDPOINT_URL=
```

키 사용 규칙:

- `.env`는 Git에 포함하지 않고 `.env.example`에는 변수명만 둔다.
- `DATA_GO_KR_API_KEY`, `DATA4LIBRARY_API_KEY`, `GMS_API_KEY`는 Vue에 전달하지 않는다.
- 공공데이터포털 키를 `httpx`의 `params`로 전달할 때 이미 percent-encoded된 키를 다시 인코딩하지 않도록 실제 호출 contract test를 둔다.
- API 인증키를 cache key, 오류 응답, 구조화 로그에 넣지 않는다.
- 로그에서 `authKey`, `serviceKey`, `ServiceKey`, `Authorization`을 마스킹한다.
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

`label`은 공통 분석·필터용 표준 명칭이고, `review_label`은 후기 체크리스트에서만 쓰는 문장형 문구다. 동일 태그를 도서관 필드·프로그램 분류·후기 선택이 공유할 수 있도록 원천 도메인 타입은 두지 않는다.

```python
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
    code = models.SlugField(max_length=80, unique=True)
    label = models.CharField(max_length=80)
    tag_group = models.CharField(max_length=40, choices=TagGroup.choices)
    description = models.TextField(blank=True)

    is_profile_selectable = models.BooleanField(default=False)
    is_review_selectable = models.BooleanField(default=False)
    review_label = models.CharField(max_length=100, blank=True)
    review_group = models.CharField(
        max_length=40,
        choices=ReviewGroup.choices,
        blank=True,
    )

    is_filterable = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    review_display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
```

인덱스:

```python
models.Index(fields=["tag_group", "is_active", "display_order"])
models.Index(
    fields=["review_group", "is_review_selectable", "review_display_order"]
)
models.CheckConstraint(
    condition=(
        models.Q(is_review_selectable=False)
        | (
            ~models.Q(review_label="")
            & ~models.Q(review_group="")
            & models.Q(review_display_order__gt=0)
        )
    ),
    name="tag_review_metadata_required",
)
```

검증:

- `code`는 의미가 바뀌어도 재사용하지 않는다.
- `is_review_selectable=True`이면 `review_label`과 `review_group`이 비어 있지 않아야 한다. 모델 `clean()`, admin form, serializer에서 모두 검증한다.
- 프로필 설정 API는 `is_profile_selectable=True`만 허용한다.
- 후기 작성 API는 `is_review_selectable=True`, `is_active=True`만 허용한다.
- `nearby`, `open_now`, `current_popular`, `low_occupancy`, `not_too_crowded` 같은 동적·시점 의존 상태 태그 seed를 금지한다.
- `notice_clear`, `staff_friendly`, `good_natural_light`는 확정 seed에 포함하지 않는다. 각각 핵심성 부족, 사람 평가, 공간 의미의 모호성 때문에 제외하며 `kind_guidance`, `good_nearby_scenery`를 사용한다.
- `review_label`은 UI 문구이므로 문구를 다듬더라도 `code`의 의미가 같으면 새 태그를 만들지 않는다.

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
- `standard_provider_agency_code`, `standard_provider_agency_name`: 최신 핵심 표준 행의 제공기관 메타데이터
- `standard_reference_date`: 최신 핵심 표준 행의 기준일
- `standard_row_hash`: 원천 행 변경 탐지
- `is_active`: `BooleanField(default=True, db_index=True)`

인덱스:

```python
models.Index(fields=["sido", "sigungu", "library_type", "is_active"])
models.Index(fields=["normalized_name"])
models.Index(fields=["standard_reference_date"])
```

`pg_trgm`을 사용하는 경우 `normalized_name`, `normalized_address`에 trigram GIN index를 추가한다.

#### LibraryAlias

- FK: `library`
- `alias_name`, `normalized_alias_name`, `sigungu`
- `alias_type`: `source_name|short_name|legacy_name|correction|duplicate_merge`
- `provider_code`, `is_active`
- unique `(library, normalized_alias_name, sigungu, provider_code)`
- index `(normalized_alias_name, sigungu, is_active)`

주소·좌표만 같은 행을 자동 병합하지 않는다. alias/merge override는 검수된 fixture 또는 관리 명령 입력으로만 만든다.

#### LibraryExternalIdentifier

```python
models.UniqueConstraint(
    fields=["provider_code", "code_type", "external_code"],
    name="uq_library_external_identifier",
)
```

`provider_code`는 문자열 코드로 저장한다. 별도 DataSource FK를 사용하지 않는다. `external_name`, `external_address`, `match_method`, `match_confidence`를 함께 보존하고 낮은 신뢰도 자동 매칭은 활성 연결로 승격하지 않는다.

#### LibraryOpeningHour

- `day_type`: `day_of_week|public_holiday|specific_date`
- `schedule_status`: `open|closed|unknown`
- `sequence`: 다중 운영 구간 지원
- `closes_next_day`: 익일 종료
- `provider_code`, `source_field`, `quality_flags`, `source_url`, `source_reference_date`, `fetched_at`

검증:

- `day_type=day_of_week`이면 `day_of_week` 필수, `specific_date`는 null
- `day_type=specific_date`이면 `specific_date` 필수
- `schedule_status=open`이어도 개관 여부만 확정되고 시간이 미제공이면 두 시간 모두 null 허용
- open/close time 중 한쪽만 존재하는 상태는 금지

#### LibraryClosureRule

`normalized_rule`은 JSON으로 보존하지만, rule parser는 version을 가진 순수 함수로 작성한다.

우선순위:

1. 특정 날짜 일정
2. 임시·장기 휴관
3. 명절·공휴일 휴관
4. 주차별·요일별 정기 휴관
5. 일반 운영시간

#### PublicHolidayCalendar

공휴일 API의 연도별 완전 적재 여부를 표현한다.

- `year`: unique
- `provider_code`: 기본 `kasi_rest_de_info`
- `is_complete`: 1~12월 전체 응답 검증·transaction 반영 완료 여부
- `synced_month_count`: 0~12
- `last_attempted_at`, `last_completed_at`
- `is_complete=True`이면 `synced_month_count=12`인 `CheckConstraint` 권장

연도 재수집은 12개월 응답을 먼저 모두 확보한 뒤 transaction 안에서 항목을 반영한다. 재수집 중 일부 월이 실패하면 기존 complete 달력을 삭제하거나 불완전 상태로 덮어쓰지 않는다.

#### PublicHoliday

- FK: `calendar`
- `date`: `locdate`를 `DateField`로 변환
- `source_seq`: 원천 `seq`
- `date_kind`: 원천 `dateKind`
- `name`: 원천 `dateName`
- `holiday_code`: 내부 정규화 코드, nullable
- `is_public_holiday`: 원천 `isHoliday`; `Y` 항목만 저장하므로 원칙적으로 `True`
- unique `(calendar, date, source_seq)`
- `(date, is_public_holiday)` 복합 인덱스

원천에 별도 필드가 없는 `is_substitute`, `is_temporary`를 필수 모델 필드로 만들지 않는다.

#### LibraryDailySchedule

- `(library, date)` unique
- `status=open|closed|unknown`
- `open`이면서 정확한 시간이 없는 경우 `open_time/close_time=None` 허용
- `has_source_conflict`: 운영시간·휴관 문구 충돌 여부
- 충돌 시 `status=unknown`, `reason_code=source_conflict`
- `is_open_now`는 `status=open`이고 시작·종료 시각이 모두 알려진 경우에만 bool, 그렇지 않으면 null
- 운영 규칙·공휴일이 바뀌면 해당 날짜 범위를 재생성
- 과거 행은 최근 30일 정도만 유지해도 된다.

#### LibraryStatisticSnapshot

- `reading_seat_count`는 정적 총 좌석 수
- `book_count`, `serial_count`, `non_book_count`, 대출 정책, 면적은 nullable
- `source_payload`: 원문 통계 값
- `quality_flags`: 필드별 0·결측·범위 이상 경고
- unique `(library, provider_code, reference_date)`
- 도서관별 `is_current=True` 조건부 unique 권장
- 면적 0은 null+flag, 연속간행물·비도서 0은 실제 0으로 보존
- 장서·좌석·대출정책 0은 원문을 보존하되 추천 지표에는 검증된 양수만 사용

#### LibraryFacilityProfile

정규화된 시설 작업 파일의 고정 nullable boolean 필드와 일치하는 선택적 OneToOne 모델이다.

```python
class LibraryFacilityProfile(TimeStampedModel):
    library = models.OneToOneField(
        "libraries.Library",
        on_delete=models.CASCADE,
        related_name="facility_profile",
    )
    has_reading_room = models.BooleanField(null=True)
    has_children_room = models.BooleanField(null=True)
    has_digital_room = models.BooleanField(null=True)
    has_parking = models.BooleanField(null=True)
    has_cafe = models.BooleanField(null=True)
    has_wifi = models.BooleanField(null=True)
    has_nursing_room = models.BooleanField(null=True)
    has_accessible_facility = models.BooleanField(null=True)
    has_elevator = models.BooleanField(null=True)
    has_lounge = models.BooleanField(null=True)
    has_outdoor_space = models.BooleanField(null=True)
    provider_code = models.CharField(max_length=40, default="facility_json")
    data_status = models.CharField(
        max_length=16,
        choices=[("draft", "Draft"), ("verified", "Verified")],
        default="draft",
        db_index=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    quality_flags = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)
```

정합성 규칙:

- 원천 행의 명시적 `true` → `True`
- 원천 행의 명시적 `false` → `False`
- 원천 행의 필드 누락·파싱 실패 → 해당 필드 `None`
- 도서관과 매칭되는 시설 행 자체가 없음 → profile을 만들지 않음
- 공식 긍정 시설 필터는 `data_status=verified`이고 해당 필드가 `True`인 경우만 통과시킴
- `False`, `None`, profile 부재, `draft`를 모두 같은 부재 사실로 표시하지 않음

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

#### PopularBookSnapshot, PopularBookItem

- `scope_type`: `national|region`만 사용
- 지역 범위는 `region_code`, `detail_region_code`로 표현
- 특정 도서관 범위 snapshot은 현재 필수 API에 없으므로 만들지 않음
- snapshot query condition을 정규화한 `query_hash` 사용
- item unique `(snapshot, rank)`, `(snapshot, book)`
- 동일 조건의 최신 fresh snapshot을 우선 반환

#### 다독자 기반 다음 책 추천의 비영속 정책

`recommandList(type=reader)` 결과 관계를 모델로 저장하지 않는다.

- 입력: ISBN 1~5개
- 반환 책: `Book` upsert
- 결과 목록: 정규화된 ISBN 입력 조합을 key로 Redis 등에서 24시간 권장 cache
- API 원천 순서를 유지
- cache miss이면 정보나루 재호출

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
- `is_visible`, `deleted_at`: soft delete

외부 ID가 없을 때 해시 입력:

```text
normalized_library_id
+ normalized_title
+ operation_start_date
+ operation_end_date
+ normalized_source_url
```

`ProgramSession` 모델은 만들지 않는다. 같은 제목이 반복되어도 운영기간·게시물이 다르면 별도 `Program`이다. 현재 프로그램 JSON에는 설명·장소·정원·비용·이미지 필드가 없으므로 모델·import에서 값을 추정하지 않는다. 신청 상태는 `application_status_raw`만 보존하고, 일정 상태는 날짜로 계산한다.

#### ProgramTag

- `source_method`: `category_rule|target_rule|metadata_rule|manual`
- unique `(program, tag, source_method)`

#### ProgramImage

- FK: `program`, `media_asset`
- 프로그램별 활성 대표 이미지 하나
- 현재 JSON에는 프로그램 이미지가 없으므로 기본적으로 `category_code` 기반 fallback을 해석하고, 공식·관리자 이미지가 별도로 있을 때만 관계를 생성

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

- 필드: `review`, `tag`, `created_at`
- unique `(review, tag)`
- `ReviewTag`는 사용자가 실제 선택한 관계만 저장한다. 관리자·모델이 주관적 태그를 임의로 추가하지 않는다.
- serializer는 연결하려는 모든 태그가 `is_active=True`, `is_review_selectable=True`인지 검증한다.
- 후기 생성은 태그 1~5개를 필수로 요구한다. 중복 ID는 validation error다.
- PATCH에서 `tag_ids`가 제공되면 원자적으로 전체 교체하고, 생략되면 기존 연결을 유지한다. 빈 배열은 허용하지 않는다.
- 후기 본문 자동 태깅 결과는 MVP에서 저장하지 않는다.

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
signal_count = 0                   → collecting, 자동 성향 항목 없음
1 <= signal_count < threshold      → collecting, 임시 성향 항목 계산 가능
signal_count >= threshold, 예약됨  → pending
정식 계산 성공                     → ready
계산 실패                          → failed
```

`collecting` 상태의 `UserPreferenceItem`은 홈의 `여기는 어때요?`에서만 임시 신호로 사용할 수 있다. 행동 신뢰도는 `min(signal_count / PERSONALIZATION_MIN_SIGNALS, 1)`로 계산하고, `PERSONALIZATION_COLLECTING_MAX_CONFIDENCE`를 넘지 않도록 제한한다. 신호가 0으로 내려가면 자동 성향 항목을 제거한다. 프로필에서 직접 고른 선호는 그대로 유지한다.

---

### 6.11 recommendations

#### Purpose, PurposeTagRule, PurposeMetricRule

- `Purpose.code` unique
- `PurposeTagRule` unique `(purpose, tag)`
- `PurposeMetricRule` unique `(purpose, metric_code)`
- 규칙의 normalization JSON schema를 코드에서 검증

#### DailyRecommendationTheme, DailyRecommendationMetricRule, DailyRecommendationTagRule

`DailyRecommendationTheme`:

- `code`: unique 안정 코드
- `label`: 운영·관리용 기준명
- `subtitle`: 홈의 “오늘의 추천 도서관” 옆에 보이는 공개 문구
- `description`, `display_order`, `is_active`
- 초기 seed: `large_space`, `rich_collection`, `mood_space`, `study_seats`, `family_outing`, `restful_space`

`DailyRecommendationMetricRule`:

- FK `theme`
- `metric_code`, `weight`, `is_required`
- `normalization_rule` JSON
- unique `(theme, metric_code)`

`DailyRecommendationTagRule`:

- FK `theme`, `tag`
- `source_scope`: `any|direct|review_rollup|program_rollup|book_rollup`
- `weight`, `is_required`, `normalization_rule` JSON
- unique `(theme, tag, source_scope)`
- `review_rollup`은 후기 최소 근거 조건을 통과한 `LibraryTag`만 사용

규칙의 normalization JSON schema와 `source_scope` 조합은 model/service validation으로 검증한다.

#### DailyLibraryRecommendationSet, DailyLibraryRecommendationItem

- set unique `(recommendation_date, region_key, algorithm_version)`; 실제 선택된 theme은 set FK로 보존
- item unique `(set, rank)`, `(set, library)`
- set은 공개 3개보다 넓은 후보군을 저장할 수 있음
- 오늘의 추천 공개 결과는 상위 최대 3개이며 사용자별로 재정렬하지 않음
- item의 `score_detail`은 내부 검증용이며 MVP 카드에 추천 문장을 만들지 않음
- `여기는 어때요?` 결과는 별도 행으로 저장하지 않음

---

## 7. 태그 파이프라인 명세

### 7.1 기본 원칙

태그 파이프라인은 다음 세 층을 분리한다.

```text
원천 필드·관계
→ 도메인별 태그 연결
→ 사용자 행동 기반 UserPreferenceItem
```

- 도메인 엔터티의 원천값과 사용자 선호 점수를 같은 테이블에 저장하지 않는다.
- 같은 `Tag`를 직접 근거와 후기 선택이 공유할 수 있지만, 연결 모델의 `source_method`와 원천 테이블로 사실성 수준을 구분한다.
- 후기 태그는 긍정 경험 신호다. 미선택을 음수로 계산하지 않는다.

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

모든 rebuild 함수는 같은 입력에 여러 번 실행해도 결과가 같아야 한다. `replace_review_tags`는 `transaction.atomic()` 안에서 1~5개 검증 후 전체 교체한다.

### 7.3 직접 태그 예시

| 원천 | 규칙 | 태그 |
|---|---|---|
| 도서관 유형 | `public` | `public_library` |
| 정적 좌석 수 | percentile/구간 | `many_seats` |
| 장서 수 | percentile/구간 | `rich_collection` |
| 운영 종료시간 | 설정 기준 이상 | `late_open` |
| 시설 프로필 `has_children_room=True` | children room | `children_room`, `children_friendly` |
| 시설 프로필의 해당 `has_*=True` | parking/wifi/accessibility | `parking`, `wifi`, `accessible_facility` |
| 책 KDC | 문학·과학 등 | `book_literature`, `book_science` 등 |
| 프로그램 분류 | 강연/인문학 | `program_lecture_humanities` |
| 프로그램 분류 | 독서/글쓰기 | `program_reading_writing` |
| 프로그램 분류 | 문화/예술 | `program_culture_art` |
| 프로그램 분류 | 체험/교육 | `program_experience_education` |
| 프로그램 분류 | 전시 | `program_exhibition` |
| 프로그램 대상 | 가족 | `for_family` |

### 7.4 후기 선택 태그 seed

후기 작성 화면은 아래 7개 그룹을 순서대로 표시하고, 전체에서 1~5개를 선택하게 한다. `Tag.label`과 `Tag.review_label`은 역할이 다르므로 fixture에 함께 저장한다.

| 후기 그룹 | code | Tag.label | Tag.review_label | 다른 데이터와의 공유 |
|---|---|---|---|---|
| 공부·열람 | `quiet_study` | 조용한 공부 환경 | 조용히 공부하기 좋아요 | 후기 중심 |
| 공부·열람 | `focused_atmosphere` | 집중하기 좋은 분위기 | 집중하기 좋은 분위기예요 | 후기 중심 |
| 공부·열람 | `many_seats` | 충분한 좌석 | 앉을 자리가 충분해요 | 정적 좌석 수와 공유 가능 |
| 공부·열람 | `comfortable_reading_space` | 쾌적한 열람공간 | 열람공간이 쾌적해요 | 후기 중심 |
| 공부·열람 | `laptop_friendly` | 노트북 이용 친화 | 노트북 쓰기 좋아요 | 검증 시설·후기에서 사용 가능 |
| 공간·분위기 | `comfortable_space` | 편안한 공간 | 공간이 편안해요 | 후기 중심 |
| 공간·분위기 | `clean_space` | 깔끔하고 쾌적한 공간 | 깔끔하고 쾌적해요 | 후기 중심 |
| 공간·분위기 | `stay_friendly` | 오래 머물기 좋은 공간 | 오래 머물기 좋아요 | 라운지·후기와 공유 가능 |
| 공간·분위기 | `good_nearby_scenery` | 주변 경관 | 근처 경관이 좋아요 | 후기 중심 |
| 공간·분위기 | `outdoor_space` | 야외공간 | 야외공간이 좋아요 | 시설 정보와 공유 가능 |
| 책·자료 | `rich_collection` | 다양한 장서 | 책이 다양해요 | 장서 통계와 공유 가능 |
| 책·자료 | `frequent_new_books` | 신간 자료 | 신간이 잘 들어와요 | 후기 중심 |
| 책·자료 | `good_children_books` | 어린이책 | 어린이책이 좋아요 | 후기 중심 |
| 책·자료 | `easy_book_finding` | 책 찾기 편함 | 책 찾기가 편해요 | 후기 중심 |
| 프로그램 | `good_programs` | 만족도 높은 프로그램 | 프로그램이 좋아요 | 후기 중심 |
| 프로그램 | `diverse_programs` | 다양한 프로그램 | 프로그램이 다양해요 | 프로그램 통계·후기와 공유 가능 |
| 프로그램 | `program_culture_art` | 문화·예술 프로그램 | 문화·예술 프로그램이 좋아요 | 프로그램 분류와 공유 |
| 프로그램 | `program_reading_writing` | 독서·글쓰기 프로그램 | 독서·글쓰기 프로그램이 좋아요 | 프로그램 분류와 공유 |
| 아이·가족 | `children_friendly` | 아이와 방문하기 좋음 | 아이와 가기 좋아요 | 시설·프로그램·후기와 공유 가능 |
| 아이·가족 | `children_room` | 어린이자료실 | 어린이자료실이 좋아요 | 시설 정보와 공유 |
| 아이·가족 | `family_friendly` | 가족 친화 | 가족이 함께 가기 좋아요 | 후기 중심 |
| 아이·가족 | `good_children_programs` | 어린이 프로그램 | 어린이 프로그램이 좋아요 | 프로그램 대상·후기와 공유 가능 |
| 접근·편의 | `easy_to_visit` | 찾아가기 쉬움 | 찾아가기 쉬워요 | 후기 중심 |
| 접근·편의 | `parking` | 주차 편의 | 주차가 편해요 | 시설 정보와 공유 |
| 접근·편의 | `public_transport_access` | 대중교통 접근성 | 대중교통으로 가기 좋아요 | 후기 중심 |
| 접근·편의 | `wifi` | 와이파이 | 와이파이가 잘 돼요 | 시설 정보와 공유 |
| 접근·편의 | `accessible_facility` | 이동약자 편의 | 이동약자도 이용하기 좋아요 | 시설 정보와 공유 |
| 안내·관리 | `kind_guidance` | 친절한 안내 | 안내가 친절해요 | 후기 중심 |
| 안내·관리 | `well_managed` | 관리 상태 양호 | 관리가 잘 되어 있어요 | 후기 중심 |

제외 정책:

- “공지가 잘 정리돼 있어요”에 해당하는 `notice_clear`는 seed하지 않는다.
- “직원이 친절해요”에 해당하는 `staff_friendly`는 seed하지 않고 `kind_guidance`/“안내가 친절해요”를 사용한다.
- 모호한 “채광이 좋아요”에 해당하는 `good_natural_light`는 seed하지 않고 `good_nearby_scenery`/“근처 경관이 좋아요”를 사용한다.
- `not_too_crowded`, `low_occupancy`는 시점 의존 상태라 seed하지 않는다.

fixture 예시:

```json
{
  "code": "quiet_study",
  "label": "조용한 공부 환경",
  "tag_group": "study_reading",
  "is_review_selectable": true,
  "review_label": "조용히 공부하기 좋아요",
  "review_group": "study_reading",
  "review_display_order": 1,
  "is_active": true
}
```

### 7.5 도서관 rollup과 사실성 경계

도서관 추천 후보가 여러 도메인 태그와 비교될 수 있도록 다음 rollup을 지원한다.

- 노출 중인 프로그램의 `ProgramTag` → `LibraryTag(source_method=program_rollup)`
- 공개 후기의 `ReviewTag` → `LibraryTag(source_method=review_rollup)`
- 충분한 소장·인기 데이터가 있을 때 `BookTag` → `LibraryTag(source_method=book_rollup)`

rollup 계산 규칙:

- visible 후기만 포함한다.
- 고유 작성자 수 최소치, 사용자별 기여 상한, 시간 감쇠를 적용한다.
- 후기 1건의 태그가 도서관 전체 특징으로 과대해석되지 않게 한다.
- `review_rollup`은 추천·요약·경험형 필터에 사용할 수 있지만 공식 시설 사실을 만들지 않는다.
- `parking`, `wifi`, `children_room`, `accessible_facility` 같은 객관형 필터는 `data_status=verified`인 `LibraryFacilityProfile`의 명시적 `True` 또는 직접 근거(`field_rule|facility_rule|manual`)만 사용한다.

### 7.6 사용자 행동 태그 집계

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
list_libraries(region: str = "21", detail_region: str | None = None)
search_books(...)
get_book_detail(isbn13: str)
get_reader_recommendations(isbn13s: list[str])
find_libraries_by_book(isbn13: str, region: str, detail_region: str | None)
get_popular_books(...)
```

`list_libraries`는 `libSrch` 전체 페이지를 순회하여 `libCode` 선연결에 사용한다. 응답의 도서관명·주소·전화·좌표를 canonical `Library` 대체 원천으로 사용하지 않는다.

검증:

- ISBN은 문자열로 받는다.
- search 조건이 비어 전체 검색이 되는 요청은 명시적으로 허용한 경우만 보낸다.
- `dtl_region`을 쓰는 경우 region 관련 조합을 검증한다.
- API key는 cache key에서 제외한다.
- `get_reader_recommendations`는 ISBN 1~5개만 허용하고 입력 순서를 정규화한 cache key를 사용한다.
- `get_popular_books`는 전국 또는 `region`/`dtl_region` 범위만 지원한다. 특정 도서관 범위 client 메서드는 만들지 않는다.
- `docs.doc`, `libs.lib` 등 단건 object/복수 list/빈 값 변형을 `ensure_list()`로 통일한다.
- 응답의 ISBN, libCode, 지역 코드는 숫자처럼 보여도 문자열로 정규화한다.
- `itemSrch`, `bookExist`, `loanItemSrchByLib`는 기본 interface에 넣지 않는다. `bookExist`를 나중에 추가하더라도 전날 기준 상태임을 API 응답에 명시한다.

normalizer 반환 객체는 Django model이 아닌 dataclass 또는 TypedDict로 둔다.

### 9.2.1 정보나루 도서관 코드 선연결

```bash
python manage.py sync_data4library_libraries --region 21
```

매칭 순서:

1. 기존 활성 `LibraryExternalIdentifier`
2. canonical 이름 + 정규화 주소 exact
3. `LibraryAlias` + 정규화 주소 exact
4. 이름/alias + 전화 또는 좌표 근접 후보
5. 수동 검수

1~3의 높은 신뢰도만 자동 연결한다. 주소·좌표 단독 일치는 후보 report만 만든다. 정보나루에 참여하지 않는 도서관은 외부 ID 없이 정상 유지한다.

### 9.2.2 GMS client 경계

GMS를 사용하는 경우 `GMS_OPENAI_BASE_URL/chat/completions`를 Django에서 호출한다.

- Vue가 GMS key를 직접 사용하지 않는다.
- GMS 응답을 도서관 운영 여부, 시설 사실, 이미지 라이선스, 추천 점수, 태그 사실값으로 저장하지 않는다.
- 현재 MVP에는 GMS가 없어도 모든 핵심 기능이 동작해야 한다.
- 향후 한 줄 표현 보조 등에 사용할 때도 입력·출력 길이, timeout, 모델명, 비용·credit 로그를 제한한다.

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

공식 `getRestDeInfo`를 월 단위로 호출하되, 서비스 작업 단위는 **연도 전체**다.

권장 메서드:

```python
fetch_month(year: int, month: int) -> list[RawHoliday]
fetch_year(year: int) -> dict[int, list[RawHoliday]]
sync_year(year: int) -> PublicHolidayCalendar
```

요청·검증 정책:

1. `solMonth`는 `01`부터 `12`까지 순차 호출한다.
2. `_type=json`, `numOfRows=PUBLIC_HOLIDAY_NUM_OF_ROWS`를 명시한다.
3. `resultCode == "00"`인지 확인한다.
4. `totalCount > numOfRows`이면 page를 끝까지 조회한다.
5. `locdate`는 `yyyymmdd` 정수·문자열 모두 허용해 `date`로 변환한다.
6. `seq`, `dateKind`, `dateName`, `isHoliday` schema를 검증한다.
7. `isHoliday == "Y"`인 항목만 영속화한다.
8. 12개월 중 하나라도 실패하면 DB의 기존 complete 달력을 교체하지 않는다.
9. `totalCount=0`인 달도 HTTP·header·schema 검증이 정상이면 성공한 달로 계산한다.
10. 12개월 성공 뒤 transaction에서 해당 연도 항목을 upsert·정리하고 `PublicHolidayCalendar.is_complete=True`, `synced_month_count=12`로 갱신한다.
11. 완료된 연도의 운영표 재생성을 예약한다.

임시공휴일·대체공휴일이 공식 API에 반영된 뒤 같은 연도를 수동 재수집할 수 있도록 management command를 제공한다.

### 9.5 파일 import 공통

```text
파일 checksum 계산
→ 형식·헤더/schema validation
→ 부산 범위 검증
→ 문자열·숫자·URL 정규화
→ Library/LibraryAlias 매칭
→ domain upsert
→ reject·warning·merge report 파일
→ 구조화 로그·통계 출력
→ 관련 태그·운영표 재생성
```

원천 파일이 문서화된 형식과 다르면 데이터를 추측해 적재하지 않고 non-zero exit한다.

### 9.6 공식 이미지 CSV import

```bash
python manage.py import_library_images --file path/to/LibraryImage.csv
```

필수 헤더:

```text
도서관명,구/군,이미지경로,이미지경로2,출처URL,공공누리 유형,출처
```

정책:

- `도서관명`, `구/군` exact 또는 검수된 alias로 매칭한다.
- `이미지경로`, `이미지경로2`는 독립 URL 후보다. 첫 유효 URL을 대표 외관 이미지 후보로 둔다.
- CSV 행 존재와 실제 이미지 보유를 구분한다. 두 URL이 모두 비어 있으면 관계를 만들지 않는다.
- `출처URL`은 비어 있을 수 있으며 임의 URL을 생성하지 않는다.
- `공공누리 유형`의 주변 공백을 제거해 `license_code`에 저장하고 `출처`는 attribution 원문으로 보존한다.
- 라이선스 공란·미검증 asset은 `is_active=False`; 공개 응답은 fallback을 사용한다.
- 동일 URL이 서로 다른 도서관에 반복되면 asset 공유는 가능하지만 warning report에 기록한다.
- HTTP URL은 mixed-content와 링크 유효성을 검사한다. 검증 실패 시 fallback을 사용한다.
- 이미지 행만으로 새 도서관을 생성하지 않는다.

### 9.7 시설 파일 정규화·import

정식 입력은 JSON 배열 또는 JSONL이다. 현재 작업 파일처럼 JSON 객체가 구분자 없이 연속된 파일은 직접 import하지 않는다.

```bash
python manage.py normalize_library_facilities   --input path/to/working.json   --output path/to/facilities.normalized.json   --report path/to/facilities.normalize-report.json

python manage.py import_library_facilities   --file path/to/facilities.normalized.json   --status draft
```

- field set은 11개 `has_*` nullable boolean으로 고정한다.
- 값은 `true|false|null`만 허용한다.
- exact `(library_name, sigungu)` 또는 검수된 alias만 자동 매칭한다.
- 이름만 같고 구·군이 다르거나 null이면 correction map 없이는 reject한다.
- 동일 이름이 여러 행에 나타나면 자동 overwrite하지 않고 duplicate report를 만든다.
- 기본 `data_status=draft`; 최종 검수 뒤 별도 명령/admin으로 `verified` 승격한다.
- `draft` profile은 공개 시설 필터와 개인화 공식 가중치에서 제외한다.

### 9.8 필수 데이터셋 계약

| 데이터셋 | 실제 형식·키 | 영속 모델 | 커버리지·결측 처리 |
|---|---|---|---|
| 부산 전국도서관 표준 데이터 | JSON object의 `fields`, `records`; 28개 필드 | `Library`, `LibraryAlias`, 운영시간, 휴관 규칙, 통계 | 부산 기준 모체; 별칭·중복 override, 필드별 0 처리, 운영 충돌 unknown |
| 프로그램 강좌 | 문서상 JSON, `library_name`, `sigungu`; 실제 파일 현재 미첨부 | `Program`, `ProgramTag` | actual contract 미검증; 빈 목록 허용 |
| 도서관 외관 사진 | CSV 한국어 7개 헤더 | `MediaAsset`, `LibraryImage` | row scaffold와 asset coverage 구분; 라이선스 미검증은 비활성, fallback |
| 도서관 시설 | 정규화 후 JSON array/JSONL | `LibraryFacilityProfile` | 현재 작업 파일은 미완성; `draft`, null=unknown, verified True만 필터 |
| 한국천문연구원 공휴일 API | 월별 `getRestDeInfo`, `DATA_GO_KR_API_KEY` | `PublicHolidayCalendar`, `PublicHoliday` | 연도별 12개월 완전 수집; singleton/list/empty 정규화 |
| 정보나루 | `libSrch`, 책·소장·인기·reader 추천 API | 외부 식별자, `Book`, `LibraryHolding`, 인기 snapshot; 추천 cache | libCode 선연결, 미참여 도서관 정상, 미조회와 부재 구분 |

### 9.9 데이터 contract audit

```bash
python manage.py audit_source_data   --library-file path/to/전국도서관표준데이터_부산.json   --image-file path/to/LibraryImage.csv   --facility-file path/to/facilities.normalized.json   --output reports/source-audit.json
```

최소 검사:

- record/header count와 필수 필드
- canonical/alias 매칭률
- 중복 이름·주소·좌표 후보
- 운영시간과 휴관 문구 충돌
- 빈 값·0·전화·좌표 이상치
- 이미지 URL·라이선스·교차 도서관 중복
- 시설 boolean type·중복·지역 불일치·draft 상태
- 프로그램 파일이 없을 때 명시적 `not_checked`

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

프로필 설정 변경 뒤 오늘의 추천 기본 세트를 재생성할 필요는 없다. 변경값은 `여기는 어때요?` 계산에 즉시 반영하고 사용자별 캐시만 무효화한다.

---

### 10.4 기준정보·태그

| Method | URL | 설명 |
|---|---|---|
| GET | `/purposes/` | 6개 방문 목적 |
| GET | `/tags/` | 공통 태그 목록 |
| GET | `/tags/review-options/` | 후기 작성용 7개 그룹과 활성 선택지, 선택 최소·최대 수 |
| GET | `/metadata/regions/` | 지역 체크리스트 |
| GET | `/metadata/library-types/` | 도서관 유형 |
| GET | `/metadata/facilities/` | `LibraryFacilityProfile`의 11개 시설 필드 코드·표시명 |
| GET | `/metadata/program-categories/` | 프로그램 분류 |

`/tags/` query:

- `group`
- `profile_selectable=true`
- `review_selectable=true`
- `filterable=true`
- `review_group`

`GET /tags/review-options/` 응답은 프론트가 별도 문구 매핑 없이 바로 체크리스트를 그릴 수 있게 그룹화한다.

```json
{
  "min_select": 1,
  "max_select": 5,
  "groups": [
    {
      "code": "study_reading",
      "label": "공부·열람",
      "items": [
        {
          "id": 41,
          "code": "quiet_study",
          "label": "조용한 공부 환경",
          "review_label": "조용히 공부하기 좋아요"
        }
      ]
    }
  ]
}
```

---

### 10.5 홈 추천

#### GET `/home/recommendations/`

홈의 세 섹션을 한 응답으로 반환한다. 프론트는 `section_order`를 그대로 사용한다.

Query:

| 이름 | 필수 | 설명 |
|---|---|---|
| `sido`, `sigungu` | 아니오 | 명시적 서비스 지역. 없으면 서비스 기본 지역 |

응답 순서:

```text
오늘의 추천 도서관
→ 여기는 어때요?  # 조건을 충족한 회원에게만 visible=true
→ 테마별 추천
```

처리:

1. 날짜·지역의 `DailyLibraryRecommendationSet`을 조회한다.
2. 세트가 없으면 **추천 날짜의 `LibraryDailySchedule.status=open` 후보만** 사용해 오늘 예정 테마로 동기 최소 계산한다.
3. 다른 날짜의 추천 세트를 그대로 stale fallback으로 사용하지 않는다. 계산 실패 또는 운영표 불충분 시 `today.status=unavailable`과 빈 목록 또는 가능한 열린 후보 수만 반환한다.
4. 공통 기본 순위 상위 최대 3개를 `today`에 그대로 반환한다. 사용자 선호로 순서를 바꾸지 않는다.
5. 인증 사용자가 활성 `UserPreferredTag`, `UserPreferredRegion` 또는 1건 이상의 유효 행동 신호를 가지고 있으면 `for_you.visible=true`로 판정한다.
6. `for_you`도 추천 날짜의 `open` 후보만 사용하고 오늘의 추천 항목을 제외한 뒤 수동 선호와 임시·정식 행동 성향을 반영해 최대 3개를 계산한다.
7. 열린 후보가 부족하면 `today`와 `for_you` 모두 3개 미만을 반환할 수 있으며 `closed`, `unknown`, 운영표 누락 도서관으로 채우지 않는다.
8. `themes`에는 활성 `Purpose` 6개를 `display_order` 순서로 반환한다. 실제 테마 결과는 별도 endpoint에서 조회한다.

응답 예시:

```json
{
  "section_order": ["today", "for_you", "themes"],
  "region": {"sido": "부산광역시", "sigungu": null},
  "today": {
    "title": "오늘의 추천 도서관",
    "recommendation_date": "2026-06-22",
    "theme": {
      "code": "large_space",
      "label": "넓은 공간",
      "subtitle": "오늘은 조금 넓은 도서관으로 가볼까요?"
    },
    "items": [
      {"rank": 1, "library": {"id": 101, "name": "연제도서관"}},
      {"rank": 2, "library": {"id": 102, "name": "시민도서관"}},
      {"rank": 3, "library": {"id": 103, "name": "중앙도서관"}}
    ]
  },
  "for_you": {
    "title": "여기는 어때요?",
    "visible": true,
    "status": "available",
    "personalization": {
      "manual_preferences_applied": true,
      "behavior_preferences_applied": true,
      "behavior_status": "collecting",
      "signal_count": 12,
      "required_count": 20,
      "behavior_confidence": 0.6
    },
    "items": [
      {"rank": 1, "library": {"id": 111, "name": "해운대도서관"}},
      {"rank": 2, "library": {"id": 112, "name": "반여도서관"}},
      {"rank": 3, "library": {"id": 113, "name": "재송어린이도서관"}}
    ]
  },
  "themes": {
    "title": "테마별 추천",
    "items": [
      {"code": "study", "label": "조용히 공부하고 싶어요"},
      {"code": "book", "label": "책을 빌리러 가요"},
      {"code": "kids", "label": "아이와 함께 가요"},
      {"code": "program", "label": "문화프로그램을 즐기고 싶어요"},
      {"code": "mood", "label": "분위기 좋은 곳에 머물고 싶어요"},
      {"code": "nearby", "label": "가까운 곳이 좋아요"}
    ]
  }
}
```

비회원 또는 개인화 입력이 전혀 없는 회원은 `for_you.visible=false`, `items=[]`로 반환한다. 프론트는 해당 섹션을 렌더링하지 않는다.

#### GET `/home/theme-recommendations/`

Query:

- `purpose=study|book|kids|program|mood|nearby`
- `sido`, `sigungu`
- `lat`, `lng`
- `limit` 기본 `THEME_RECOMMENDATION_DEFAULT_LIMIT`, 최대 20

선택한 `PurposeTagRule`과 `PurposeMetricRule`만으로 계산한다. 오늘의 추천과 달리 날짜 순환 기준을 사용하지 않고, `여기는 어때요?`와 달리 사용자 수동·행동 선호를 더하지 않는다. `nearby`는 `lat`, `lng`가 없으면 400 또는 위치 미사용 fallback 정책을 명시적으로 적용한다.

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

`open_now`는 `LibraryDailySchedule`과 현재 시각으로 계산한다. 외부 API를 호출하지 않는다. 개관일은 확정되었지만 시간이 없는 경우 `is_open_now=null`이며, `open_now=true` 필터에는 포함하지 않는다.

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

목록 카드의 `facilities`에는 `LibraryFacilityProfile`에서 값이 `True`인 코드만 넣는다. `False`, `NULL`, profile 부재를 동일한 “없음”으로 단정하지 않는다. 상세 응답은 `facility_data_status=complete|partial|missing`과 11개 nullable boolean을 함께 제공할 수 있다.

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
- `page`, `page_size`

`libSrchByBook` 응답으로 소장 도서관을 조회한다. 초기 `libSrch(region=21)` 선연결 결과의 `libCode`를 먼저 사용하고, 미연결 code만 canonical/alias+주소로 보수적으로 재매칭한다. 낮은 신뢰도 또는 미매칭 외부 도서관으로 `Library`를 자동 생성하거나 `LibraryHolding`을 만들지 않고 구조화 로그·검수 큐에 남긴다. 응답의 `closed`, `operatingTime`은 매칭 참고용이며 내부 `LibraryDailySchedule`을 덮어쓰지 않는다.

#### GET `/books/recommendations/`

Query:

- `isbn13`: 1~5개. 반복 query parameter(`?isbn13=...&isbn13=...`)로 받는 방식을 권장

`recommandList(type=reader)`를 호출해 다음 읽을 책 후보를 반환한다. 반환 책은 `Book`으로 upsert하지만 추천 관계는 DB에 저장하지 않는다. 정규화된 ISBN 입력 조합은 24시간 단기 cache를 권장한다.

#### GET `/popular-books/`

- `scope=national|region`
- 범위별 필수 파라미터 검증
- 최신 snapshot 우선; 수집 주기는 기본 주 1회

---

### 10.8 프로그램

#### GET `/programs/`

필터:

- `q`: 프로그램명·도서관명
- `sido`, `sigungu`
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
- 태그는 활성 상태이며 `is_review_selectable=True`인 항목만 허용
- `tag_ids`는 필수이며 중복 없는 1~5개여야 함
- 이미지 최대 5장

#### GET/PATCH/DELETE `/reviews/{id}/`

- GET: 공개 후기
- PATCH/DELETE: 작성자 또는 관리자
- PATCH에서 `tag_ids`를 보내면 전체 교체하고, 생략하면 기존 태그 유지
- 빈 `tag_ids` 배열과 6개 이상 선택은 400 응답
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
    "ready": false,
    "provisional_available": true,
    "behavior_confidence": 0.65,
    "signal_count": 13,
    "required_count": 20,
    "breakdown": {
      "libraries": 3,
      "books": 5,
      "programs": 2,
      "reviews": 3
    },
    "calculated_at": "2026-06-22T09:30:00+09:00",
    "items": [
      {"tag_code": "quiet_study", "score": 0.82, "rank": 1},
      {"tag_code": "rich_collection", "score": 0.67, "rank": 2}
    ]
  },
  "manual": {
    "preferred_regions": ["21:21090"],
    "preferred_tags": [
      {"code": "quiet_study", "label": "조용한 공부 환경"}
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
∩ 해당 추천 규칙의 필수 조건
∩ 좌표가 필요한 목적이면 좌표 보유 도서관
```

사용 데이터:

- `Library`
- `LibraryDailySchedule`; `오늘의 추천 도서관`과 `여기는 어때요?`는 추천일 `status=open`만 허용하고, 테마별 추천은 운영 상태를 표시하거나 명시적 운영 필터가 있을 때 사용
- 최신 `LibraryStatisticSnapshot` 중 추천 지표에 유효한 양수·품질 플래그 통과 값
- `LibraryFacilityProfile(data_status=verified)`의 명시적 `True` 필드
- 활성 `LibraryTag`
- 향후 프로그램 수와 프로그램 rollup
- 후기 평균·개수와 후기 rollup
- 실제·대체 이미지 상태
- 요청 좌표와 거리
- 개인화 영역에서만 `UserPreferredRegion`, `UserPreferredTag`, `UserPreferenceItem`

사용하지 않는 데이터:

- 실시간 좌석·방문자 수
- 사용자의 영구 저장 현재 좌표

### 11.2 홈 섹션별 책임

| 섹션 | 대상 | 결과 수 | 개인화 | 중복 정책 |
|---|---|---:|---|---|
| 오늘의 추천 도서관 | 모든 사용자 | 최대 3 | 적용하지 않음 | 공통 기본 순위 유지 |
| 여기는 어때요? | 개인화 입력이 있는 로그인 회원 | 최대 3 | 수동·행동 선호 적용 | 오늘의 추천 3개 제외 |
| 테마별 추천 | 모든 사용자 | 기본 6, 최대 20 | 적용하지 않음 | 선택 목적 안에서 계산 |

홈의 화면 순서는 반드시 `오늘의 추천 도서관 → 여기는 어때요? → 테마별 추천`이다.

### 11.3 오늘의 추천 도서관

활성 `DailyRecommendationTheme`를 `display_order`로 정렬하고 날짜에 따라 예정 테마를 하나 결정한다.

```python
scheduled_index = target_date.toordinal() % len(active_themes)
scheduled_theme = active_themes[scheduled_index]
```

먼저 추천 날짜의 `LibraryDailySchedule.status=open`인 활성 도서관만 후보군으로 만든다. `closed`, `unknown`, 운영표 누락 도서관은 테마 점수 계산 전에 제거한다.

무작위로 테마를 바꾸지 않는다. 생성기는 예정 테마부터 활성 테마를 순서대로 순환하며 열린 후보 중 `DAILY_RECOMMENDATION_MIN_RESULT_COUNT`개 이상의 근거 있는 후보를 만들 수 있는 첫 테마를 실제 테마로 선택한다. 모든 테마가 기준을 충족하지 못하면 `rich_collection`을 최종 fallback으로 사용하지만 이때도 열린 후보만 허용한다. 실제 선택된 테마는 `DailyLibraryRecommendationSet.theme`에 저장하므로 같은 날짜·지역의 재요청은 동일한 테마와 subtitle을 사용한다. 지역별 기본 후보를 최대 `DAILY_RECOMMENDATION_CANDIDATE_LIMIT`만큼 미리 저장하고, 공개 응답은 기본 순위 상위 최대 `TODAY_RECOMMENDATION_LIMIT=3`개다. 열린 후보 자체가 3개 미만이면 가능한 수만 반환한다.

```text
today_score
= Σ(metric_rule.weight × normalized_metric)
+ Σ(tag_rule.weight × normalized_library_tag_score)
```

사용자 수동 선호와 행동 성향은 `today_score`에 더하지 않으며 응답 순서도 바꾸지 않는다.

### 11.4 오늘의 추천 초기 테마 6종

| code | subtitle | 지표 규칙 | 태그 규칙 |
|---|---|---|---|
| `large_space` | 오늘은 조금 넓은 도서관으로 가볼까요? | `building_area` 중심, `site_area` 보조 | 없음 또는 보조 공간 태그 |
| `rich_collection` | 서가 사이를 천천히 둘러보기 좋은 날이에요 | `book_count` | `rich_collection` 직접 태그는 보조 |
| `mood_space` | 분위기도 함께 즐겨보세요 | 없음 또는 낮은 공간 지표 | `good_nearby_scenery`, `outdoor_space` 등 검증된 후기 rollup |
| `study_seats` | 오늘은 차분히 앉아 있을 곳을 찾아볼까요? | `reading_seat_count` | `quiet_study`, `focused_atmosphere`, `comfortable_reading_space` |
| `family_outing` | 가족 나들이처럼 들르기 좋은 도서관이에요 | 어린이 관련 시설 존재 여부 | `children_room`, `children_friendly`, `family_friendly`, `good_children_books`, `good_children_programs` |
| `restful_space` | 잠깐 쉬어가도 좋은 공간을 골라봤어요 | 필요 시 낮은 비중의 공간 지표 | `comfortable_space`, `clean_space`, `stay_friendly` |

테마 간 의미가 겹치지 않도록 `mood_space`는 주변 경관·야외·장소 분위기에, `restful_space`는 내부 편안함·오래 머무름에 초점을 둔다.

다음은 초기 오늘의 추천 기준으로 사용하지 않는다.

- 주차·와이파이·엘리베이터 등 일반 시설 편의 종합
- 사용자 현재 위치에 따른 가까움
- 프로그램 다양성

이 정보들은 도서관 검색 필터·상세 정보, 프로필 선호와 `여기는 어때요?`, 테마별 `program`·`nearby`에서 사용한다.

### 11.5 여기는 어때요?

노출 조건:

```text
인증 사용자
∩ (
    활성 UserPreferredTag 존재
    or 활성 UserPreferredRegion 존재
    or (UserPreference.signal_count >= PERSONALIZATION_HOME_MIN_SIGNALS and UserPreferenceItem exists)
  )
```

후보군은 추천일의 `LibraryDailySchedule.status=open`인 공통 후보군에서 오늘의 추천 항목을 제외한 도서관이다.

```text
personal_score
= manual_tag_match
+ manual_region_match
+ behavior_tag_match × behavior_confidence
+ stable_quality_tiebreaker
```

- `manual_tag_match`: 사용자가 직접 고른 태그와 후보 `LibraryTag`의 일치도
- `manual_region_match`: 선호 지역과 후보 지역의 일치도
- `behavior_tag_match`: `UserPreferenceItem`과 후보 `LibraryTag`의 일치도
- `stable_quality_tiebreaker`: 검증 데이터 충실도, 유효 후기 수 등 낮은 비중의 안정적인 동점 처리값

행동 신뢰도:

```text
signal_count = 0       → 0
collecting             → min(signal_count / PERSONALIZATION_MIN_SIGNALS, 1)
ready                  → 1
pending or failed      → 마지막 성공 항목이 있으면 상태에 맞는 신뢰도, 없으면 0
```

`collecting` 신뢰도는 `PERSONALIZATION_COLLECTING_MAX_CONFIDENCE`를 넘지 않는다. 결과는 최대 `PERSONALIZED_HOME_RECOMMENDATION_LIMIT=3`개이며 오늘의 추천과 중복되면 안 된다. 일치 후보가 부족하면 선호 지역·데이터 충실도 기준의 **당일 open 후보**로 채울 수 있지만, 중복 제거 원칙을 유지한다. 열린 후보가 부족하면 3개 미만을 반환한다.

각 수동·행동 구성요소는 환경변수의 최대 보너스 비율을 넘지 않게 정규화한다. 사용자별 결과는 영속 테이블에 저장하지 않는다. Redis 단기 캐시는 가능하며 프로필 설정·저장·후기·성향 계산 변경 시 무효화한다.

### 11.6 행동 기반 임시·정식 성향

활성 행동 신호:

```text
library saves
+ book saves
+ program saves
+ review saves
+ visible authored reviews
```

`signal_count >= 1`이면 `UserPreferenceItem`을 계산할 수 있다.

```text
raw_tag_score
= Σ(interaction_type_weight × entity_tag_score)

normalized_tag_score
= group-aware normalization(raw_tag_score)
```

- `collecting`: 임시 항목이며 여기는 어때요?에서 신뢰도 축소 적용
- `pending`: threshold를 충족해 정식 계산 대기 중
- `ready`: 전체 행동 가중치 적용
- `failed`: 마지막 성공 항목이 있으면 stale 표시 후 제한적으로 사용 가능
- 데이터가 없는 태그는 임의로 추론하지 않는다.
- 도서관·책·프로그램·후기 기여 수를 따로 보존한다.

### 11.7 테마별 추천

```text
theme_score
= Σ(PurposeTagRule.weight × candidate_tag_score)
+ Σ(PurposeMetricRule.weight × normalized_metric)
```

대표 입력:

| 목적 | 대표 태그·지표 |
|---|---|
| study | 정적 좌석 수, 조용함, Wi-Fi, 열람실, 늦은 운영 |
| book | 장서 수, 책 주제 관련 태그, 자료실·디지털실 |
| kids | 어린이자료실, 수유실, 가족·어린이 프로그램, 후기 태그 |
| program | 향후 프로그램 수, 프로그램 분류·대상 태그 |
| mood | 카페, 라운지, 야외공간, 분위기 후기 태그, 이미지·평점 |
| nearby | 거리, 해당 날짜 운영, 주차·접근성 |

테마별 추천은 사용자가 선택한 목적을 명확히 유지하기 위해 개인화 보너스로 재정렬하지 않는다. `nearby`의 거리는 요청 좌표로만 계산한다.

### 11.8 정규화·동점 처리

- 결측값은 0으로 단정하지 않고 규칙별 missing 정책을 적용한다.
- 큰 통계값은 log 또는 percentile 정규화를 사용한다.
- 후기 rollup은 최소 후기 수·고유 작성자 수·시간 감쇠 조건을 통과한 값만 사용한다.
- 오늘의 추천 동점: 검증 데이터 충실도, 유효 후기 수, 도서관명 순
- 여기는 어때요? 동점: 개인화 일치 태그 수, 선호 지역, 검증 데이터 충실도, 도서관명 순
- 테마별 추천 동점: 해당 테마 필수 규칙 충족도, 거리 또는 데이터 충실도, 도서관명 순
- MVP 응답에는 도서관별 추천 문장을 생성하지 않는다. `score_detail`은 내부 검증과 테스트에만 사용한다.

### 11.9 Haversine

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

`lat`는 -90~90, `lng`는 -180~180 범위를 검증하고 원문 좌표를 DB나 분석 로그에 저장하지 않는다.

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

### 12.4 정보나루 도서관 코드

- `libSrch(region=21)` 전체 동기화 결과는 DB의 `LibraryExternalIdentifier`가 기준이다.
- 미매칭 후보 report는 cache가 아니라 파일/관리 큐로 남긴다.
- 재동기화 시 기존 활성 연결을 먼저 검증하고 code가 사라졌다고 즉시 canonical `Library`를 비활성화하지 않는다.

### 12.5 다독자 기반 다음 책 추천

- `recommandList` 입력 ISBN 조합별 24시간 cache 권장
- 반환 책은 `Book`에 upsert하고 추천 관계 자체는 영속화하지 않음
- upstream 실패 시 같은 입력 조합의 stale cache를 제한적으로 사용할 수 있음

### 12.6 인기 도서

- 주 단위 수집을 기본으로 하되 홈 노출 정책에 따라 더 자주 갱신 가능
- 전국·지역 범위의 최신 fresh snapshot 우선
- 집계 범위·기간·필터를 response에 포함
- 특정 도서관 범위는 현재 필수 API에서 지원하지 않음

### 12.7 일자별 운영표

- 향후 180일 생성
- 운영시간·휴관·공휴일 변경 시 영향 범위 재생성
- 공휴일 규칙이 있는 도서관은 해당 연도의 `PublicHolidayCalendar.is_complete=True`일 때만 공휴일 여부를 확정
- 달력 불완전·규칙 해석 실패·행 누락은 `unknown`으로 보수적으로 처리
- 조회 중 행이 없으면 동기 계산 가능하되 외부 API 호출 금지

### 12.8 홈 추천

- 오늘의 추천 도서관: 추천일 `open` 후보로 지역별 매일 생성, 기본 후보 20개 내외, 공개 최대 3개는 공통 순위 유지
- 여기는 어때요?: 추천일 `open` 후보에서 요청 시 계산, 사용자별 단기 캐시 가능, 영속 결과 테이블 없음
- 다른 날짜 추천 결과를 당일 stale fallback으로 그대로 사용하지 않음
- 열린 후보가 부족하면 3개 미만 반환; 휴관·미확인 후보로 채우지 않음
- 테마별 추천: 목적·지역·좌표 query별 단기 캐시 선택
- 프로필 설정·저장·후기 변경 시 여기는 어때요? 캐시와 사용자 성향 캐시만 무효화
- 오늘의 추천 기본 세트는 사용자 변경으로 재생성하지 않음

### 12.9 이미지 해석

- 기본 규칙은 짧은 in-process 또는 Redis 캐시 가능
- `MediaAsset`·`DefaultMediaAssetRule` 변경 시 캐시 무효화
- 사용자 업로드 변경 시 해당 엔터티 응답 캐시 무효화

---

## 13. Celery 작업

| task | 주기·트리거 | 역할 |
|---|---|---|
| `libraries.import_standard_dataset` | 새 파일·수동 | 도서관·운영시간·휴관·통계 upsert |
| `libraries.import_facility_dataset` | 정규화 파일·수동 | 시설 프로필 nullable boolean upsert; 기본 `draft`, 검수 후 `verified` |
| `libraries.sync_public_holidays` | 초기 배포 + 매년 1월 초 + 공식 변경 시 수동 | 지정 연도 1~12월 완전 수집·transaction 반영 |
| `libraries.rebuild_daily_schedules` | 매일 00:01·원천 변경 후 | 향후 운영표 생성; 홈 추천보다 먼저 완료 |
| `libraries.rebuild_library_tags` | 도서관 데이터 변경 후 | 직접 태그 재계산 |
| `libraries.rebuild_program_rollups` | 프로그램 변경 후 | 프로그램 태그 집계 |
| `libraries.rebuild_review_rollups` | 후기 변경 후 | 후기 태그 집계 |
| `libraries.sync_data4library_codes` | 초기 적재 후 월 1회 또는 수동 | `libSrch(region=21)` 외부 code 검증·선연결 |
| `books.refresh_popular_books` | 주 1회 기본 | 전국·부산·세부 지역 인기 도서 snapshot |
| `books.refresh_book_metadata` | 필요 시 | stale 책 상세 갱신 |
| `programs.sync_programs` | 원천 주기 | 프로그램 upsert·soft delete |
| `media_assets.audit_external_links` | 월 1회 | 공식 이미지 링크·license 점검 |
| `recommendations.generate_daily_sets` | 매일 00:10 | 당일 open 후보만으로 지역별 오늘의 추천 기본 후보 생성 |
| `preferences.rebuild_user_preference` | 행동 변경 후 debounce | 태그 기반 자동 성향 재계산 |
| `preferences.reconcile_states` | 매일 | 누락·실패·threshold 하락 보정 |
| `community.cleanup_deleted_images` | 삭제 후 | storage 객체 정리 |

모든 task는 idempotent하게 구현한다. 초기 배포에서는 현재 연도 공휴일 command를 먼저 실행한다. 이후 연초 공휴일 작업은 1월 첫 운영일 새벽에 해당 연도 전체를 수집하도록 예약할 수 있으며, 팀 운영상 자동화를 쓰지 않으면 같은 management command를 연초 체크리스트로 실행한다. `rebuild_daily_schedules`가 완료된 뒤 `generate_daily_sets`가 실행되도록 task 순서를 보장한다.

동일 대상 task 중복 실행 방지:

```text
preference:{user_id}
library-tags:{library_id}
today-recommendation:{date}:{region_key}
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

### 14.3 도서관 매칭·중복 처리

1. canonical 정규화 이름 + 시군구 + 정규화 주소 exact
2. `LibraryAlias` + 시군구 + 정규화 주소 exact
3. 이름/alias + 시군구 + 전화 또는 좌표 근접을 검수 후보로 생성
4. 명시적 merge override
5. 그 외 신규 생성 또는 reject

전국도서관표준데이터의 제공기관코드를 개별 도서관 ID로 사용하지 않는다. 동일 주소·좌표만으로 자동 병합하지 않는다. same-building distinct library 사례가 있으므로 자동 merge는 1~2 또는 검수된 override만 허용한다.

canonical `Library`를 선택한 뒤 원천 명칭이 다르면 `LibraryAlias(alias_type=source_name|duplicate_merge)`를 upsert한다.

### 14.4 필드 변환·품질 플래그

- 빈 문자열 → nullable 필드는 null
- 숫자 문자열 → 안전한 정수·decimal 변환
- 면적의 0 → null + `ambiguous_zero`
- 연속간행물·비도서의 0 → 실제 0 유지
- 장서·좌석·대출정책 0 → 원문 유지 + 품질 플래그; 추천 지표는 유효한 양수만 사용
- 좌표 부산 범위·형식 검증
- 전화번호 placeholder/형식 이상은 공개값에서 제외하고 원문·warning 보존
- 행정구역 alias 정규화
- `제공기관코드/명`, `데이터기준일자`, 원천 행 hash를 `Library` provenance 필드에 저장

### 14.5 운영시간·휴관

- `평일운영시작/종료시각`은 월~금에, `토요일운영시작/종료시각`은 토요일에만 확장한다. 토요일 시간을 일요일에 복사하지 않는다.
- 표준 데이터에 일요일 전용 시간은 없지만 휴관 문구가 비휴관일을 확정할 수 있다. 예를 들어 “월요일 휴관”이 명확히 파싱되면 일요일은 `open`이되 시간은 null이다. 문구가 모호하면 `unknown`이다.
- `status=open`과 정확한 시간의 존재를 분리한다. `is_open_now`는 시간이 없으면 null이다.
- `공휴일운영시작/종료시각`은 공휴일 규칙으로 저장하고 실제 날짜는 완전한 공휴일 달력으로 판정한다.
- `00:00~00:00`을 24시간 운영으로 해석하지 않는다.
- 휴관 문구가 공휴일 휴관인데 공휴일 시간이 0이 아니거나, 토요일 휴관인데 토요일 시간이 0이 아니면 `source_conflict`; 해당 날짜 `unknown`.
- `휴관중`은 전체 휴관으로 처리한다. `휴관`, 괄호 예외, 자료실만의 휴실 등은 raw text를 보존하고 확정하지 못한 범위는 `unknown`이다.
- parser는 tokenized weekday, nth weekday, 공휴일·대체공휴일, 연중무휴, 전체 휴관의 지원 범위를 version으로 관리한다.
- unknown/conflict가 있어도 import 전체를 실패시키지 않지만 홈 추천 후보에는 들어가지 않는다.

### 14.6 공휴일 연도 전체 수집

```bash
python manage.py sync_public_holidays --year 2026
```

실행 절차:

1. 초기 배포 또는 연초 운영일에 대상 연도를 지정
2. 1월부터 12월까지 `getRestDeInfo` 호출
3. 각 월의 HTTP·header·schema·pagination 검증; `totalCount=0`인 정상 빈 달도 성공 처리
4. `isHoliday=Y`만 정규화
5. 모든 월 성공 뒤 transaction으로 연도 항목 반영
6. `PublicHolidayCalendar(is_complete=True, synced_month_count=12)` 확정
7. 해당 연도의 `LibraryDailySchedule` 재생성 예약

한 월이라도 실패하면 non-zero exit와 구조화 로그를 남기고 기존 complete 달력은 유지한다. 임시공휴일 발표 뒤 같은 command를 다시 실행할 수 있다.

### 14.7 시설 import

`9.7 시설 파일 정규화·import` 계약을 따른다.

현재 작업 파일에서 확인된 유형의 오류를 자동 보정하지 않는다.

- top-level JSON array가 아님
- `sigungu` 누락 또는 실제 표준도서관 지역과 불일치
- 같은 `library_name`이 서로 다른 지역으로 중복
- `남향분관`/`남항분관` 같은 이름 오타

correction map 형식 예:

```yaml
- source_name: 영도도서관 남향분관
  source_sigungu: 영도구
  canonical_name: 영도도서관 남항분관
  canonical_sigungu: 영도구
  reason: source_typo
```

correction 적용도 audit report에 남긴다. `--status verified`는 검수 완료 파일에만 허용한다.

---

## 15. 프로그램 import

```bash
python manage.py import_programs --file path/to/programs.json
```

처리:

1. `library_name`, `sigungu`로 개최 도서관 매칭. 매칭 실패 시 프로그램 행만으로 새 도서관을 생성하지 않고 reject report에 기록
2. 분류·대상 코드 정규화
3. 날짜 파싱
4. 외부 key 생성
5. Program upsert
6. 이번 입력에 없는 기존 provider 행의 soft delete 정책 적용
7. ProgramTag 재계산
8. 개최 도서관 program rollup 재계산

같은 제목이라도 날짜가 다르면 하나로 병합하지 않는다.

원천 `application_status`는 `application_status_raw`에 보존하지만 서비스 내부 신청 상태 테이블로 확장하지 않는다. 원천에 없는 설명·장소·정원·비용·이미지는 생성하지 않는다.

---

## 16. 쿼리·성능 설계

### 16.1 도서관 목록

권장 queryset:

- `select_related`로 latest stat을 직접 가져오기 어렵다면 Subquery 또는 별도 current FK 고려
- 대표 이미지 `Prefetch`
- `facility_profile`을 `select_related`하고 응답에는 `True`인 시설만 노출; active LibraryTag는 `Prefetch`
- `Exists`로 사용자 저장 여부 annotate
- 리뷰 평균·수는 annotation 또는 집계 캐시

### 16.2 시설·태그 필터

시설 필터는 `facility_profile__data_status="verified"`와 해당 nullable boolean `True`를 함께 요구한다. `draft`, null, profile 부재를 `False`로 표현하지 않는다.

태그 필터는 다음 규칙을 따른다.

다중 태그 AND의 기본 형태:

```text
filter(library_tags__tag_id__in=tag_ids)
→ annotate distinct matched tag count
→ matched_count = len(tag_ids)
```

태그의 사실성에 따라 source를 제한한다.

- 객관형 필터(도서관 유형, 운영, 주차, 와이파이, 어린이자료실, 이동약자 편의 등): `field_rule|facility_rule|manual` 또는 `data_status=verified`인 `LibraryFacilityProfile`의 명시적 `True`만 사용
- 경험형 필터(편안함, 오래 머물기 좋음, 주변 경관, 안내·관리 등): 최소 표본 기준을 충족한 `review_rollup` 사용 가능
- 프로그램 관련 필터: 현재 노출 중인 프로그램에서 계산된 `program_rollup` 사용 가능
- rollup과 direct 연결이 함께 존재해도 distinct `tag_id` 기준으로 한 번만 집계

후기 선택 태그를 근거로 `LibraryFacilityProfile`의 nullable boolean을 `True`로 변경하지 않는다.

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

- `tag_group`, `review_group`, 프로필·후기·필터 선택 가능 여부 필터
- `label`과 `review_label` 동시 미리보기 및 후기 노출 순서 편집
- `is_review_selectable=True`인데 `review_label/review_group`이 비어 있으면 저장 거절
- code 변경 경고
- 비활성화 시 연결 영향 확인

### Libraries

- 별칭·외부 식별자·운영시간·휴관·통계·시설 프로필·태그·이미지 inline
- 시설 프로필 부재·`draft|verified`·nullable 필드 필터
- 낮은 신뢰도의 외부 코드 매칭과 alias 충돌 검수 action
- 운영표 재생성 action
- 태그 재계산 action

### Media assets

- 원본/저장 이미지 미리보기
- license·attribution 필수 검증
- 기본 이미지 규칙 충돌 검사

### Books

- ISBN·제목 검색
- KDC·BookTag 확인
- holding 관계·인기 snapshot 조회

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
- 후기 선택 가능 Tag의 `review_label/review_group` 필수 검증
- 확정 ReviewTag seed 29개 code unique, 7개 그룹 순서 검증
- `notice_clear`, `staff_friendly`, `good_natural_light`, `not_too_crowded` seed 부재 검증
- 각 domain tag unique constraint
- KDC→BookTag
- program_type/target→ProgramTag
- facility→LibraryTag
- 동적 상태 태그 생성 금지
- rebuild idempotency

### 19.3 이미지·시설 실제 계약

- 이미지 CSV 7개 한국어 헤더 검증
- CSV 행은 있으나 URL 둘 다 공란 → 유형 fallback
- URL 하나 → 정상
- 라이선스 공란 → asset 비활성 + fallback
- 서로 다른 도서관의 동일 URL → warning report
- 시설의 연속 JSON 객체 파일 → direct import 실패
- normalized array/JSONL만 허용
- 시설 행 없음 → profile 미생성
- 시설 필드 null → None, 명시적 false → False
- draft profile → 공식 긍정 필터 불통과
- verified + True만 긍정 필터 통과
- 이름 동일·지역 불일치/중복은 correction 없으면 reject

### 19.4 도서관 운영·공휴일

- 단순 주간 휴관
- 첫째·셋째 요일 휴관
- 공휴일 휴관
- 특정일 예외 우선
- `00:00~00:00` unknown 처리
- 임시 휴관
- 180일 운영표 재생성
- 공휴일 client가 1~12월을 모두 호출하는지
- 공휴일이 없는 달의 `totalCount=0` 정상 응답도 성공 월로 집계하는지
- `numOfRows>=20`, pagination, `resultCode`, `isHoliday=Y` 필터 검증
- 한 월 실패 시 기존 complete 달력을 보존하고 `is_complete`를 잘못 확정하지 않는지
- 달력 불완전 시 공휴일 의존 운영 판정이 unknown인지

### 19.5 프로그램

- 같은 제목·다른 날짜는 별도 Program
- 같은 provider+external key는 upsert
- 원천에 없는 설명·장소·정원·비용·이미지를 추정하지 않음
- ProgramSession 모델 없음
- 분류·대상 태그 생성
- 분류별 fallback 이미지

### 19.6 커뮤니티

- 후기 도서관 필수
- 평점 1~5
- 관련 책·프로그램 중복 방지
- 활성 review-selectable 태그만 허용
- 후기 생성 시 태그 1~5개 필수
- 중복 태그, 빈 배열, 6개 이상 선택 거절
- PATCH에서 `tag_ids` 제공 시 전체 교체, 생략 시 기존 연결 유지
- visible 후기만 review rollup에 포함
- review rollup이 `LibraryFacilityProfile`의 boolean을 변경하지 않음
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

- signal_count 0이면 collecting이며 자동 항목 없음
- 1건 이상 threshold 미만이면 collecting 임시 항목 생성 가능
- threshold 충족 pending
- 계산 성공 ready
- 신호 감소 시 collecting 복귀, 0이면 항목 제거
- `UserPreferenceItem`이 tag FK 중심
- library/book/program/review source count
- 수동 선호가 signal_count에 포함되지 않음
- collecting 행동 신호는 신뢰도 축소 후 여기는 어때요?에 반영
- 수동 선호는 threshold 미만에도 여기는 어때요?에 반영

### 19.9 추천

- 홈 섹션 순서가 오늘의 추천 → 여기는 어때요? → 테마별 추천인지 확인
- 같은 날짜·지역의 오늘의 추천 항목이 사용자와 무관하게 동일한지 확인
- 오늘의 추천·여기는 어때요?에 `closed`, `unknown`, 운영표 누락 도서관이 포함되지 않는지 확인
- 열린 후보가 3개 미만일 때 휴관 후보로 채우지 않고 짧은 목록을 반환하는지 확인
- 6개 일일 테마와 subtitle 날짜 순환 재현성 및 후보 부족 시 다음 테마 fallback
- `DailyRecommendationTagRule`의 source_scope·후기 최소 근거 검증
- 여기는 어때요?가 개인화 입력 없는 회원·비회원에게 숨겨지는지 확인
- 여기는 어때요? 결과가 오늘의 추천과 중복되지 않는지 확인
- collecting 행동 신호의 confidence 축소와 ready 전체 가중치 적용
- 테마별 추천이 개인화로 재정렬되지 않는지 확인
- 실시간 좌석 데이터를 참조하지 않음
- MVP 응답에 도서관별 추천 문장을 생성하지 않음

### 19.10 외부 API contract

- timeout, malformed response, 429/backoff, empty result
- API key/Authorization masking
- `docs.doc`, `libs.lib`, `items.item` object/list/empty 정규화
- ISBN 문자열 유지, 5개 초과 거절
- `libSrch(region=21)` pagination과 외부 code 선연결
- canonical/alias exact 매칭 성공, 낮은 신뢰도 미연결
- `libSrchByBook` 기존 external id 우선, 미매칭 holding 미생성
- 공휴일 12개월 완전성, 단일 item/list/빈 달 정규화
- percent-encoded 공공데이터 키 중복 인코딩 방지

### 19.11 데이터 품질

- 220행/28필드 표준 JSON baseline contract와 schema drift
- 잘못된 좌표·placeholder/형식 이상 전화번호
- 동일 시설 중복 후보와 same-building distinct library 비병합
- 공휴일/토요일 휴관 문구와 운영시간 충돌 → unknown
- 빈 URL, 라이선스 공란, 교차 도서관 동일 이미지 URL
- 잘못된 날짜와 필드별 0값 정책
- 시설 draft·중복·지역 불일치·이름 오타
- 프로그램 원본 부재 → not_checked 상태
- reject, warning, merge, audit report 생성

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
- 대상 연도 1~12월 공휴일 완전 수집·운영표 생성
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
- 공통 Tag seed와 확정된 후기 선택 태그 29개 seed
- MediaAsset·기본 이미지 규칙
- 공통 예외·API schema

### Phase 1: 도서관·소스 계약

- actual source audit command
- standard import + alias/merge override
- 운영시간·휴관 parser + conflict unknown
- 공휴일 연도 전체 수집
- 일자별 운영표
- 정보나루 `libSrch(region=21)` 외부 code 선연결
- 검색·상세
- 이미지 CSV import
- 시설 파일 정규화, draft import, 검수 후 verified

### Phase 2: 홈·기본 추천

- Purpose 6종·규칙 seed
- 오늘의 추천 테마 6종·subtitle·metric/tag 규칙 seed
- 당일 open 후보만 사용하는 오늘의 추천 세트와 공통 최대 3개, 후보 부족 시 결정론적 테마 fallback
- 홈 섹션 순서와 통합 API
- 테마별 추천 endpoint
- 개인화 없는 상태의 재현성 테스트

### Phase 3: 책

- 정보나루 client
- 검색·상세
- BookTag
- 소장 도서관
- 다독자 기반 다음 책 추천 cache
- 전국·지역 인기 도서

### Phase 4: 프로그램

- JSON import
- ProgramTag
- ProgramImage·분류 fallback
- 목록·상세·저장

### Phase 5: 커뮤니티·나의 나들이

- 후기 CRUD
- 관련 책·프로그램
- 확정된 7개 그룹·29개 ReviewTag 선택지와 1~5개 검증
- 후기 이미지
- 네 종류 저장
- 작성 후기·저장 후기 구분

### Phase 6: 프로필 설정·개인화

- 프로필 화면·설정 화면 API
- 선호 지역·태그 체크리스트
- UserPreference 임시·정식 상태
- tag 중심 UserPreferenceItem
- 여기는 어때요? 노출 조건·중복 제거·최대 3개
- collecting 신뢰도 축소와 ready 전체 행동 가중치

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

- 화면 순서: 오늘의 추천 도서관 → 여기는 어때요? → 테마별 추천
- 같은 날짜·지역에 모든 사용자에게 동일한 당일 open 도서관 기반 오늘의 추천 최대 3개
- 6개 일일 기준과 확정 subtitle 순환
- 개인화 입력 있는 회원에게만 여기는 어때요? 최대 3개
- 여기는 어때요?와 오늘의 추천 사이 중복 없음
- 오늘의 추천·여기는 어때요?에 `closed`, `unknown`, 운영표 누락 도서관이 포함되지 않음
- 열린 후보가 부족하면 휴관 후보로 채우지 않고 3개 미만을 허용
- 하단 6개 테마별 추천과 목적별 결과 조회
- 일반 시설 편의는 오늘의 추천이 아니라 필터·상세·개인화에서 사용

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
- 다독자 기반 다음 책 추천
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

- load 가능한 정제 fixture와 원본 checksum·audit report
- `.env` 키 이름 `GMS_API_KEY`, `GMS_OPENAI_BASE_URL`, `DATA_GO_KR_API_KEY`, `DATA4LIBRARY_API_KEY` 고정
- 공휴일 12개월 완전 수집
- 표준 JSON alias/중복 검수, 이미지 CSV import, 시설 JSON 정규화 command
- 정보나루 `libSrch` code 선연결과 selected API contract
- Celery 주기 작업
- stale·upstream 장애 정책
- structured logging

---

## 24. 구현 시 최종 확인 항목

1. 시설 작업 파일을 JSON 배열 또는 JSONL로 먼저 정규화하고, `true/false`는 그대로 저장하며 행 부재·필드 누락은 별도의 미확인 상태로 유지하는지 확인한다. 초기 적재는 `draft`, 공식 필터 사용 전에는 `verified` 전환을 요구한다.
2. 프로그램 제공 파일에 안정적인 원천 ID가 있는지 확인하고 없으면 hash 구성 필드를 확정한다.
3. 확정된 후기 태그 29개의 `code`는 유지하고, 사용자 문구를 바꿀 때는 `review_label`만 수정한다.
4. 프로필 체크리스트에 노출할 태그 수와 그룹을 제한한다.
5. 행동 신호별 기본 가중치와 중복 태그 상한을 algorithm version으로 고정한다.
6. 후기 작성 신호와 후기 저장 신호의 상대 가중치를 확정한다.
7. 도서관 program/review rollup의 최소 표본수를 확정한다.
8. 공식 이미지의 공공누리 유형별 변형·썸네일 정책을 확인한다.
9. `recommandList`의 ISBN 최대 5개, 결과 순서, cache key 정규화를 contract test로 검증한다.
10. 매년 초 공휴일 12개월 수집을 Celery beat로 자동화할지, 연초 management command 실행 절차로 운영할지 팀이 결정한다.
11. MVP 배포 환경에서 Celery·Redis를 사용할지, management command 수동 실행으로 대체할지 팀이 결정한다.

---

## 25. 데이터/API 최종 검수 기준선

현재 첨부 파일 기준 QA baseline:

| 대상 | 기준선 |
|---|---|
| 부산 표준 JSON | 220 records, 28 fields, 16개 구·군 |
| 도서관 유형 | small 165, public 53, children 2 |
| 표준 운영 충돌 | 공휴일 문구/시간 충돌 29, 토요일 문구/시간 충돌 2, `휴관중` 3 |
| 이미지 CSV | 220 rows, 실제 이미지 보유 19, 두 번째 URL 17, 라이선스 공란 이미지 보유 행 3 |
| 시설 작업 파일 | 연속 객체 41, exact pair 37, 지역 누락·불일치 name-only 3, 이름 오타 미매칭 1, 동일 이름 중복 1 |
| 프로그램 | 실제 원본 파일 미첨부로 contract 미검증 |

정확한 행 목록과 checksum은 `library_outing_dataset_api_audit_v2_4.md`를 따른다. 파일이 바뀌면 exact count assertion보다 schema와 비율·warning threshold를 우선하고 baseline을 갱신한다.

---

## 26. 참고 문서

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
