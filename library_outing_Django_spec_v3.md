# 도서관 나들이 Django 개발 명세서 v3

- 문서 버전: 3.0
- 작성 기준일: 2026-06-23
- 기준 ERD: `library_outing_ERD_v3.md`
- 대상: Django REST API 백엔드, 데이터 import·동기화 작업, 추천·개인화 서비스
- 1차 서비스 범위: 부산 지역 MVP, 전국 확장 가능한 코드 구조

---

## 1. 목적과 전제

이 문서는 최종 페이지 구조를 Django 앱, `models.py`, REST API, import·동기화 작업으로 옮기기 위한 구현 기준이다.

1. 모든 사용자에게 동일한 **오늘의 추천 도서관** 최대 3개
2. 선호 또는 행동 데이터가 있는 회원에게만 보이는 **여기는 어때요?** 최대 3개
3. 사용자가 직접 선택하는 홈 공개 테마 5개: `study`, `book`, `kids`, `mood`, `nearby`
4. 도서관 검색·필터·상세·당일 운영 여부·비슷한 도서관 조회
5. 도서 검색·상세, 부산 소장 도서관, 주간 인기 도서 조회
6. 문화 프로그램 검색·필터·개최 도서관 연결
7. 도서관 후기 커뮤니티, 조회수·좋아요, 관련 책·프로그램, 경험 태그
8. 저장한 도서관·책·프로그램, 좋아요한 후기, 작성 후기의 나의 나들이
9. 선호 목적·지역·태그 설정과 행동 기반 성향 분석
10. 공공누리 출처문구 오버레이와 유형별 대체 이미지
11. 공휴일 12개월 완전 수집, 일자별 운영표, 일일 추천 생성
12. 실제 데이터셋의 이름·지역 오류를 안전하게 `Library.id`로 매칭하는 import 파이프라인

서비스 내부 프로그램 신청·예약·결제·참여 이력, 실시간 열람실 잔여좌석, 후기 자동 텍스트 태깅, AI가 직접 결정하는 추천 순위는 범위에서 제외한다.

### 1.1 고정 정책

- 가입 입력은 이메일·닉네임·비밀번호다.
- `User`에 기본 지역이나 현재 좌표를 저장하지 않는다.
- 사용자가 직접 고른 선호 목적·지역·태그는 행동 성향과 별도로 저장한다.
- 선호 시설은 `facility_parking`, `facility_wifi`, `facility_lounge` 같은 객관 시설 태그를 `UserPreferredTag`로 선택한다.
- 홈 공개 테마는 5개다. `program` 목적은 `Purpose.is_home_theme=False`로 유지해 프로필 선택·프로그램형 분석·개인화에 사용한다.
- 외부 `library_name`은 import 매칭 입력일 뿐 FK가 아니다. 매칭 뒤 모든 관계는 내부 `Library.id`를 사용한다.
- 태그 동일성은 표시문구가 아니라 의미와 `Tag.code`로 판단한다.
- 객관 시설 존재와 후기 체감은 별도 태그다. 예: `facility_parking`과 `review_parking_convenient`는 함께 표시할 수 있다.
- 동일 `tag_id`가 여러 근거로 생성된 경우에만 화면·유사도 계산에서 병합한다.
- 후기 작성은 1~200자 본문, 경험 태그 1~5개, 선택적 관련 책·프로그램으로 구성한다. 별도 제목·별점·방문 목적 FK는 사용하지 않는다.
- 후기 저장은 없다. `UserReviewLike`가 좋아요 원본 관계이며 `UserReview.like_count`는 집계 캐시다.
- 후기 조회수는 공개 상세 조회에서 원자적으로 증가시킨다.
- 나의 나들이 행동 신호는 도서관·책·프로그램 저장, 좋아요한 후기, 공개 가능한 작성 후기다.
- 최근성은 코드 설정으로 관리한다. 기본 권장은 90일 반감기, 최대 365일 관측창이다.
- `open_today`와 `open_now`를 구분한다. 둘은 영구 태그가 아니다.
- `weekend_open=true`는 가장 가까운 토·일 중 적어도 하루가 `open`인 경우다.
- `holiday_status=open|closed|unknown`은 지정 공휴일 또는 가장 가까운 공휴일의 운영표를 기준으로 한다.
- 늦게까지 운영 필터의 UI 기준은 `18:00`이다.
- 오늘의 추천과 여기는 어때요?는 추천일 `LibraryDailySchedule.status=open` 후보만 사용한다.
- `restful_space`는 `facility_lounge` 직접 사실과 편안함·쾌적함·오래 머무름 경험 태그를 함께 사용한다.
- 프로그램 상태는 목록·상세 조회 전 날짜 기준으로 재계산해 현재 필드에 저장한다. `신청마감`은 신청기간 종료다.
- 시설은 선택적 `LibraryFacilityProfile` OneToOne과 nullable boolean으로 저장한다.
- 이미지·시설 미수집은 정상 상태다. fallback과 `NULL`로 처리한다.
- 공개 이미지 응답은 `attribution_text`, `license_code`를 제공한다. 출처 URL 링크는 UI 계약이 아니다.
- ⓘ는 hover·focus·tap 시 전체 출처문구를 이미지 위 오버레이로 표시한다.
- 공휴일은 1~12월 호출이 모두 성공한 연도만 complete다.
- 수집 실행 상태는 `SourceSyncRun`; 도메인 행에는 `draft`, `verified` 같은 검수 상태를 두지 않는다.
- GMS가 없어도 핵심 기능이 모두 동작해야 한다.

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
│  ├─ recommendations/
│  ├─ community/
│  ├─ myoutings/
│  ├─ preferences/
│  └─ integrations/
├─ tests/
└─ scripts/
```

### 3.1 앱 책임

| 앱 | 책임 |
|---|---|
| `common` | 공통 추상 모델, 예외, 응답, 날짜·지역·문자열 유틸리티 |
| `tags` | 공통 태그 어휘, 객관·경험·분류 의미 구분, seed API |
| `accounts` | 커스텀 사용자, 프로필, 선호 목적·지역·태그 |
| `media_assets` | 공식·시스템 이미지, 라이선스·출처문구, fallback 규칙 |
| `libraries` | canonical 도서관, 별칭·외부 코드·운영·공휴일·운영표·통계·시설·태그·이미지 |
| `books` | 책·KDC 태그·소장 관계·인기 스냅샷 |
| `programs` | 문화 프로그램·상태·분류·대상·이미지 |
| `recommendations` | 방문 목적, 홈 5개 테마 규칙, 일일 추천 세트 |
| `community` | 후기, 조회수·좋아요, 후기 이미지·태그·관련 책·프로그램 |
| `myoutings` | 도서관·책·프로그램 저장과 나의 나들이 조회 service |
| `preferences` | 행동 기반 자동 성향 상태·태그 점수·대시보드 계산 service |
| `integrations` | 외부 API client, loader, normalizer, import, `SourceSyncRun` |

`UserReviewLike`는 후기 카운터와 생명주기를 함께 관리해야 하므로 `community`가 소유한다. `myoutings`는 관계를 읽기만 한다.

### 3.2 모델 소유권

```text
tags.Tag
├─ libraries.LibraryTag
├─ books.BookTag
├─ programs.ProgramTag
└─ community.ReviewTag

accounts.User
├─ accounts.UserPreferredPurpose
├─ accounts.UserPreferredRegion
├─ accounts.UserPreferredTag
├─ community.UserReview / UserReviewLike
├─ myoutings.UserLibrarySave / UserBookSave / UserProgramSave
└─ preferences.UserPreference
```

### 3.3 앱 의존 방향

```text
common
├─ tags
├─ media_assets
└─ accounts.0001

