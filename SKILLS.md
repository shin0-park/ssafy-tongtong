## 0. 기준

이 문서는 `docs/library_outing_Django_spec_v3.md`와 `docs/library_outing_ERD_v3.md`를 구현하기 위한 기술 스택 요약 문서다.

구체적인 모델 필드, 제약조건, `related_name`, API 계약, import 정책은 v3 문서를 최우선으로 따른다.

## 1. 기본 기술 스택

### Backend

* Python 3.11
* Django `>=5.2,<5.3`
* Django REST Framework `>=3.16,<3.17`
* PostgreSQL 16 이상 권장
* Redis 7 이상 권장
* Celery `>=5.6,<5.7`
* httpx
* django-environ
* django-filter
* drf-spectacular
* djangorestframework-simplejwt
* Pillow
* pytest
* pytest-django

### Frontend

* Node.js LTS
* Vue 3
* Vite
* Vue Router
* Pinia
* Axios
* Bootstrap 5.3

## 2. 권장 Backend 패키지

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

```text
django-storages
boto3
rapidfuzz
python-dateutil
sentry-sdk
```

PostgreSQL 검색 고도화 시 `pg_trgm` 사용을 고려한다.

## 3. 권장 프로젝트 구조

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

## 4. Django 앱 책임

### common

공통 추상 모델, 예외 처리, 응답 포맷, pagination, 날짜·지역·문자열 유틸리티를 담당한다.

주요 요소:

* `TimeStampedModel`
* 공통 pagination
* 공통 exception handler
* 정규화 유틸리티
* 한국 시간 기준 date helper

### tags

공통 태그 어휘와 선택 정책을 담당한다.

주요 모델:

* `Tag`

핵심 역할:

* 객관 태그와 경험 태그 분리
* 프로필 선택 가능 태그
* 후기 선택 가능 태그
* 필터 노출 가능 태그
* KDC·프로그램·시설·후기 태그 연결의 기준 어휘 제공

### accounts

사용자 인증, 프로필, 직접 선언한 선호를 담당한다.

주요 모델:

* `User`
* `UserProfile`
* `UserPreferredRegion`
* `UserPreferredTag`
* `UserPreferredPurpose`

로그인은 이메일 기반이다.

`User`에는 기본 지역이나 현재 좌표를 저장하지 않는다.

### media_assets

공식 이미지, 시스템 기본 이미지, 사용자 업로드 이미지의 출처·라이선스·fallback 규칙을 담당한다.

주요 모델:

* `MediaAsset`
* `DefaultMediaAssetRule`

공식 외부 이미지는 `license_code`, `attribution_text`를 관리한다.

### libraries

도서관 canonical identity, 별칭, 외부 코드, 운영시간, 휴관 규칙, 공휴일, 운영표, 통계, 시설, 태그, 이미지를 담당한다.

주요 모델:

* `Library`
* `LibraryAlias`
* `LibraryExternalIdentifier`
* `LibraryOpeningHour`
* `LibraryClosureRule`
* `PublicHolidayCalendar`
* `PublicHoliday`
* `LibraryDailySchedule`
* `LibraryStatisticSnapshot`
* `LibraryFacilityProfile`
* `LibraryTag`
* `LibraryImage`

도서관 관계의 기준은 내부 `Library.id`다.

### books

책 메타데이터, KDC 태그, 소장 도서관, 인기 도서 스냅샷을 담당한다.

주요 모델:

* `Book`
* `BookTag`
* `LibraryHolding`
* `PopularBookSnapshot`
* `PopularBookItem`

전체 장서를 사전 적재하지 않는다.

검색·상세·저장·인기 목록에 노출된 책과 확인된 소장 관계만 선택적으로 저장한다.

### programs

문화 프로그램, 프로그램 상태, 분류, 대상, 이미지 연결을 담당한다.

주요 모델:

* `Program`
* `ProgramTag`
* `ProgramImage`

프로그램 신청·예약·결제·참여 이력은 서비스 범위가 아니다.

프로그램 상태는 조회 전 현재 날짜 기준으로 재계산한다.

### recommendations

방문 목적, 홈 5개 공개 테마, 일일 추천 규칙과 결과를 담당한다.

주요 모델:

* `Purpose`
* `PurposeTagRule`
* `PurposeMetricRule`
* `DailyRecommendationTheme`
* `DailyRecommendationMetricRule`
* `DailyRecommendationTagRule`
* `DailyLibraryRecommendationSet`
* `DailyLibraryRecommendationItem`

홈 공개 테마는 `study`, `book`, `kids`, `mood`, `nearby` 5개다.

`program` 목적은 홈 공개 테마가 아니라 프로필 선택, 프로그램형 분석, 개인화에 사용한다.

### community

후기, 조회수, 좋아요, 후기 이미지, 관련 책·프로그램, 후기 태그를 담당한다.

주요 모델:

* `UserReview`
* `UserReviewLike`
* `UserReviewImage`
* `ReviewBookReference`
* `ReviewProgramReference`
* `ReviewTag`

후기 저장 모델은 만들지 않는다.

### myoutings