libraries → tags, media_assets
books → libraries, tags
programs → libraries, tags, media_assets
recommendations → libraries, tags
accounts.0002 → tags, recommendations
community → accounts, libraries, books, programs, tags
myoutings → accounts, libraries, books, programs
preferences → accounts, tags
integrations → common
```

`preferences` service는 `community`, `myoutings`를 조회하지만 모델 FK를 두지 않는다. 교차 앱 FK는 문자열 참조를 사용한다.

### 3.4 권장 migration 순서

1. `common`(추상 모델만 있으면 migration 없음)
2. `accounts.0001`: `User`, `UserProfile`, `UserPreferredRegion`
3. `tags.0001`, `media_assets.0001`
4. `libraries.0001`
5. `books.0001`, `programs.0001`, `recommendations.0001`
6. `accounts.0002`: `UserPreferredTag`, `UserPreferredPurpose`
7. `community.0001`, `myoutings.0001`, `preferences.0001`, `integrations.0001`

커스텀 User 초기 migration이 `Tag`·`Purpose`에 의존하지 않도록 교차 앱 선호 모델을 후속 migration으로 분리한다.

### 3.5 FK·OneToOne 선언 기준

실제 `models.py`에서는 모든 관계에 명시적 `related_name`을 사용한다. 아래 이름을 권장 표준으로 고정하면 serializer·prefetch·admin 작성 시 역참조 충돌을 줄일 수 있다.

| 소유 모델.필드 | 대상 | `on_delete` | 권장 `related_name` | nullable |
|---|---|---|---|---:|
| `UserProfile.user` | `AUTH_USER_MODEL` | `CASCADE` | `profile` | N |
| `UserPreferredRegion.user` | User | `CASCADE` | `preferred_regions` | N |
| `UserPreferredTag.user` | User | `CASCADE` | `preferred_tags` | N |
| `UserPreferredTag.tag` | `Tag` | `PROTECT` | `preferred_by_users` | N |
| `UserPreferredPurpose.user` | User | `CASCADE` | `preferred_purposes` | N |
| `UserPreferredPurpose.purpose` | `Purpose` | `PROTECT` | `preferred_by_users` | N |
| `DefaultMediaAssetRule.media_asset` | `MediaAsset` | `PROTECT` | `default_rules` | N |
| `LibraryAlias.library` | `Library` | `CASCADE` | `aliases` | N |
| `LibraryExternalIdentifier.library` | Library | `CASCADE` | `external_identifiers` | N |
| `LibraryOpeningHour.library` | Library | `CASCADE` | `opening_hours` | N |
| `LibraryClosureRule.library` | Library | `CASCADE` | `closure_rules` | N |
| `PublicHoliday.calendar` | `PublicHolidayCalendar` | `CASCADE` | `holidays` | N |
| `LibraryDailySchedule.library` | Library | `CASCADE` | `daily_schedules` | N |
| `LibraryStatisticSnapshot.library` | Library | `CASCADE` | `statistic_snapshots` | N |
| `LibraryFacilityProfile.library` | Library | `CASCADE` | `facility_profile` | N |
| `LibraryTag.library` | Library | `CASCADE` | `tag_links` | N |
| `LibraryTag.tag` | Tag | `PROTECT` | `library_links` | N |
| `LibraryImage.library` | Library | `CASCADE` | `images` | N |
| `LibraryImage.media_asset` | MediaAsset | `PROTECT` | `library_usages` | N |
| `BookTag.book` | `Book` | `CASCADE` | `tag_links` | N |
| `BookTag.tag` | Tag | `PROTECT` | `book_links` | N |
| `LibraryHolding.library` | Library | `CASCADE` | `holdings` | N |
| `LibraryHolding.book` | Book | `CASCADE` | `holdings` | N |
| `PopularBookItem.snapshot` | `PopularBookSnapshot` | `CASCADE` | `items` | N |
| `PopularBookItem.book` | Book | `PROTECT` | `popular_items` | N |
| `Program.library` | Library | `PROTECT` | `programs` | N |
| `ProgramTag.program` | Program | `CASCADE` | `tag_links` | N |
| `ProgramTag.tag` | Tag | `PROTECT` | `program_links` | N |
| `ProgramImage.program` | Program | `CASCADE` | `images` | N |
| `ProgramImage.media_asset` | MediaAsset | `PROTECT` | `program_usages` | N |
| `UserReview.user` | User | `CASCADE` | `reviews` | N |
| `UserReview.library` | Library | `PROTECT` | `reviews` | N |
| `UserReviewLike.user` | User | `CASCADE` | `review_likes` | N |
| `UserReviewLike.review` | UserReview | `CASCADE` | `likes` | N |
| `UserReviewImage.review` | UserReview | `CASCADE` | `images` | N |
| `ReviewBookReference.review` | UserReview | `CASCADE` | `book_references` | N |
| `ReviewBookReference.book` | Book | `PROTECT` | `review_references` | N |
| `ReviewProgramReference.review` | UserReview | `CASCADE` | `program_references` | N |
| `ReviewProgramReference.program` | Program | `PROTECT` | `review_references` | N |
| `ReviewTag.review` | UserReview | `CASCADE` | `tag_links` | N |
| `ReviewTag.tag` | Tag | `PROTECT` | `review_links` | N |
| `UserLibrarySave.user` | User | `CASCADE` | `saved_libraries` | N |
| `UserLibrarySave.library` | Library | `CASCADE` | `saved_by_users` | N |
| `UserBookSave.user` | User | `CASCADE` | `saved_books` | N |
| `UserBookSave.book` | Book | `CASCADE` | `saved_by_users` | N |
| `UserProgramSave.user` | User | `CASCADE` | `saved_programs` | N |
| `UserProgramSave.program` | Program | `CASCADE` | `saved_by_users` | N |
| `UserPreference.user` | User | `CASCADE` | `preference` | N |
| `UserPreferenceItem.user_preference` | UserPreference | `CASCADE` | `items` | N |
| `UserPreferenceItem.tag` | Tag | `PROTECT` | `preference_items` | N |
| `PurposeTagRule.purpose` | Purpose | `CASCADE` | `tag_rules` | N |
| `PurposeTagRule.tag` | Tag | `PROTECT` | `purpose_rules` | N |
| `PurposeMetricRule.purpose` | Purpose | `CASCADE` | `metric_rules` | N |
| `DailyRecommendationMetricRule.theme` | `DailyRecommendationTheme` | `CASCADE` | `metric_rules` | N |
| `DailyRecommendationTagRule.theme` | DailyRecommendationTheme | `CASCADE` | `tag_rules` | N |
| `DailyRecommendationTagRule.tag` | Tag | `PROTECT` | `daily_theme_rules` | N |
| `DailyLibraryRecommendationSet.theme` | DailyRecommendationTheme | `PROTECT` | `recommendation_sets` | N |
| `DailyLibraryRecommendationItem.recommendation_set` | DailyLibraryRecommendationSet | `CASCADE` | `items` | N |
| `DailyLibraryRecommendationItem.library` | Library | `PROTECT` | `daily_recommendation_items` | N |

추가 규칙:

- 교차 앱 FK는 `"app_label.ModelName"` 문자열로 선언한다.
- 사용자 FK는 `settings.AUTH_USER_MODEL`을 사용한다.
- canonical 데이터는 물리 삭제보다 `is_active=False` 또는 domain별 soft delete를 우선한다.
- `PROTECT`를 둔 참조 대상은 사용 중인 과거 관계를 보존하기 위한 것이다.
- `related_name="+"`는 역참조가 정말 불필요한 내부 로그 FK에만 제한적으로 사용한다.

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

전역 soft-delete manager는 사용하지 않는다. 필요한 모델만 `is_active`, `is_visible`, `deleted_at`을 명시한다.

### 6.2 tags

```python
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
```

제약:

```python
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
models.Index(fields=["semantic_kind", "tag_group", "is_active", "display_order"])
models.Index(fields=["review_group", "is_review_selectable", "review_display_order"])
```

객관·경험 태그는 별도 코드다.

```text
facility_parking           # 주차장 존재
review_parking_convenient  # 주차 편의 체감
facility_wifi              # 무료 와이파이 제공
review_wifi_reliable       # 와이파이가 잘 된다는 경험
```

### 6.3 accounts

#### User

```python
class User(AbstractUser, TimeStampedModel):
    username = None
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
```

커스텀 manager에서 `create_user`, `create_superuser`를 구현한다.

#### UserProfile

- `user`: OneToOne `CASCADE`
- `profile_image`: `ImageField(null=True, blank=True)`
- `profile_image_alt`: `CharField(max_length=200, blank=True)`
- `bio`: `CharField(max_length=300, blank=True)`

#### UserPreferredRegion

- `user`: FK `CASCADE`
- `region_key`: `CharField(max_length=30)`
- `sido`, `sigungu`
- `weight`: `DecimalField(max_digits=5, decimal_places=4, default=1)`
- `display_order`, `is_active`
- unique `(user, region_key)`

#### UserPreferredTag

- `user`: FK `CASCADE`
- `tag`: FK `tags.Tag`, `PROTECT`
- `weight`, `display_order`, `is_active`
- unique `(user, tag)`
- `tag.is_profile_selectable=True` 검증

#### UserPreferredPurpose

- `user`: FK `CASCADE`
- `purpose`: FK `recommendations.Purpose`, `PROTECT`
- `weight`: `DecimalField(max_digits=5, decimal_places=4, default=1)`
- `display_order`, `is_active`
- unique `(user, purpose)`
- `purpose.is_profile_selectable=True` 검증

### 6.4 media_assets

#### MediaAsset

- `asset_origin`: `official_external|system_default|admin_upload`
- `original_url`, `file` 중 하나 이상 필수
- `source_name`, 내부 추적용 `source_page_url`, `source_asset_id`
- 비어 있지 않은 `original_url` 조건부 unique 권장
- `license_code`, `attribution_text`
- `commercial_use_allowed`, `modification_allowed`: nullable boolean
- `is_active`

활성 공식 외부 asset은 `license_code`와 `attribution_text`를 필수로 한다. 공개 serializer는 `source_page_url`을 요구하지 않는다.

#### DefaultMediaAssetRule

- `target_domain`: `library|program|review|profile`
- `target_code`, `media_asset`, `priority`, `is_active`
- 활성 `(target_domain, target_code, priority)` unique

### 6.5 libraries

#### Library

- canonical `name`, `normalized_name`, `sido`, `sigungu`, `library_type`
- 주소·좌표·전화·홈페이지·운영기관
- 표준데이터 제공기관·기준일·행 해시
- `is_active`
- 지역·유형·이름·좌표 인덱스

#### LibraryAlias

- `library`: FK `CASCADE`
- `alias_name`, `normalized_alias_name`, `sigungu`
- `alias_type`, `provider_code`, `is_active`
- `(library, normalized_alias_name, sigungu, provider_code)` unique. nullable 열까지 중복을 막기 위해 PostgreSQL에서는 `UniqueConstraint(nulls_distinct=False)`를 사용하거나 import 시 빈 문자열 sentinel로 정규화한다.

#### LibraryExternalIdentifier

- `library`: FK `CASCADE`
- `provider_code`, `code_type`, `external_code`
- 원천 이름·주소, 매칭 방식·신뢰도
- unique `(provider_code, code_type, external_code)`

#### LibraryOpeningHour / LibraryClosureRule / PublicHolidayCalendar / PublicHoliday / LibraryDailySchedule

핵심 필드:

```text
LibraryOpeningHour
- library, provider_code
- day_type=day_of_week|public_holiday|specific_date
- day_of_week / specific_date / sequence
- schedule_status=open|closed|unknown
- open_time / close_time / closes_next_day
- valid_from / valid_to
- raw_text / source_field / quality_flags
- source_reference_date / fetched_at / is_current

LibraryClosureRule
- library, provider_code
- rule_type=weekly|nth_weekday|public_holiday|named_holiday|temporary|full_closure|unknown
- normalized_rule / raw_text
- valid_from / valid_to / priority
- source_reference_date / fetched_at / is_current

PublicHolidayCalendar
- year unique
- provider_code
- is_complete / synced_month_count
- last_attempted_at / last_completed_at

PublicHoliday
- calendar, date, source_seq, date_kind, name
- holiday_code / is_public_holiday / fetched_at
- unique (calendar, date, source_seq)

LibraryDailySchedule
- library, date unique
- status=open|closed|unknown
- open_time / close_time / closes_next_day
- reason_code / reason_text
- calculation_basis / has_source_conflict / rule_version / generated_at
```

- `LibraryDailySchedule`는 `(library, date)` unique다.
- `status=open`이어도 원천이 개관일만 확정하고 시간을 제공하지 않으면 `open_time`, `close_time`은 둘 다 null일 수 있다.
- 휴관 규칙과 운영시간이 충돌하면 `unknown`, `has_source_conflict=True`로 보수적으로 판정한다.
- 공휴일 계산은 해당 연도 `PublicHolidayCalendar.is_complete=True`일 때만 신뢰한다.

#### LibraryStatisticSnapshot

- 정적 좌석 수, 장서 3종, 대출정책, 면적
- `source_payload`, `quality_flags`, `is_current`
- unique `(library, provider_code, reference_date)`
- `is_current=True`인 `(library, provider_code)` 조건부 unique 권장

#### LibraryFacilityProfile

```python
class LibraryFacilityProfile(TimeStampedModel):
    library = models.OneToOneField("libraries.Library", on_delete=models.CASCADE, related_name="facility_profile")
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
    source_name = models.CharField(max_length=80, default="facility_json")
    source_reference_date = models.DateField(null=True, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)
```

`True`, `False`, `None`, profile 부재를 구분한다. 긍정 필터는 `True`만 통과한다.

#### LibraryTag

- `library`: FK `CASCADE`
- `tag`: FK `PROTECT`
- `source_method`: `field_rule|facility_rule|program_rollup|review_rollup|book_rollup|manual`
- `source_field`, `score`, `confidence`, `evidence_url`, `is_active`
- unique `(library, tag, source_method)`

동일 `tag_id`의 여러 source는 응답에서 하나로 병합할 수 있다. `facility_parking`과 `review_parking_convenient`는 다른 tag이므로 병합하지 않는다.

#### LibraryImage

- `library`: FK `CASCADE`
- `media_asset`: FK `PROTECT`
- `image_type`, `is_main`, `is_active`, `display_order`, `caption`
- unique `(library, media_asset)`
- `is_active=True AND is_main=True`인 도서관별 대표 이미지 조건부 unique

### 6.6 books

#### Book

- ISBN 문자열, 조건부 unique
- 서지정보, KDC, 설명, 표지 URL, 원천 상세 URL
- provider·마지막 상세 확인 시각

#### BookTag

- `book`: FK `CASCADE`
- `tag`: FK `PROTECT`
- `source_method=kdc_rule|metadata_rule|manual`
- unique `(book, tag, source_method)`

#### LibraryHolding

- `library`: FK `CASCADE`
- `book`: FK `CASCADE`
- unique `(library, book)`

#### PopularBookSnapshot / PopularBookItem

- snapshot은 집계 범위·기간·조건 해시를 저장
- snapshot unique `(provider_code, query_hash, period_start, period_end)`
- item은 snapshot `CASCADE`, book `PROTECT`
- item rank·book unique

### 6.7 programs

#### Program

- `library`: FK `PROTECT`
- 원천 시도·시군구·도서관명 보존
- `provider_code`, `external_program_key` unique 조합
- 분류: `lecture_humanities|reading_writing|culture_art|experience_education|exhibition|other`
- 대상: `infant|elementary|teen|adult|senior|family|other|all`
- 신청 필요 여부·신청 기간·신청 상태
- 운영 기간·운영 상태
- 게시판·원문 URL·게시일·수집일
- soft delete

상태 규칙:

```text
application_required=False              → 신청없음
today < application_start_date          → null
application_start_date <= today <= end  → 신청가능
today > application_end_date            → 신청마감
날짜 부족·역전                           → null

today < operation_start_date            → 예정
operation_start_date <= today <= end    → 진행중
today > operation_end_date              → 종료
날짜 부족·역전                           → null
```

`source_library_name`은 import 추적용이다. 서비스 관계는 `library_id`만 사용한다.

#### ProgramTag / ProgramImage

- `ProgramTag`: program `CASCADE`, tag `PROTECT`, source method, score/confidence, active
- `ProgramTag` unique `(program, tag, source_method)`
- `ProgramImage`: program `CASCADE`, media asset `PROTECT`, `is_main`, `is_active`, display order, caption
- `ProgramImage` unique `(program, media_asset)`
- `is_active=True AND is_main=True`인 프로그램별 대표 이미지 조건부 unique

### 6.8 community

#### UserReview

```python
class ReviewModerationStatus(models.TextChoices):
    PENDING = "pending", "검토 대기"
    VISIBLE = "visible", "공개"
    HIDDEN = "hidden", "숨김"


class UserReview(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    library = models.ForeignKey("libraries.Library", on_delete=models.PROTECT, related_name="reviews")
    content = models.CharField(max_length=200)
    view_count = models.PositiveBigIntegerField(default=0)
    like_count = models.PositiveBigIntegerField(default=0)
    moderation_status = models.CharField(
        max_length=16,
        choices=ReviewModerationStatus.choices,
        default=ReviewModerationStatus.VISIBLE,
        db_index=True,
    )
```

제약·인덱스:

```python
models.CheckConstraint(condition=~Q(content=""), name="review_content_not_empty")
models.Index(fields=["moderation_status", "-created_at"])
models.Index(fields=["moderation_status", "-view_count", "-created_at"])
models.Index(fields=["moderation_status", "-like_count", "-created_at"])
models.Index(fields=["library", "moderation_status", "-created_at"])
models.Index(fields=["user", "-created_at"])
```

`PositiveBigIntegerField`는 0 이상을 표현한다. serializer에서 공백 제거 후 본문 1~200자를 검증한다.

#### UserReviewLike

```python
class UserReviewLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_likes")
    review = models.ForeignKey("community.UserReview", on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "review"], name="uq_user_review_like")
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["review", "-created_at"]),
        ]
```

숨김 후기에는 신규 좋아요를 허용하지 않는다. 자신의 후기 좋아요는 허용할 수 있으나 자동 성향 계산에서는 같은 후기의 작성 신호와 좋아요 신호를 중복 가산하지 않는다.

#### UserReviewImage

- review `CASCADE`, 사용자 업로드 `ImageField`, alt, display order
- 후기당 최대 5장 service validation

#### ReviewBookReference

- review `CASCADE`, book `PROTECT`, display order
- unique `(review, book)`, 최대 5권

#### ReviewProgramReference

- review `CASCADE`, program `PROTECT`, display order
- unique `(review, program)`, 최대 5개
- 원칙적으로 `program.library_id == review.library_id`

#### ReviewTag

- review `CASCADE`, tag `PROTECT`
- unique `(review, tag)`
- `tag.is_review_selectable=True`, `semantic_kind=experience`, `is_active=True`
- 후기당 1~5개

### 6.9 myoutings

세 저장 모델은 구조를 동일하게 유지하되 대상 FK만 다르다. 저장 행이 행동 신호의 원본이므로 soft delete 대신 생성·삭제를 사용한다.

```python
class UserLibrarySave(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_libraries")
    library = models.ForeignKey("libraries.Library", on_delete=models.CASCADE, related_name="saved_by_users")
    memo = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "library"], name="uq_user_library_save")
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]


class UserBookSave(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_books")
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="saved_by_users")
    memo = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "book"], name="uq_user_book_save")
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]


class UserProgramSave(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_programs")
    program = models.ForeignKey("programs.Program", on_delete=models.CASCADE, related_name="saved_by_users")
    memo = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "program"], name="uq_user_program_save")
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]
```

후기 저장 모델은 만들지 않는다. 좋아요한 후기는 `community.UserReviewLike`를 조회한다.

### 6.10 preferences

#### UserPreference

- OneToOne user `CASCADE`
- `status=collecting|pending|ready|failed`
- `signal_count`
- `library_signal_count`, `book_signal_count`, `program_signal_count`
- `written_review_signal_count`, `liked_review_signal_count`
- algorithm version, eligible since, calculated at, failure message

#### UserPreferenceItem

- `user_preference`: FK `CASCADE`
- `tag`: FK `PROTECT`
- `score`: `DecimalField(max_digits=12, decimal_places=6)`, 0 이상
- `count`: `DecimalField(max_digits=12, decimal_places=6)`, 최근성 가중 관측 횟수이므로 정수가 아님
- `rank`: `PositiveIntegerField`
- source counts: library, book, program, written review, liked review. 원천 행 수를 보존한다면 정수형을 사용한다.
- unique `(user_preference, tag)`
- 권장 unique `(user_preference, rank)`

최근성 기본:

```text
recency_weight = 0.5 ** (age_days / 90)
age_days > 365 → 행동 계산에서 제외
```

### 6.11 recommendations

#### Purpose

```python
class AnalysisAxis(models.TextChoices):
    STUDY = "study", "공부형"
    BOOK = "book", "책 탐색형"
    PROGRAM = "program", "프로그램형"
    REST = "rest", "휴식형"


class Purpose(TimeStampedModel):
    code = models.SlugField(max_length=40, unique=True)
    label = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_home_theme = models.BooleanField(default=False, db_index=True)
    is_profile_selectable = models.BooleanField(default=False)
    analysis_axis = models.CharField(max_length=20, choices=AnalysisAxis.choices, blank=True)
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
            models.Index(fields=["is_home_theme", "is_active", "display_order"])
        ]
```

초기 seed:

```text
study   home=Y profile=Y analysis=study requires_location=N
book    home=Y profile=Y analysis=book requires_location=N
kids    home=Y profile=Y analysis="" requires_location=N
mood    home=Y profile=Y analysis=rest requires_location=N
nearby  home=Y profile=Y analysis="" requires_location=Y
program home=N profile=Y analysis=program requires_location=N
```

non-empty `analysis_axis`는 조건부 unique를 권장한다.

#### PurposeTagRule

- purpose `CASCADE`, tag `PROTECT`
- `source_scope=any|direct|review_rollup|program_rollup|book_rollup`
- weight, is_required
- unique `(purpose, tag, source_scope)`

#### PurposeMetricRule

- purpose `CASCADE`
- metric code, weight, is_required, normalization JSON
- unique `(purpose, metric_code)`
- `review_rating` 사용 금지

#### DailyRecommendationTheme / MetricRule / TagRule

- 일일 기준 6종과 subtitle 유지
- `restful_space` direct tag에 `facility_lounge`
- tag rule unique `(theme, tag, source_scope)`

#### DailyLibraryRecommendationSet / Item

- set unique `(recommendation_date, region_key, algorithm_version)`
- set의 theme는 `PROTECT`
- item의 set은 `CASCADE`, library는 `PROTECT`
- item rank·library unique

### 6.12 integrations

#### SourceSyncRun

```text
source_name
target_year / target_month nullable
status=success|failed|partial; 실행 중에는 null 허용
started_at / finished_at
fetched_count / imported_count / skipped_count
error_message nullable
```

`SourceSyncRun`은 수집·적재 실행 결과만 기록한다. 도메인 행의 검수 상태나 신뢰도 필드가 아니며, 상세 미매칭·파싱 실패는 별도 report와 구조화 로그에 둔다.

## 7. 태그 파이프라인 명세

### 7.1 기본 원칙

```text
원천 필드·분류·후기 선택
→ 도메인별 *Tag 관계
→ LibraryTag rollup
→ UserPreferenceItem
```

- 원천값과 사용자 성향 점수를 같은 테이블에 저장하지 않는다.
- 객관 시설·운영·통계와 후기 체감은 별도 `Tag.code`다.
- 같은 `tag_id`의 여러 근거만 병합한다.
- 미선택 후기 태그는 음수 신호가 아니다.

### 7.2 직접 객관 태그

| 원천 | 태그 |
|---|---|
| 도서관 유형 | `public_library`, `small_library`, `children_library` |
| 좌석·장서 구간 | `many_seats`, `rich_collection` |
| 늦은 운영 | `late_open` |
| 시설 True | `facility_reading_room`, `facility_children_room`, `facility_digital_room`, `facility_parking`, `facility_cafe`, `facility_wifi`, `facility_nursing_room`, `facility_accessible`, `facility_elevator`, `facility_lounge`, `facility_outdoor_space` |
| KDC | `book_literature`, `book_science` 등 |
| 프로그램 분류·대상 | `program_*`, `for_*` |

시설 하나만으로 `review_children_friendly`나 `review_parking_convenient`를 생성하지 않는다.

### 7.3 후기 선택 경험 태그

후기 선택지는 ERD v3의 확정 목록을 seed한다. 모든 항목은 `semantic_kind=experience`, `is_review_selectable=True`다.

대표 구분:

```text
facility_parking              ≠ review_parking_convenient
facility_wifi                 ≠ review_wifi_reliable
facility_children_room        ≠ review_children_room_good
facility_outdoor_space        ≠ review_outdoor_space_good
many_seats                    ≠ review_seats_sufficient
rich_collection               ≠ review_books_diverse
```

### 7.4 도메인 서비스

```text
libraries.services.tags.rebuild_library_direct_tags(library_id)
libraries.services.tags.rebuild_library_program_rollup(library_id)
libraries.services.tags.rebuild_library_review_rollup(library_id)
books.services.tags.rebuild_book_tags(book_id)
programs.services.tags.rebuild_program_tags(program_id)
community.services.tags.replace_review_tags(review_id, tag_ids)
```

모든 rebuild는 idempotent해야 한다.

### 7.5 도서관 rollup

- visible 후기만 포함
- 사용자별 반복 기여 상한
- 최소 후기 수·고유 작성자 수
- 시간 감쇠
- `review_rollup`은 경험 태그만 생성
- 객관 시설 필터는 profile `True` 또는 direct 객관 태그만 사용

### 7.6 행동 성향 입력

| 행동 | 태그 원천 |
|---|---|
| 도서관 저장 | `LibraryTag` |
| 책 저장 | `BookTag` |
| 프로그램 저장 | `ProgramTag` |
| 후기 좋아요 | `ReviewTag` + 관련 책·프로그램 태그 + 대상 도서관 태그 |
| 후기 작성 | 선택 `ReviewTag` + 관련 책·프로그램 태그 + 대상 도서관 태그 |

동일 상호작용에서 같은 `tag_id`가 여러 경로로 도달하면 deduplicate한다.

## 8. 이미지·대체 이미지 처리

### 8.1 해석 객체

```python
@dataclass(frozen=True)
class ResolvedImage:
    url: str | None
    is_fallback: bool
    fallback_key: str | None
    attribution_text: str | None
    license_code: str | None