사용자가 저장한 도서관·책·프로그램을 담당한다.

주요 모델:

* `UserLibrarySave`
* `UserBookSave`
* `UserProgramSave`

좋아요한 후기는 `community.UserReviewLike`를 조회한다.

### preferences

행동 기반 자동 성향 상태와 태그 점수를 담당한다.

주요 모델:

* `UserPreference`
* `UserPreferenceItem`

`preferences` service는 `community`, `myoutings`를 조회할 수 있지만 모델 FK는 두지 않는다.

### integrations

외부 API client, 파일 loader, normalizer, import, 동기화 실행 이력을 담당한다.

주요 모델:

* `SourceSyncRun`

원천별 실패 행, 미매칭 목록, merge 후보는 DB 도메인 행에 검수 상태를 넣지 말고 report 파일, 구조화 로그, 관리 명령 출력으로 남긴다.

## 5. 앱 의존 방향

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

교차 앱 FK는 문자열 참조를 사용한다.

예시:

```python
models.ForeignKey("libraries.Library", ...)
models.ForeignKey("tags.Tag", ...)
models.ForeignKey("recommendations.Purpose", ...)
```

사용자 FK는 항상 `settings.AUTH_USER_MODEL`을 사용한다.

## 6. 권장 migration 순서

1. `common`
2. `accounts.0001`: `User`, `UserProfile`, `UserPreferredRegion`
3. `tags.0001`, `media_assets.0001`
4. `libraries.0001`
5. `books.0001`, `programs.0001`, `recommendations.0001`
6. `accounts.0002`: `UserPreferredTag`, `UserPreferredPurpose`
7. `community.0001`, `myoutings.0001`, `preferences.0001`, `integrations.0001`

커스텀 User 초기 migration이 `Tag`, `Purpose`에 의존하지 않도록 선호 태그·선호 목적 모델은 후속 migration으로 분리한다.

## 7. Django 설정 기준

```python
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

한국 기준 날짜 계산에는 `ZoneInfo("Asia/Seoul")`를 명시한다.

외부 날짜·시간은 파싱 즉시 aware datetime 또는 명시적 `date`로 변환한다.

## 8. 환경변수

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

`.env`는 Git에 포함하지 않는다.

`.env.example`에는 변수명과 예시 값만 둔다.

## 9. 외부 API

### 정보나루 API

Django backend에서만 호출한다.

사용 예정 API:

* 도서관 조회: `libSrch`
* 도서 검색: `srchBooks`
* 인기대출도서: `loanItemSrch`
* 도서 상세: `srchDtlList`
* 다독자 추천도서: `recommandList?type=reader`
* 도서 소장 도서관: `libSrchByBook`
* 도서관/지역별 인기대출도서: `loanItemSrchByLib`

부산 지역 조회는 `region=21`을 사용한다.

응답 형식은 가능하면 `format=json`을 명시한다.

### 공휴일 API

Django backend에서만 호출한다.

사용 API:

```text
getRestDeInfo
```

월별로 1월부터 12월까지 호출하고, 모두 성공한 연도만 `PublicHolidayCalendar.is_complete=True`로 둔다.

공휴일 판단에는 `isHoliday=Y`인 항목만 사용한다.

### GMS API

Django backend에서만 호출한다.

사용 목적:

* 추천 문구 생성
* 나의 나들이 요약 문장 생성
* 사용자 친화적 설명 생성

사용 금지:

* 추천 순위 결정
* 사실 필드 생성
* 시설 여부 판단
* 운영 여부 판단

권장 흐름:

```text
Vue → Django API → GMS API → Django → Vue
```

## 10. 추천 로직 MVP

추천은 설명 가능한 점수 기반으로 구현한다.

GMS는 추천 점수 계산 이후 설명 문구 생성에만 사용한다.

### 오늘의 추천

후보 조건:

```text
LibraryDailySchedule.status = open
```

닫힘, unknown, 운영표 누락 도서관은 후보에서 제외한다.

오늘의 추천 기준은 다음 중 하나다.

* 넓은 공간
* 풍부한 장서
* 공간 분위기
* 차분한 열람
* 가족 나들이
* 쉬어가기

결과는 모든 사용자에게 동일한 최대 3개다.

### 여기는 어때요?

로그인 사용자에게만 제공한다.

다음 중 하나 이상의 신호가 있어야 한다.

* 선호 목적
* 선호 지역
* 선호 태그
* 저장한 도서관
* 저장한 책
* 저장한 프로그램
* 좋아요한 후기
* 작성 후기

오늘의 추천과 중복되지 않는 최대 3개를 반환한다.

### 테마별 추천

공개 테마:

```text
study
book
kids
mood
nearby
```

기본 반환 개수는 6개다.

도서관 찾기와 같은 목적 필터 규칙을 재사용한다.

## 11. 주요 Backend API 초안

정확한 상세 계약은 v3 명세를 따른다.

```text
/api/accounts/signup/
/api/accounts/login/
/api/accounts/profile/
/api/accounts/preferences/

/api/tags/
/api/tags/review-options/
/api/tags/profile-options/