```

공개 응답에 `source_page_url`은 포함하지 않아도 된다.

### 8.2 해석 순서

```text
도서관: 대표 LibraryImage → library/{type} → library/default → null
프로그램: 대표 ProgramImage → program/{category} → program/default → null
후기: 첫 UserReviewImage → review/default → null
프로필: profile_image → profile/default → null
```

### 8.3 응답 예시

```json
{
  "url": "https://...",
  "is_fallback": false,
  "fallback_key": null,
  "attribution_text": "한국관광공사 ... 공공누리 제3유형",
  "license_code": "공공누리 제3유형"
}
```

### 8.4 UI·접근성 계약

- ⓘ는 외부 링크가 아니다.
- mouse hover, keyboard focus, mobile tap 시 전체 `attribution_text`를 이미지 위 오버레이로 표시한다.
- 키보드 사용자를 위해 focus 가능 요소와 `aria-describedby`를 제공한다.
- 출처문구를 임의로 축약해 법정 표시를 훼손하지 않는다.
- fallback 내부 이미지는 필요한 경우 `license_code=internal`, attribution null로 반환한다.

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

- `sido`, `sigungu`, `library_name` → source 원문 필드 + `Library` 매칭
- `program_type` → `category_code`
- `target` → `target_text`, `target_codes`
- 신청·운영 날짜 문자열 → `date`
- `application_required` → nullable boolean
- `application_status` → `Program.application_status` 초기값
- `operation_status` → `Program.operation_status` 초기값
- 외부 ID가 없으면 안정적 해시 생성

프로그램 upsert 뒤 현재 날짜 기준 상태를 한 번 계산하고, `ProgramTag`와 개최 도서관의 program rollup을 재계산한다. 이후 목록·상세 조회에서도 상태를 다시 확인해 필요한 행만 갱신한다.

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
12. 연간 또는 월별 실행 결과를 `SourceSyncRun`에 기록한다. 한 월 실패 시 연간 실행은 `partial` 또는 `failed`로 종료하고 대표 오류와 처리 건수를 남긴다.

임시공휴일·대체공휴일이 공식 API에 반영된 뒤 같은 연도를 수동 재수집할 수 있도록 management command를 제공한다.

### 9.5 파일 import 공통

```text
SourceSyncRun 시작 행 생성
→ 파일 checksum 계산
→ 형식·헤더/schema validation
→ 부산 범위 검증
→ 문자열·숫자·URL 정규화
→ Library/LibraryAlias 매칭
→ domain upsert
→ reject·warning·merge report 파일
→ 구조화 로그·통계 출력
→ SourceSyncRun status·건수·종료 시각 갱신
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
- 라이선스 공란 또는 공개 사용 조건이 불명확한 asset은 `is_active=False`; 공개 응답은 fallback을 사용한다.
- 동일 URL이 서로 다른 도서관에 반복되면 asset 공유는 가능하지만 warning report에 기록한다.
- HTTP URL은 mixed-content와 링크 유효성을 검사한다. 검증 실패 시 fallback을 사용한다.
- 이미지 행만으로 새 도서관을 생성하지 않는다.

### 9.7 시설 파일 정규화·import

정식 입력은 JSON 배열 또는 JSONL이다. 현재 작업 파일처럼 JSON 객체가 구분자 없이 연속된 파일은 직접 import하지 않는다.

```bash
python manage.py normalize_library_facilities   --input path/to/working.json   --output path/to/facilities.normalized.json   --report path/to/facilities.normalize-report.json

python manage.py import_library_facilities   --file path/to/facilities.normalized.json
```

- field set은 11개 `has_*` nullable boolean으로 고정한다.
- 값은 `true|false|null`만 허용한다.
- exact `(library_name, sigungu)` 또는 검수된 alias만 자동 매칭한다.
- 이름만 같고 구·군이 다르거나 null이면 correction map 없이는 reject한다.
- 동일 이름이 여러 행에 나타나면 자동 overwrite하지 않고 duplicate report를 만든다.
- `true|false|null`은 각각 `True|False|None`으로 직접 저장하며, 행 부재는 profile 부재로 표현한다.
- 파일 완성도와 미매칭은 `SourceSyncRun`의 처리 건수와 normalize/import report에서 관리하고 profile에 상태 필드를 두지 않는다.
- 데이터셋 설명 문서의 `has_cafe` 비고가 `건물`로 적힌 부분은 필드명과 모순된다. 실제 수집 근거가 확인되기 전에는 원문 boolean만 보존하고 카페 존재 의미로 임의 확대하지 않는다.

### 9.8 필수 데이터셋 계약

| 데이터셋 | 실제 형식·키 | 영속 모델 | 커버리지·결측 처리 |
|---|---|---|---|
| 부산 전국도서관 표준 데이터 | JSON object의 `fields`, `records`; 28개 필드 | `Library`, `LibraryAlias`, 운영시간, 휴관 규칙, 통계 | 부산 기준 모체; 별칭·중복 override, 필드별 0 처리, 운영 충돌 unknown |
| 프로그램 강좌 | 문서상 JSON, `library_name`, `sigungu`; 실제 파일 현재 미첨부 | `Program`, `ProgramTag` | actual contract 미검증; 빈 목록 허용 |
| 도서관 외관 사진 | CSV 한국어 7개 헤더 | `MediaAsset`, `LibraryImage` | row scaffold와 asset coverage 구분; 사용 조건 불명확 asset은 비활성, fallback |
| 도서관 시설 | 정규화 후 JSON array/JSONL | `LibraryFacilityProfile` | 부분 커버리지; null=unknown, 명시적 True만 긍정 필터, 미매칭은 report |
| 한국천문연구원 공휴일 API | 월별 `getRestDeInfo`, `DATA_GO_KR_API_KEY` | `PublicHolidayCalendar`, `PublicHoliday` | 연도별 12개월 완전 수집; singleton/list/empty 정규화 |
| 정보나루 | `libSrch`, 책·소장·인기·reader 추천 API | 외부 식별자, `Book`, `LibraryHolding`, 인기 snapshot; 추천 cache | libCode 선연결, 미참여 도서관 정상, 미조회와 부재 구분 |
| 수집 실행 로그 | 파일 import/API sync 공통 | `SourceSyncRun` | 실행 단위 성공·실패·부분 성공과 처리 건수; 상세 reject는 report |

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
- 시설 boolean type·중복·지역 불일치·미매칭 처리 건수
- 프로그램 파일이 없을 때 명시적 `not_checked`

---

## 10. REST API 명세

모든 URL의 기본 prefix는 `/api/v1`이다. 날짜 판정은 `Asia/Seoul` 기준이며, 목록 응답은 기본 20개 페이지네이션을 사용한다. `GET` 요청은 DB를 변경하지 않는 것이 원칙이지만, 프로그램 상태 보정과 후기 상세 조회수 증가는 아래에 명시한 예외 서비스에서 원자적으로 수행한다.

### 10.1 공통 응답과 오류

목록 응답:

```json
{
  "count": 120,
  "next": "...",
  "previous": null,
  "results": []
}
```

오류 응답:

```json
{
  "code": "invalid_parameter",
  "detail": "요청값이 올바르지 않습니다.",
  "fields": {
    "purpose": ["공개 테마만 사용할 수 있습니다."]
  }
}
```

공통 규칙:

- 인증하지 않은 사용자의 개인화·저장·좋아요 필드는 `null` 또는 미포함으로 응답한다.
- 클라이언트가 날짜를 보내지 않는 당일 판정은 서버의 한국 표준시를 사용한다.
- 외부 원천의 `library_name`은 공개 관계 키로 사용하지 않는다. API의 관계 식별자는 내부 `Library.id`다.
- 다중 선택 쿼리는 쉼표 구분 또는 반복 파라미터 중 한 방식을 프로젝트 전체에서 통일한다. 이 명세는 쉼표 구분을 예시로 사용한다.
- `unknown`은 `false`와 다르며, 응답과 필터에서 임의로 합치지 않는다.

### 10.2 인증·계정·프로필

| Method | URL | 설명 |
|---|---|---|
| POST | `/auth/signup/` | 이메일·닉네임·비밀번호 회원가입 |
| POST | `/auth/login/` | 토큰 또는 세션 로그인 |
| POST | `/auth/logout/` | 로그아웃 |
| GET | `/profile/` | 프로필 화면 데이터 |
| PATCH | `/profile/` | 닉네임·프로필 이미지·소개 수정 |
| GET | `/profile/preferences/` | 선호 설정 조회 |
| PUT | `/profile/preferences/` | 선호 목적·지역·태그 전체 교체 |

회원가입 transaction에서 `UserProfile`, `UserPreference`를 함께 생성한다. 선호 설정은 다음 세 배열을 원자적으로 교체한다.

```json
{
  "purpose_ids": [1, 6],
  "regions": [
    {"region_key": "21:21090", "weight": 1.0, "display_order": 1}
  ],
  "tag_ids": [31, 44, 52]
}
```

검증:

- `purpose_ids`: `Purpose.is_profile_selectable=True`, `is_active=True`
- `tag_ids`: `Tag.is_profile_selectable=True`, `is_active=True`
- `region_key`: 서비스의 부산 구·군 기준정보에 존재
- 중복 ID·지역은 `400`
- 저장 성공 후 `transaction.on_commit()`에서 개인화 캐시를 무효화한다.

### 10.3 기준정보

| Method | URL | 설명 |
|---|---|---|
| GET | `/purposes/?context=home` | 홈 공개 테마 5개 |
| GET | `/purposes/?context=profile` | 프로필에서 선택 가능한 목적 |
| GET | `/tags/?context=profile` | 프로필 선택 태그 |
| GET | `/tags/?context=review` | 후기 7개 그룹의 선택 태그 |
| GET | `/regions/` | 부산광역시 구·군 기준정보 |

`context=home` 결과는 `study`, `book`, `kids`, `mood`, `nearby`만 반환한다. `program`은 홈 테마가 아니지만 `context=profile`에는 포함될 수 있다.

후기 태그 응답은 그룹과 문장형 label을 포함한다.

```json
{
  "group_code": "access_convenience",
  "group_label": "접근·편의",
  "items": [
    {
      "id": 81,
      "code": "review_parking_convenient",
      "label": "주차 편의",
      "review_label": "주차가 편해요"
    }
  ]
}
```

### 10.4 홈

#### GET `/home/recommendations/`

선택 쿼리 `lat`, `lng`를 받을 수 있다. 현재 위치가 전달된 경우에만 `nearby` 직접 선호를 개인화 점수에 적용한다. 위치가 없어도 다른 선호·행동 신호로 개인화는 계산한다.

화면 순서와 동일하게 다음 세 section을 반환한다.

```json
{
  "today": {
    "title": "오늘의 추천 도서관",
    "subtitle": "오늘은 조금 넓은 도서관으로 가볼까요?",
    "theme_code": "large_space",
    "items": []
  },
  "personalized": {
    "title": "여기는 어때요?",
    "is_available": true,
    "items": []
  },
  "themes": [
    {
      "code": "study",
      "label": "공부하기 좋은 곳",
      "requires_location": false
    },
    {
      "code": "nearby",
      "label": "가까운 곳",
      "requires_location": true
    }
  ]
}
```

정책:

- `today.items`: 모든 사용자에게 같은 최대 3개. 추천일 `LibraryDailySchedule.status=open`만 허용한다.
- `personalized.items`: 로그인하고 수동 선호 또는 행동 신호가 있을 때만 최대 3개. `today.items`와 중복을 제거하고 당일 `open`만 허용한다.
- 개인화 데이터가 없으면 `is_available=false`, `items=[]`로 반환한다. 프론트는 section을 숨긴다.
- 개인화 결과가 3개 미만이어도 휴관·미확인 도서관으로 채우지 않는다.
- 홈 공개 테마는 5개이며 `program`을 반환하지 않는다.

#### GET `/home/theme-recommendations/`

쿼리:

```text
purpose=study|book|kids|mood|nearby
lat=35.1796        # nearby에 필수
lng=129.0756       # nearby에 필수
limit=6            # 최대 6
```

- `Purpose.is_home_theme=True`만 허용한다.
- `nearby`는 `lat`, `lng`가 없으면 `400 location_required`를 반환한다.
- 이 section은 목적별 탐색이므로 기본적으로 당일 휴관 도서관을 강제 제외하지 않는다. 각 카드에 `open_today`를 표시한다.
- 동일한 목적 점수 계산기를 `/libraries/?purpose=`에서도 사용한다.
- 더보기 링크는 해당 쿼리를 그대로 도서관 찾기 페이지에 전달한다.

### 10.5 도서관 찾기

#### GET `/libraries/`

지원 쿼리:

```text
q=
sigungu=해운대구,수영구
library_type=public,small,children
purpose=study|book|kids|mood|nearby
facility=parking,wifi,lounge
open_today=true
open_now=true
weekend_open=true
holiday_status=open|closed|unknown
holiday_date=2026-10-03
late_open_after=18:00
min_book_count=10000
max_book_count=
min_reading_seat_count=100
max_reading_seat_count=
lat=
lng=
radius_km=
ordering=name|-book_count|-reading_seat_count|distance|purpose_score
page=
page_size=
```

필터 의미:

- `q`: 도서관명, 정규화 별칭, 구·군, 도로명주소, 운영기관, `Tag.is_filterable=True`인 태그명·코드
- `purpose`: 공개 홈 테마 5개만 허용. `PurposeTagRule`·`PurposeMetricRule`로 점수를 계산하고 `purpose_score`를 annotate한다.
- `purpose=nearby`: `lat`, `lng` 필수. 거리 오름차순이 기본이다.
- `facility`: 허용 코드는 `reading_room`, `children_room`, `digital_room`, `parking`, `cafe`, `wifi`, `nursing_room`, `accessible_facility`, `elevator`, `lounge`, `outdoor_space`다. `LibraryFacilityProfile`의 대응 필드가 명시적으로 `True`이거나 동일 의미의 객관 `LibraryTag`가 `field_rule|facility_rule|manual` 근거로 활성화된 도서관만 통과한다. `review_rollup` 경험 태그는 시설 보유 조건에 사용하지 않는다. 수동 보정은 가능하면 프로필과 직접 태그를 함께 갱신한다. `False`, `NULL`, profile 부재만으로는 긍정 조건을 충족하지 않는다.
- `open_today=true`: 오늘의 `LibraryDailySchedule.status=open`. 정확한 시간이 없어도 하루 개관이 확정되면 통과한다.
- `open_now=true`: 오늘 status가 `open`이고 현재 시각이 알려진 `open_time`~`close_time` 구간 안인 경우만 통과한다. 시간 미확인은 통과하지 않는다.
- `weekend_open=true`: 한국 날짜 기준으로 가장 가까운 토요일·일요일 중 적어도 하나의 일일 운영표가 `open`이면 통과한다. `unknown`만 존재하면 통과하지 않는다.
- `holiday_status`: `holiday_date`가 있으면 그 날짜를, 없으면 완전한 공휴일 달력에서 오늘 이후 가장 가까운 공휴일을 사용한다. 해당 날짜 운영표의 `open|closed|unknown`과 정확히 일치시키며, `unknown`을 `closed`로 취급하지 않는다.
- `late_open_after`: 현재 유효한 일반 운영 구간 중 하나라도 지정 시각보다 늦게 종료되면 통과한다. 화면 기본값은 `18:00`이다.
- 장서·좌석 조건은 `LibraryStatisticSnapshot.is_current=True`의 최신값을 사용한다. 값이 `NULL`이면 최소·최대 조건을 충족하지 않는다.
- 거리 필터·정렬을 요청한 경우에만 Haversine 또는 PostGIS distance를 계산한다. 사용자 위치는 영구 저장하지 않는다.

도서관 카드 응답 예시:

```json
{
  "id": 101,
  "name": "반여도서관",
  "library_type": "public",
  "sigungu": "해운대구",
  "thumbnail": {
    "url": "...",
    "is_fallback": false,
    "license_code": "공공누리 제3유형",
    "attribution_text": "한국관광공사 ..."
  },
  "open_today": true,
  "open_now": false,
  "today_hours": {"open": "09:00", "close": "22:00"},
  "book_count": 61405,
  "reading_seat_count": 134,
  "distance_m": null,
  "purpose_score": null,
  "main_tags": [
    {"code": "facility_children_room", "label": "어린이자료실", "semantic_kind": "objective"},
    {"code": "review_quiet_study", "label": "조용한 공부 환경", "semantic_kind": "experience"}
  ],
  "is_saved": false
}
```

#### GET `/libraries/{library_id}/`

응답 묶음:

1. 상단 요약: 대표 이미지, 이름, 유형, 지역, 오늘 운영, 주요 태그, 저장 여부
2. 기본 정보: 주소, 전화, 홈페이지, 운영기관
3. 운영 정보: 평일·토요일·공휴일 운영시간, 휴관 원문, 오늘 운영표
4. 최신 통계: 장서 3종, 열람좌석, 부지·건물면적, 대출정책
5. 시설: 값이 `True`인 시설 칩. `False`와 `NULL`은 “확인된 시설” 칩에 표시하지 않는다.
6. 위치: 좌표
7. 관련 프로그램 preview
8. 관련 후기 preview
9. 비슷한 도서관 최대 3개

태그 응답은 같은 `tag_id`의 여러 근거를 하나로 합칠 수 있지만, 서로 다른 의미의 태그는 함께 반환한다.

```json
{
  "tags": [
    {"code": "facility_parking", "label": "주차장", "semantic_kind": "objective"},
    {"code": "review_parking_convenient", "label": "주차 편의", "semantic_kind": "experience"}
  ]
}
```

이미지 응답은 `source_page_url`을 공개하지 않아도 된다. `attribution_text`와 `license_code`를 제공하고, 프론트는 ⓘ hover·focus·tap 오버레이로 전체 문구를 표시한다.

#### 관련 endpoint

| Method | URL | 설명 |
|---|---|---|
| GET | `/libraries/{id}/programs/` | 해당 도서관의 프로그램 목록. `/programs/?library_id=`와 같은 결과 계약 |
| GET | `/libraries/{id}/reviews/` | 해당 도서관 공개 후기. `/reviews/?library_id=`와 같은 결과 계약 |
| GET | `/libraries/{id}/similar/?limit=3` | 비슷한 도서관 비영속 계산 |
| PUT | `/my-outings/libraries/{id}/` | 도서관 저장·메모 upsert |
| DELETE | `/my-outings/libraries/{id}/` | 도서관 저장 해제 |

### 10.6 책 둘러보기

#### GET `/popular-books/`

- 가장 최근 성공한 부산 주간 `PopularBookSnapshot`을 반환한다.
- 응답에 `start_date`, `end_date`, `region_code`, `generated_at`, `is_stale`을 포함한다.
- 외부 API 장애 시 최근 성공 스냅샷을 stale로 반환할 수 있다.

#### GET `/books/search/`

```text
search_type=title|author|isbn|keyword|publisher
q=
page=
page_size=
sort=loan|title|author|pub|pubYear|isbn
order=asc|desc
```

Django가 정보나루를 호출하고 정규화한 결과를 반환한다. 키는 브라우저에 노출하지 않는다. 조회 결과는 `Book`에 idempotent upsert할 수 있다.

#### GET `/books/{isbn13}/`

책 표지, 도서명, 저자, 출판사, 출판연도, KDC, `BookTag`, 책 소개를 반환한다. 로컬 상세가 오래되었으면 정보나루 `srchDtlList`를 재조회하고 갱신한다.

#### GET `/books/{isbn13}/libraries/`

정보나루 `libSrchByBook(region=21)` 결과를 canonical `Library.id`로 매칭해 부산 소장 도서관을 반환한다. 외부 `libCode` 선연결을 우선하고, 낮은 신뢰도 항목으로 `Library`를 자동 생성하지 않는다.

#### 저장 endpoint

| Method | URL | 설명 |
|---|---|---|
| PUT | `/my-outings/books/{book_id}/` | 책 저장·메모 upsert |
| DELETE | `/my-outings/books/{book_id}/` | 책 저장 해제 |

### 10.7 문화 프로그램

#### GET `/programs/`

```text
q=
library_id=
sigungu=
category=lecture_humanities,reading_writing,culture_art,experience_education,exhibition,other
target=infant,elementary,teen,adult,senior,family,other,all
application_status=신청가능,신청마감,신청없음
operation_status=예정,진행중,종료
ordering=operation_start_date|-operation_start_date|title
page=
```

- `q`: 프로그램명과 canonical 도서관명
- `library_id`: 정확한 도서관 필터
- 조회 전에 날짜 기준 bulk 상태 보정을 실행한다.
- `application_status=신청마감`은 신청기간 종료를 의미한다.
- 원천 도서관 문자열이 아니라 `Program.library_id`로 필터한다.

카드 응답:

```json
{
  "id": 501,
  "title": "책 소풍 가는 날",
  "library": {"id": 101, "name": "부산진구어린이청소년도서관"},
  "category_code": "reading_writing",
  "target_codes": ["adult"],
  "application_required": true,
  "application_start_date": "2026-06-01",
  "application_end_date": "2026-06-09",
  "application_status": "신청마감",
  "operation_start_date": "2026-06-10",
  "operation_end_date": "2026-06-24",
  "operation_status": "진행중",
  "source_url": "https://...",
  "image": {"url": "...", "is_fallback": true},
  "is_saved": false
}
```

#### GET `/programs/{program_id}/`

카드 필드와 원천 게시판·수집일·전체 태그·개최 도서관 링크를 반환한다. 프로그램 자체 신청 endpoint는 제공하지 않는다.

#### 저장 endpoint

| Method | URL | 설명 |
|---|---|---|
| PUT | `/my-outings/programs/{id}/` | 프로그램 저장·메모 upsert |
| DELETE | `/my-outings/programs/{id}/` | 프로그램 저장 해제 |

### 10.8 커뮤니티

#### GET `/reviews/`

```text
q=
library_id=
tag=review_quiet_study,review_parking_convenient
ordering=-created_at|-view_count|-like_count
page=
```

- 공개 조건은 `moderation_status=visible`이다.
- `q`는 후기 본문과 도서관명을 검색한다. 최종 모델에는 별도 제목이 없다.
- `tag`는 `ReviewTag`의 경험 태그 코드다.
- 기본 정렬은 `-created_at`이다.
- 카드에는 작성자 닉네임·프로필 이미지, 도서관, 본문, 태그, 관련 책·프로그램 미니 카드, 이미지, 조회수, 좋아요 수, 로그인 사용자의 좋아요 여부를 포함한다.

미니 카드 예시:

```json
{
  "related_books": [
    {"id": 3, "isbn13": "978...", "title": "...", "cover_image_url": "..."}
  ],
  "related_programs": [
    {"id": 8, "title": "...", "library_id": 101, "library_name": "..."}
  ]
}
```

#### POST `/reviews/`

multipart 또는 JSON + 별도 이미지 업로드 정책 중 하나를 선택해 일관되게 구현한다.

```json
{
  "library_id": 101,
  "content": "휴게공간이 편안하고 아이와 머물기 좋았어요.",
  "tag_ids": [81, 93],
  "book_ids": [3],
  "program_ids": [8]
}
```

검증:

- 로그인 필수
- 본문 trim 후 1~200자
- 경험 태그 1~5개
- 관련 책 최대 5권, 프로그램 최대 5개
- 관련 프로그램은 원칙적으로 후기 도서관과 같은 `library_id`
- `rating`, `title`, `purpose_id` 입력은 허용하지 않는다.
- 전체 생성은 하나의 transaction으로 처리한다.
- 성공 후 작성자 성향 재계산과 해당 도서관 `review_rollup` 갱신을 예약한다.

#### GET `/reviews/{review_id}/`

공개 후기 상세 조회 시 `view_count = F("view_count") + 1`로 원자 증가시킨다. 목록·프리뷰·봇 health check에서는 증가시키지 않는다. 응답은 갱신된 값을 다시 읽어 반환한다.

#### PATCH `/reviews/{review_id}/`

작성자만 수정할 수 있다.

- `content`: 전달 시 1~200자
- `tag_ids`: 전달하면 1~5개 전체 교체, 생략하면 유지
- `book_ids`, `program_ids`: 전달하면 전체 교체
- 관계 교체와 본문 수정은 transaction으로 묶는다.

#### DELETE `/reviews/{review_id}/`

작성자 또는 관리자만 가능하다. 물리 삭제를 사용하면 좋아요·이미지·관련 관계가 `CASCADE`된다. 운영상 보존이 필요하면 `moderation_status=hidden`으로 전환하는 별도 관리자 action을 사용한다.

#### PUT `/reviews/{review_id}/like/`

idempotent 좋아요 생성. 공개 후기만 허용한다. 관계 생성과 `like_count` 증가는 같은 transaction에서 처리한다.