/api/libraries/
/api/libraries/{id}/
/api/libraries/{id}/save/
/api/libraries/{id}/similar/
/api/libraries/{id}/programs/
/api/libraries/{id}/reviews/

/api/books/popular/
/api/books/search/
/api/books/{isbn}/
/api/books/{isbn}/libraries/
/api/books/{isbn}/save/

/api/programs/
/api/programs/{id}/
/api/programs/{id}/save/

/api/reviews/
/api/reviews/{id}/
/api/reviews/{id}/like/
/api/reviews/{id}/unlike/

/api/my-outings/dashboard/
/api/my-outings/libraries/
/api/my-outings/books/
/api/my-outings/programs/
/api/my-outings/liked-reviews/
/api/my-outings/my-reviews/

/api/recommendations/today/
/api/recommendations/themes/
/api/recommendations/personal/
/api/recommendations/gms-message/
```

## 12. Frontend 구조

```text
frontend/
  src/
    api/
      axios.js
      accounts.js
      tags.js
      libraries.js
      books.js
      programs.js
      community.js
      myoutings.js
      recommendations.js
    assets/
    components/
      common/
      library/
      book/
      program/
      community/
      myouting/
    router/
      index.js
    stores/
      auth.js
      saved.js
      preference.js
    views/
      HomeView.vue
      LibrarySearchView.vue
      LibraryDetailView.vue
      BookExploreView.vue
      ProgramView.vue
      CommunityView.vue
      ReviewDetailView.vue
      MyOutingView.vue
      ProfileView.vue
      ProfileSettingsView.vue
      LoginView.vue
      SignupView.vue
    App.vue
    main.js
```

## 13. Frontend Routes

```text
/                         홈
/libraries                 도서관 찾기
/libraries/:id             도서관 상세
/books                     책 둘러보기
/programs                  문화 프로그램
/community                 커뮤니티
/community/:id             후기 상세
/my                        나의 나들이
/profile                   프로필
/profile/settings          프로필 설정
/login                     로그인
/signup                    회원가입
```

## 14. UI 기준

* Bootstrap 5.3 기반
* 카드형 레이아웃
* 태그 칩 적극 활용
* 도서관 이미지는 16:9 비율 권장
* 책 표지는 세로형 비율 유지
* 프로그램 카드는 운영 도서관, 운영 기간, 대상, 신청/운영 상태를 명확히 표시
* 후기 카드는 200자 이내 본문, 태그, 관련 책·프로그램 미니 카드 표시
* 이미지 위 ⓘ는 출처문구 오버레이로 구현
* 비로그인 또는 데이터 부족 시 “여기는 어때요?” 섹션은 표시하지 않음

## 15. import / fixture 정책

사용 데이터:

* 부산 도서관 표준 데이터 JSON
* 도서관 시설 데이터 JSON
* 도서관 외관 이미지 데이터 CSV 또는 JSON
* 문화 프로그램 JSON
* 공휴일 API
* 정보나루 API

외부 `library_name`은 직접 FK로 사용하지 않는다.

import 흐름:

```text
원천 파일/API
→ normalize
→ Library exact match
→ LibraryAlias match
→ 검수된 correction map
→ Library.id 확정
→ upsert
```

모호한 데이터는 자동 연결하지 않고 report에 남긴다.

import는 idempotent하게 작성한다.

## 16. 테스트 우선순위

1. 모델 생성과 migration 순서
2. 도서관 import 매칭
3. 시설 nullable boolean 처리
4. 공휴일 12개월 complete 처리
5. 운영표 계산
6. 오늘 추천 후보 필터링
7. 후기 작성 검증
8. 후기 좋아요 idempotent 처리
9. 태그 의미 분리
10. GMS 실패 fallback

## 17. 작업 우선순위

### 1순위

* 프로젝트 초기 구조
* accounts 커스텀 User
* tags
* media_assets
* libraries 핵심 모델
* books 핵심 모델
* programs 핵심 모델
* community 핵심 모델
* myoutings 저장 모델
* recommendations Purpose 기본 구조
* migrations 정상 생성

### 2순위

* 도서관 표준 데이터 import
* 시설 데이터 import
* 이미지 데이터 import
* 프로그램 데이터 import
* 도서관 목록/상세 API
* 도서관 필터 API
* 후기 CRUD/like API
* 저장 API

### 3순위

* 공휴일 API 수집
* 운영표 생성
* 오늘의 추천
* 테마별 추천
* 나의 나들이 dashboard
* 책 검색/상세/소장 도서관 API
* GMS 문구 생성

### 4순위

* 프론트 UI 고도화
* 캐시
* Celery beat
* 배포
* 테스트 보강
* README 정리

## 18. README에 포함할 내용

* 프로젝트 소개
* 문제 정의
* 주요 기능
* 기술 스택
* 데이터 출처
* API Key 설정 방법
* 실행 방법
* DB migration 순서
* fixture/import 방법
* 추천 알고리즘 설명
* GMS 사용 위치
* Git 협업 방식
* 팀원 역할
* 구현 한계 및 향후 개선점