#### DELETE `/reviews/{review_id}/like/`

idempotent 좋아요 삭제. 관계가 있을 때만 `like_count`를 1 감소시키며 0 미만이 되지 않도록 한다.

후기 저장 endpoint와 `UserReviewSave` 모델은 만들지 않는다.

### 10.9 나의 나들이

로그인 필수다.

#### GET `/my-outings/dashboard/`

```json
{
  "profile": {
    "nickname": "김나들이",
    "profile_image": {"url": "...", "is_fallback": true}
  },
  "greeting": "김나들이님, 반가워요!",
  "preference_summary": "조용한 학습공간과 장서가 풍부한 도서관을 자주 찾고 있어요.",
  "analysis_basis": "최근 저장, 작성 후기, 좋아요한 후기의 태그를 바탕으로 분석했어요.",
  "purpose_distribution": {
    "study": 42.0,
    "book": 31.0,
    "program": 17.0,
    "rest": 10.0
  },
  "top_tags": [],
  "interests": {
    "book_subjects": [],
    "program_categories": [],
    "frequent_regions": []
  },
  "counts": {
    "saved_libraries": 5,
    "saved_books": 7,
    "saved_programs": 2,
    "liked_reviews": 3,
    "written_reviews": 4
  },
  "preference_status": {
    "status": "ready",
    "signal_count": 21,
    "calculated_at": "2026-06-23T07:00:00+09:00"
  }
}
```

계산 기준:

- 자동 성향 신호: 저장한 도서관·책·프로그램, 공개 가능한 작성 후기, 공개 후기 좋아요
- 최근성: 90일 반감기, 최대 365일 관측창
- 같은 사용자가 자신이 작성한 후기를 좋아요한 경우 같은 후기 태그를 두 번 가산하지 않는다.
- 수동 선호 목적·지역·태그는 행동 기반 `purpose_distribution`에 합쳐 저장하지 않는다. 별도 설정으로 표시하고 개인화 점수에 보너스로 사용한다.
- 목적 비율은 `UserPreferenceItem`과 `Purpose.analysis_axis`가 설정된 목적 규칙을 이용해 `study|book|program|rest` 네 축으로 정규화한다.
- `book_subjects`: 저장 책의 `BookTag`
- `program_categories`: 저장 프로그램의 category·`ProgramTag`
- `frequent_regions`: 저장 도서관의 `sigungu`
- 대표 문장은 상위 축과 태그를 이용한 결정론적 template이 기본이다. GMS 사용 시에도 사실·순위를 생성하지 않고 문장 표현만 보조하며 실패 시 template으로 즉시 fallback한다.

#### 목록 endpoint

| Method | URL | 설명 |
|---|---|---|
| GET | `/my-outings/libraries/` | 저장한 도서관 |
| GET | `/my-outings/books/` | 저장한 책 |
| GET | `/my-outings/programs/` | 저장한 프로그램 |
| GET | `/my-outings/liked-reviews/` | `UserReviewLike` 기준 좋아요한 공개 후기 |
| GET | `/my-outings/reviews/` | 내가 쓴 후기. 본인에게는 hidden 포함 여부를 권한 정책으로 명시 |

성향 재계산 이벤트는 `transaction.on_commit()` 뒤 예약한다.

- 저장 생성·삭제 → 해당 사용자
- 후기 좋아요 생성·삭제 → 좋아요한 사용자
- 후기 작성·삭제·태그·관련 책·프로그램 변경 → 작성자
- 후기 숨김 또는 태그 변경 → 작성자와 현재 좋아요한 사용자 전체
- 도서관·책·프로그램의 태그 rollup 변경 → 영향을 받은 저장·후기 관계 사용자를 배치 재계산

동일 사용자의 반복 이벤트는 debounce한다.

---

## 11. 서비스·도메인 로직

### 11.1 외부 도서관명과 내부 FK 경계

모든 import는 다음 순서를 사용한다.

```text
1. 원천 이름·시군구 정규화 exact
2. LibraryAlias + 시군구
3. 주소·전화·좌표 등 보조 필드
4. 검수된 correction map
5. 단일 후보가 아니면 자동 연결 중단
```

성공 후에는 `library_id`만 관계에 저장한다. 원천 이름은 `Program.source_library_name`, `LibraryAlias`, import report 등 추적 위치에만 보존한다.

금지:

```python
LibraryTag.objects.filter(library__name=source_library_name)
Program.objects.create(library_id=None, source_library_name=...)
```

허용:

```python
library = matcher.resolve(source_name, sigungu, address)
Program.objects.update_or_create(library=library, ...)
```

### 11.2 태그 파이프라인

```text
시설·통계·운영 필드 ──> 객관 Tag ──> LibraryTag(direct)
프로그램 분류·대상   ──> ProgramTag ──> LibraryTag(program_rollup)
후기 선택 경험       ──> ReviewTag  ──> LibraryTag(review_rollup)
저장·후기·좋아요     ──> UserPreferenceItem
```

- 시설 태그는 대응 boolean이 `True`일 때만 생성한다.
- 시설 `False`는 “부재 확인”이며 긍정 태그를 생성하지 않는다.
- `NULL`·profile 부재는 미확인이고 긍정 태그를 생성하지 않는다.
- 후기 rollup은 `moderation_status=visible`인 후기만 사용한다.
- 같은 `tag_id`의 여러 source 행은 표시·유사도 입력에서 tag별로 합산 또는 최댓값 처리한다.
- 의미가 다른 태그는 병합하지 않는다. `facility_parking`과 `review_parking_convenient`는 둘 다 표시·유사도에 기여할 수 있다.
- 후기 경험 태그가 공식 시설 boolean을 갱신하는 일은 없다.

### 11.3 공개 목적 점수

공통 service 예시:

```python
def score_libraries_for_purpose(
    queryset: QuerySet[Library],
    *,
    purpose: Purpose,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
) -> QuerySet[Library]:
    ...
```

점수 요소:

```text
sum(normalized metric * PurposeMetricRule.weight)
+ sum(tag contribution * PurposeTagRule.weight)
```

- `is_required=True`인 규칙을 충족하지 못한 후보는 제외한다.
- `source_scope=direct`는 객관·직접 `LibraryTag`만 본다.
- `source_scope=review_rollup`은 후기 집계만 본다.
- `nearby`는 저장 태그가 아니라 요청 좌표와 `distance_m` 역거리 점수로 계산한다.
- 홈 preview와 `/libraries/?purpose=`가 같은 service를 사용한다.
- 정규화 범위·결측 처리·가중치는 `normalization_rule`과 알고리즘 버전으로 기록한다.

초기 seed 방향:

| purpose | metric | direct tag | experience·rollup tag |
|---|---|---|---|
| `study` | `reading_seat_count`, `late_close_minutes` | `facility_reading_room`, `many_seats` | `review_quiet_study`, `review_focused_atmosphere`, `review_seats_sufficient`, `review_comfortable_reading_space` |
| `book` | `book_count` | `rich_collection` | `review_books_diverse`, `review_easy_book_finding`, `review_frequent_new_books` |
| `kids` | 선택적 어린이 시설 지표 | `facility_children_room`, 어린이도서관 유형 태그 | `review_children_friendly`, `review_children_room_good`, `review_family_friendly`, `review_good_children_books`, `review_good_children_programs` |
| `mood` | 선택적 공간 규모 | `facility_lounge`, `facility_outdoor_space` | `review_comfortable_space`, `review_clean_space`, `review_stay_friendly`, `review_good_nearby_scenery`, `review_outdoor_space_good` |
| `nearby` | `distance_m` 역거리 | 없음 | 없음 |
| `program` | `active_program_count` | 활성 프로그램 분류 rollup | 프로그램 유형·대상 rollup과 프로그램 경험 태그 |

`program`은 홈 공개 테마가 아니지만 `UserPreferredPurpose` 개인화와 `analysis_axis=program` 계산을 위해 규칙을 유지한다. `nearby` 직접 선호는 요청 좌표가 있을 때만 적용한다.

### 11.4 오늘의 추천 도서관

생성 순서:

```text
1. 추천 날짜의 활성 DailyRecommendationTheme 선택
2. 부산 활성 도서관 후보 조회
3. 해당 날짜 LibraryDailySchedule.status=open만 남김
4. 테마 metric·tag 점수 계산
5. 필수 근거·결측 정책 적용
6. 결정론적 동점 처리
7. 상위 최대 3개를 DailyLibraryRecommendationSet/Item에 저장
```

- 사용자 가중치는 적용하지 않는다.
- 같은 날짜·지역·algorithm version은 idempotent 재생성한다.
- `closed`와 `unknown`은 제외한다.
- 추천 생성 후 운영표가 변경되어 후보가 닫힌 것으로 판정되면 홈 응답 전에 세트를 재검증하고 해당 항목을 제외한다. 다른 날짜 결과로 채우지 않는다.
- 동점 기준 권장: 점수 내림차순 → 근거 완전성 → `Library.id` 오름차순.

초기 테마 6개:

| code | 핵심 근거 |
|---|---|
| `large_space` | 건물·부지면적 |
| `rich_collection` | 장서 수 + 책 다양성 경험 |
| `mood_space` | 야외공간 + 분위기·경관 경험 |
| `study_seats` | 열람좌석 + 공부 경험 |
| `family_outing` | 어린이자료실 + 아이·가족 경험 |
| `restful_space` | `has_lounge=True` + 휴식·쾌적 경험 |

### 11.5 여기는 어때요?

노출 자격은 다음 중 하나 이상이다.

```text
활성 UserPreferredPurpose
활성 UserPreferredRegion
활성 UserPreferredTag
유효 행동 신호 1개 이상
```

계산:

```text
공개 목적·직접 태그 기반 후보 점수
+ 수동 선호 목적 보너스
+ 수동 선호 지역 보너스
+ 수동 선호 태그 보너스
+ UserPreferenceItem 행동 점수
```

후보 정책:

- 오늘 `open`만
- 오늘의 추천 3개 제외
- 비활성 도서관 제외
- 사용자가 저장한 도서관을 무조건 제외하지 않는다. 저장 이력은 관심 신호이므로 다시 추천될 수 있다.
- 최대 3개, 부족하면 그대로 반환
- 개인화 결과 테이블은 만들지 않고 user/date/version 기준 단기 캐시만 사용

### 11.6 비슷한 도서관

endpoint 요청 시 계산하고 영속 테이블을 만들지 않는다.

초기 가중치 권장:

```text
시설 True 집합 Jaccard           0.30
LibraryTag 가중 유사도          0.35
공개 목적 5개 점수 벡터 유사도  0.25
지역 유사도                      0.10
```

- 자기 자신·비활성 도서관 제외
- 동일 `tag_id`는 source별 중복을 제거한 뒤 계산
- 객관 시설 태그와 후기 경험 태그는 코드가 다르면 각각 계산
- 운영 여부는 유사도 자체에 포함하지 않되 카드에 `open_today`를 표시한다.
- 결과 최대 3개, 짧은 TTL 캐시 허용

### 11.7 프로그램 상태 보정

목록·상세 조회 전에 한 번의 bulk update로 날짜 기반 상태를 보정한다.

```text
application_required=False → 신청없음
required=True + today < application_start_date → NULL
required=True + start <= today <= end → 신청가능
required=True + today > end → 신청마감

 today < operation_start_date → 예정
 start <= today <= end → 진행중
 today > operation_end_date → 종료
```

날짜 누락·역전은 `NULL`로 두고 품질 로그에 남긴다. `*_raw`, `effective_*` 필드는 추가하지 않는다.

### 11.8 좋아요·조회수 일관성

좋아요 생성:

```python
with transaction.atomic():
    like, created = UserReviewLike.objects.get_or_create(...)
    if created:
        UserReview.objects.filter(pk=review_id).update(like_count=F("like_count") + 1)
```

좋아요 삭제는 관계가 삭제된 경우에만 `Greatest(F("like_count") - 1, 0)` 또는 DB 호환 방식으로 감소시킨다.

관리 명령:

```text
reconcile_review_like_counts
```

은 `Count("likes")`로 캐시를 재계산한다. 상세 조회수는 `F()` 증가를 사용하고 cache page view와 목록 조회에서는 증가하지 않는다.

### 11.9 나의 나들이 자동 성향

행동 source별 기본 가중치는 설정 상수로 둔다.

```text
library_save
book_save
program_save
review_written
review_liked
```

- 신호 발생일은 저장·작성·좋아요의 `created_at`을 사용한다.
- 90일 반감기, 최대 365일 관측창을 적용한다.
- 동일 review가 작성·좋아요 양쪽에 있으면 한 사용자에 대해 한 번만 반영하거나 source 상한을 적용한다. 선택한 정책을 `algorithm_version`에 기록한다.
- 결과는 `UserPreferenceItem`의 tag별 점수와 source count에 저장한다.
- 4축 목적 비율과 관심 분포는 dashboard 요청 시 현재 항목에서 계산하거나 짧은 캐시를 사용한다.
- 수동 선호는 자동 성향 통계에 섞지 않는다.

---

## 12. 외부 데이터·동기화

### 12.1 SourceSyncRun 원칙

수집 성공 여부는 도메인 행의 `verified` 필드가 아니라 `SourceSyncRun`에서 관리한다.

```text
source_name
target_year / target_month
status=success|failed|partial
started_at / finished_at
fetched_count / imported_count / skipped_count
error_message
```

행별 미매칭·파싱 실패는 JSON/CSV report와 구조화 로그에 남긴다. 서비스 테이블에는 `draft`, `verified`, `is_verified`, `verified_at`, `verified_by`를 두지 않는다.

### 12.2 전국도서관표준데이터

관리 명령 예시:

```bash
python manage.py import_library_standard --file "$LIBRARY_STANDARD_DATA_FILE" --sido 부산광역시
```

처리 순서:

1. top-level `fields`, `records` contract 검증
2. 부산 행 필터와 필수 키 검증
3. 이름·주소 정규화와 canonical identity 결정
4. `Library` upsert, alias·품질 report 생성
5. 운영시간·휴관 규칙 upsert
6. 통계 snapshot 생성
7. 운영표 재생성 예약
8. 직접 태그 재계산 예약

`제공기관코드`는 개별 도서관 식별자가 아니므로 `LibraryExternalIdentifier.external_code`로 사용하지 않는다.

### 12.3 시설 데이터

- 원천 구조를 배열 또는 JSONL로 정규화한 뒤 import한다.
- `library_name + sigungu`를 matcher에 전달하고 canonical `Library.id`가 단일 확정된 경우만 `LibraryFacilityProfile`을 upsert한다.
- 명시적 `true` → `True`, 명시적 `false` → `False`, 누락·`null` → `None`.
- 도서관 행 자체가 없으면 profile을 생성하지 않는다.
- facility direct tag는 값이 `True`일 때만 생성한다.
- 작업 파일의 파일명·완성도는 DB row 상태로 옮기지 않는다.

### 12.4 외관 이미지

- 이미지 행만으로 새 도서관을 생성하지 않는다.
- 빈 URL은 `MediaAsset`을 만들지 않는다.
- 이용허락과 출처문구가 확인된 공식 외부 asset만 `is_active=True`로 공개 연결한다.
- 공식 외부 asset은 `license_code`, `attribution_text` 필수다.
- `source_page_url`은 내부 추적용이며 공개 serializer에 필요하지 않다.
- 도서관 이미지가 없으면 유형별 fallback을 사용한다.

### 12.5 문화 프로그램

- 월 단위 JSON을 idempotent import한다.
- `provider_code + external_program_key`로 upsert한다. 원천 ID가 없으면 source URL·제목·도서관·운영기간의 안정 해시를 사용한다.
- 도서관 매칭 실패 행은 `Program(library=NULL)`로 저장하지 않고 reject한다.
- `target_codes`에 `other`를 허용한다.
- 원천 상태는 초기값으로 적재한 뒤 조회·일일 작업에서 현재 날짜 기준으로 보정한다.
- 원천에서 사라진 프로그램은 즉시 물리 삭제하지 않고 `is_visible=False`, `deleted_at`으로 soft delete한다.

### 12.6 공휴일 12개월 수집

관리 명령 예시:

```bash
python manage.py sync_public_holidays --year 2026
```

- `solMonth=01`~`12`를 반복 호출한다.
- 각 응답은 `resultCode=00`과 `totalCount <= numOfRows`를 검증한다.
- `isHoliday=Y`만 `PublicHoliday`에 저장한다.
- 12개월이 모두 성공한 경우에만 새 달력을 transaction으로 교체하고 `PublicHolidayCalendar.is_complete=True`, `synced_month_count=12`로 갱신한다.
- 일부 월 실패 시 기존 완전 달력을 유지하고 실행은 `partial` 또는 `failed`로 남긴다.
- 연초 전체 수집을 기본으로 하되 임시공휴일 반영을 위해 현재 연도 재수집을 실행할 수 있다.

### 12.7 정보나루

환경변수 `DATA4LIBRARY_API_KEY`를 Django에서만 사용한다.

| 기능 | endpoint | 저장·캐시 |
|---|---|---|
| 도서 검색 | `srchBooks` | 검색 캐시 + Book upsert 선택 |
| 도서 상세 | `srchDtlList` | Book 상세 갱신 |
| 인기대출 | `loanItemSrch` | 주간 snapshot |
| 소장 도서관 | `libSrchByBook` | LibraryHolding 갱신 |
| 도서관 선연결 | `libSrch` | LibraryExternalIdentifier |
| 다독자 추천 | `recommandList?type=reader` | 단기 캐시, 선택 기능 |

`bookExist`는 조회일 전날 대출 상태이므로 실시간 대출 가능으로 표시하지 않는다.

### 12.8 GMS 경계

GMS는 Django를 경유한다.

```text
Vue → Django → GMS → Django → Vue
```

허용:

- 이미 계산된 나의 나들이 상위 성향을 자연스러운 한 문장으로 표현
- 결정론적 template의 보조 표현 생성

금지:

- 도서관 운영·시설·소장 사실 생성
- 추천 후보·점수·순위 결정
- 후기 태그 자동 저장
- 원천에 없는 근거 생성

timeout·오류·quota 초과 시 template으로 즉시 fallback한다.

---

## 13. 캐시·비동기 작업

### 13.1 권장 작업

| 작업 | 주기·트리거 | 역할 |
|---|---|---|
| `sync_public_holidays` | 연초 전체 + 필요 시 재수집 | 공휴일 달력 완전 적재 |
| `build_library_daily_schedules` | 매일 또는 원천 변경 후 | 향후 180일 운영표 생성 |
| `generate_daily_library_recommendations` | 매일 운영표 생성 후 | 오늘의 추천 세트 생성 |
| `sync_weekly_popular_books` | 주 1회 | 부산 인기 도서 snapshot |
| `import_programs` | 월 1회 또는 파일 도착 시 | 프로그램 upsert·soft delete |
| `refresh_program_statuses` | 매일 + 조회 전 보정 | 프로그램 상태 갱신 |
| `rebuild_library_tag_rollups` | 시설·프로그램·후기 변경 후 | LibraryTag 집계 |
| `rebuild_user_preference` | 저장·후기·좋아요 commit 후 debounce | 행동 기반 성향 갱신 |
| `reconcile_review_like_counts` | 일 1회 또는 운영 명령 | 좋아요 관계·카운터 정합성 |

Celery를 사용하지 않는 MVP에서는 동일 로직을 management command와 배포 scheduler로 실행할 수 있다. service 함수는 command·task·API가 재사용하도록 분리한다.

### 13.2 캐시 키

```text
home:daily:{date}:{region_key}:{algorithm_version}
home:personal:{user_id}:{date}:{preference_version}
home:theme:{purpose}:{lat_bucket}:{lng_bucket}:{rules_version}
library:similar:{library_id}:{rules_version}
book:search:{query_hash}
book:detail:{isbn13}
book:holdings:{isbn13}:21
program:list:{query_hash}:{status_date}
myoutings:dashboard:{user_id}:{preference_version}
```

- 당일 운영·오늘의 추천은 다른 날짜 cache로 fallback하지 않는다.
- 사용자 저장·좋아요·선호 변경 후 해당 사용자 cache를 무효화한다.
- 후기·시설·프로그램 rollup 변경 후 관련 도서관 유사도·테마 cache를 무효화한다.

---

## 14. 쿼리·성능 설계

### 14.1 목록 queryset

도서관 목록:

```python
Library.objects.filter(is_active=True).select_related(
    "facility_profile"
).prefetch_related(
    "images__media_asset",
    "tag_links__tag",
)
```

최신 통계·오늘 운영표는 `Subquery`, `FilteredRelation`, 별도 materialized annotation service 중 하나로 일관되게 구현한다. Python loop에서 도서관별 추가 쿼리를 실행하지 않는다.

프로그램 목록:

```python
Program.objects.filter(is_visible=True, deleted_at__isnull=True).select_related(
    "library"
).prefetch_related("tag_links__tag", "images__media_asset")
```

후기 목록:

```python
UserReview.objects.filter(
    moderation_status="visible"
).select_related(
    "user", "user__profile", "library"
).prefetch_related(
    "tag_links__tag",
    "book_references__book",
    "program_references__program__library",
    "images",
)
```

로그인 사용자의 `is_saved`, `is_liked`는 `Exists` subquery로 annotate한다.

### 14.2 인덱스

ERD의 핵심 인덱스 외에 다음을 확인한다.

- trigram 또는 full-text: `Library.normalized_name`, 주소, 운영기관, `Tag.label`
- 프로그램: `(is_visible, operation_status, operation_start_date)`, `(library_id, is_visible)`
- 후기: 공개 상태와 세 정렬 인덱스
- 저장: `(user_id, -created_at)`
- 일일 운영표: `(date, status)`, `(library_id, date)`
- 목적 규칙: `(purpose_id, is_required)`

### 14.3 페이지 크기

- 기본 20
- 최대 100
- 홈 preview는 고정 limit 3 또는 6
- 비슷한 도서관은 최대 3
- 후기 관련 책·프로그램 미니 카드는 각각 최대 5

### 14.4 동시성

- 좋아요 카운터·조회수는 `F()` 표현식
- 일일 추천·공휴일 연간 교체는 transaction + idempotency key
- 사용자 선호 rebuild는 user 단위 lock 또는 task deduplication
- 같은 import file의 중복 실행은 source hash·external key로 idempotent 처리

---

## 15. 권한·보안·개인정보

- API 키는 `.env`와 server secret에만 두고 Git에 커밋하지 않는다.
- `.env.example`에는 변수명만 제공한다.
- 회원 수정 endpoint는 본인만 접근한다.
- 후기 수정·삭제는 작성자 또는 관리자만 허용한다.
- hidden 후기는 공개 목록·추천·rollup·좋아요 대상에서 제외한다.
- 외부 URL은 `http/https` allowlist와 scheme validation을 적용한다.
- 업로드 이미지는 MIME·용량·확장자 검증, UUID 파일명, 악성 파일 검사를 적용한다.
- 사용자 현재 좌표는 요청 계산에만 사용하고 DB·로그에 원문 저장하지 않는다.
- 이메일은 공개 serializer에 포함하지 않는다.
- 이미지 출처문구는 이용조건을 훼손하지 않도록 원문을 보존한다.
- `source_page_url`은 공개 링크가 아니며 내부 추적 데이터다.

---

## 16. Django Admin

| 앱 | 주요 admin 기능 |
|---|---|
| accounts | 사용자·프로필, 선호 목적·지역·태그 inline |
| tags | semantic kind·group·선택 가능 여부 필터, 후기 그룹 순서 |
| libraries | alias·external ID·시설·이미지·태그·운영표 inline/링크, 미매칭 report 링크 |
| media_assets | 원천·라이선스·출처문구·활성 상태 필터 |
| books | ISBN·KDC·태그·소장 관계 검색 |
| programs | 도서관·분류·대상·상태·기간 필터, 원문 링크 |
| community | 공개 상태·도서관·작성자·좋아요·조회수 필터, hide action |
| myoutings | 세 저장 관계 검색·중복 확인 |
| preferences | 계산 상태·신호 수·algorithm version, rebuild action |
| recommendations | Purpose 규칙, 일일 테마·세트·점수 detail 확인 |
| integrations | SourceSyncRun 상태·처리 건수·오류 조회 |

Admin에서 도메인 데이터 행에 `verified`를 추가하지 않는다. import 품질은 실행 로그와 report로 확인한다.

---

## 17. 테스트 명세

### 17.1 모델·migration

- 커스텀 User가 초기 migration에서 순환 의존 없이 생성됨
- accounts 후속 migration이 Tag·Purpose FK를 정상 생성함
- 모든 FK의 `on_delete`, `related_name`, nullable 설정이 관계표와 일치함
- 모든 unique·check·조건부 unique가 DB에서 동작함
- `python manage.py makemigrations --check --dry-run` 결과가 깨끗함
- 빈 DB에 전체 migration 적용·reverse 가능한 범위를 검증함

### 17.2 태그·시설

- `facility_parking`과 `review_parking_convenient`가 별도 Tag로 존재함
- 같은 tag의 여러 LibraryTag source는 표시에서 중복 제거됨
- 서로 다른 객관·경험 태그는 함께 표시됨
- 시설 `True`만 direct 태그·긍정 필터에 사용됨
- `False`, `None`, profile 부재가 서로 보존됨
- 후기 경험 태그가 시설 boolean을 변경하지 않음

### 17.3 도서관 매칭

- exact name+sigungu, alias, correction map 순서
- 지역 누락·오타·중복 후보는 자동 연결되지 않음
- 원천 이름으로 서비스 FK를 직접 생성하지 않음
- 같은 주소라도 실제 별도 시설인 행은 병합하지 않음

### 17.4 운영·공휴일

- 12개월 전체 성공 전 calendar complete가 되지 않음
- 일부 월 실패 시 기존 complete calendar 유지
- `open_today`, `open_now` 차이
- 시간 없는 open day의 `open_today=true`, `open_now=null/false filter 제외`
- 가장 가까운 주말 OR 규칙
- `holiday_status` 삼분형
- 18시 이후 운영 필터
- 휴관 문구와 운영시간 충돌 시 `unknown`

### 17.5 홈·목적·유사도

- 홈 목적은 5개만 노출되고 program은 제외됨
- program은 프로필 선택·분석에 사용 가능함
- nearby는 좌표 없을 때 400
- 홈 preview와 도서관 찾기 purpose 점수가 동일함
- 오늘 추천은 open 후보만, 공통 최대 3개
- 개인화는 공통 결과와 중복 없음, open 후보만
- 데이터 없는 회원은 personalized section 비노출
- restful_space가 lounge direct 근거를 사용함
- 유사도에서 동일 tag source 중복 제거, 객관·경험 별도 기여

### 17.6 프로그램

- `library_id` 필터
- `other` 대상 코드
- 신청기간 전/중/후 상태
- 신청 불필요 상태
- 운영 예정/진행/종료 상태
- 날짜 누락·역전 null
- 조회 전 bulk 보정 idempotency
- 관련 후기 프로그램이 같은 도서관인지 검증

### 17.7 커뮤니티

- 본문 1~200자
- 태그 1~5개, 경험 태그만 허용
- rating/title/purpose 입력 거절
- 관련 책·프로그램 unique와 최대 개수
- 최신·조회수·좋아요 정렬
- q가 본문·도서관명을 검색
- 후기 상세 조회만 view count 증가
- 좋아요 PUT/DELETE idempotency
- 동시 좋아요에서 관계 중복 없음과 카운터 정합성
- reconcile 명령이 실제 관계 수로 복구
- 후기 저장 모델·endpoint 부재
- hidden 후기 공개·좋아요·rollup 제외

### 17.8 나의 나들이

- 세 저장 목록, 좋아요한 후기, 작성 후기 반환
- 저장·후기·좋아요 변화 후 rebuild 예약
- 90일 반감기·365일 관측창
- 동일 후기 작성+좋아요 중복 신호 방지
- 4축 합이 100 또는 신호 없음 처리
- KDC·프로그램 분야·지역 분포
- 수동 선호가 행동 분포에 섞이지 않고 개인화에만 보너스로 적용됨
- 대표 문장 template fallback

### 17.9 이미지

- 공식 외부 활성 asset의 license·attribution 필수
- 이미지 없는 도서관의 유형별 fallback
- 프로그램 분류별·후기·프로필 fallback
- 공개 응답에 attribution·license 포함
- source page URL 비노출 가능
- ⓘ overlay 키보드 focus·모바일 tap 접근성 계약

### 17.10 외부 API contract

- 정보나루 JSON/XML 기본값 차이를 방지하기 위해 `format=json` 고정
- timeout·retry·응답 schema 오류
- libCode 선연결과 미매칭 reject
- `bookExist`를 실시간으로 노출하지 않음
- 공휴일 `resultCode`, pagination 검증
- SourceSyncRun 처리 건수 정확성

---

## 18. 구현 순서

### Phase 0. 프로젝트 기반

1. 커스텀 User를 코드 작성 전에 확정하고 `AUTH_USER_MODEL` 설정
2. 공통 abstract model·choices·validator 작성
3. PostgreSQL·DRF·환경변수·테스트 설정
4. 앱 생성

```bash
mkdir -p apps
touch apps/__init__.py
cd apps
python ../manage.py startapp common
python ../manage.py startapp tags
python ../manage.py startapp media_assets
python ../manage.py startapp accounts
python ../manage.py startapp libraries
python ../manage.py startapp books
python ../manage.py startapp programs
python ../manage.py startapp recommendations
python ../manage.py startapp community
python ../manage.py startapp myoutings
python ../manage.py startapp preferences
python ../manage.py startapp integrations
cd ..
```

### Phase 1. migration 기반

권장 순서:

1. `accounts.0001` — `User`, `UserProfile`, `UserPreferredRegion`
2. `tags.0001`, `media_assets.0001`
3. `libraries.0001`
4. `books.0001`, `programs.0001`, `recommendations.0001`
5. `accounts.0002` — `UserPreferredTag`, `UserPreferredPurpose`
6. `community.0001`, `myoutings.0001`, `preferences.0001`, `integrations.0001`

`accounts.0001`은 `Tag`와 `Purpose` FK를 포함하지 않는다. 교차 앱 모델은 후속 migration으로 분리한다.

### Phase 2. seed·import

1. Tag seed와 후기 그룹
2. Purpose 6행 중 홈 공개 5개 플래그
3. 일일 테마 6개와 규칙
4. 기본 이미지 asset·fallback 규칙
5. 표준 도서관 JSON
6. alias/correction map
7. 시설·이미지
8. 공휴일 연간 달력과 운영표
9. 프로그램 JSON
10. 정보나루 libCode 선연결

### Phase 3. 읽기 API

1. 도서관 목록·상세·운영 필터
2. 목적 score service와 홈 테마 preview
3. 오늘의 추천 생성·홈 응답
4. 책 검색·상세·인기·소장
5. 프로그램 목록·상태 보정

### Phase 4. 사용자 상호작용

1. 프로필 선호 설정
2. 도서관·책·프로그램 저장
3. 후기 CRUD·태그·관련 콘텐츠·이미지
4. 조회수·좋아요
5. 나의 나들이 dashboard와 성향 rebuild
6. 여기는 어때요?
7. 비슷한 도서관

### Phase 5. 운영 보강

1. SourceSyncRun·reject report
2. 캐시·작업 scheduler
3. 카운터 reconcile
4. 관리자 화면
5. contract·통합·성능 테스트
6. 배포·모니터링

---

## 19. MVP 완료 조건

### 계정·프로필

- 이메일·닉네임 가입
- 프로필 표시·수정
- 선호 목적·지역·태그 설정
- 가입 시 기본 지역 강제 입력 없음

### 홈

- 오늘의 추천 최대 3개
- 데이터 있는 회원에게 여기는 어때요 최대 3개
- 두 section 중복 없음
- 홈 공개 테마 5개, 각 preview 최대 6개
- more link가 `/libraries/?purpose=`로 같은 결과 규칙을 재현

### 도서관

- 전체 목록·검색·필터
- open today와 open now 구분
- 주말·공휴일 삼분형·18시 이후 운영
- 시설 True 필터와 장서·좌석 조건
- 상세의 출처문구 overlay, 프로그램·후기·유사 도서관

### 책

- 주간 인기
- 도서명·저자·ISBN 검색
- 상세 요약·KDC 태그·소개
- 부산 소장 도서관

### 프로그램

- 프로그램·도서관명 검색
- 지역·도서관·유형·대상·상태 필터
- 날짜 기준 상태 보정
- 원문 링크와 개최 도서관 연결

### 커뮤니티

- 200자 후기, 태그 1~5개
- 관련 책·프로그램 미니 카드
- 최신·조회·좋아요 정렬
- 좋아요 관계와 카운터
- 후기 저장·별점·별도 제목 없음

### 나의 나들이

- 저장한 도서관·책·프로그램
- 좋아요한 후기·내가 쓴 후기
- 4축 목적 비율·상위 태그
- 책 주제·프로그램 분야·지역 분포
- 데이터 변경 후 자동 갱신

### 데이터 운영

- 표준 도서관·시설·이미지·프로그램 import
- 이미지·시설 누락 정상 처리
- 공휴일 12개월 완전 수집
- 휴관·미확인 도서관의 오늘 추천 제외
- 외부 이름을 Library.id로 안전하게 매칭
- row별 draft/verified 필드 없음

---

## 20. 최종 models.py 확인표

코드 생성 직전에 다음을 확인한다.

1. `AUTH_USER_MODEL`이 첫 migration 전에 확정되었는가.
2. 모든 FK가 문자열 참조·명시적 `on_delete`·고유한 `related_name`을 갖는가.
3. `UserPreferredTag`·`UserPreferredPurpose`가 후속 accounts migration으로 분리되는가.
4. `LibraryFacilityProfile`이 OneToOne nullable boolean 구조인가.
5. 외부 `library_name`을 FK처럼 쓰는 필드나 query가 없는가.
6. `UserReviewSave`, review rating, review title, review purpose가 없는가.
7. `UserReviewLike` unique와 `UserReview.like_count` cache가 함께 있는가.
8. `ProgramSession`과 실시간 좌석 모델이 없는가.
9. `Purpose.program.is_home_theme=False`이고 공개 필터가 5개만 허용하는가.
10. `Purpose.nearby.requires_location=True`인가.
11. 공휴일 완전성 모델과 수집 실행 로그의 역할이 분리되어 있는가.
12. `MediaAsset` 공식 외부 활성 조건에 출처문구·라이선스 검증이 있는가.
13. 객관 태그와 경험 태그가 별도 코드이고, 같은 tag_id만 표시 중복 제거하는가.
14. 추천·유사 도서관·나의 나들이 파생 결과 중 불필요한 영속 테이블을 만들지 않았는가.
15. unique·check·조건부 unique 이름이 프로젝트 전체에서 충돌하지 않는가.
16. migration dependency graph가 순환하지 않는가.

---

## 21. 참고 문서

- `library_outing_ERD_v3.md`
- 최종 도서관 나들이 주요 페이지 구조
- 데이터셋 정보 문서
- 전국도서관표준데이터 부산 JSON
- LibraryImage CSV
- 도서관 시설 데이터 JSON
- 정보나루 Open API 매뉴얼
- 한국천문연구원 특일 정보 API
- GMS 사용 문서
