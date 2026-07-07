# 도서관 나들이 기술 스택 및 구현 참고

- 문서 성격: 기술 스택과 구현 경계 요약
- 최종 갱신: 2026-06-24
- 주의: 이 문서는 Endpoint·DTO·Frontend Route를 중복 정의하지 않는다.

## 0. 문서 범위와 우선순위

이 문서는 기술 선택, 앱 책임, 패키지, 환경변수, 외부 API와 테스트 대상을 요약한다.

| 관심사 | 기준 문서 |
|---|---|
| 현재 코드·migration·설정 | 실제 저장소 |
| 현재 공개 API Endpoint·Method·Request·Response | `library_outing_frontend_api_contract_v4.0.md` |
| 모델·관계·도메인 정책 | `library_outing_Django_spec_v4.0.md`, `library_outing_ERD_v4.0.md` |
| Frontend 구조·Route·Store·Service·UI/UX | `library_outing_frontend_spec_v4.0.md` |
| 기술 스택·패키지 요약 | 본 문서 |

현재 구현과 문서가 다르면 코드를 자동 변경하지 않는다. 먼저 실제 코드와 테스트를 확인하고 차이를 보고한다.

### 인증 관련 확정 사항

- Django 인증의 로그인 식별자는 **이메일**이다.
- Django admin에서 이메일과 비밀번호 로그인이 확인되었다.
- username 로그인을 새로 도입하지 않는다.
- 과거 API/Frontend 문서의 `username` 로그인 예시는 현재 인증 구현과 충돌하는 구형 예시다.
- 실제 인증 API 요청 키는 로그인 serializer를 확인하여 사용한다. 전송 키가 `username`이더라도 이메일 값을 받는 호환 어댑터일 수 있으므로 User 모델의 식별자와 구분한다.

## 1. 기본 기술 스택

### Backend

- Python 3.11
- Django `>=5.2,<5.3`
- Django REST Framework `>=3.16,<3.17`
- PostgreSQL 16 이상 권장
- Redis 7 이상 권장
- Celery `>=5.6,<5.7`
- httpx
- django-environ
- django-filter
- drf-spectacular
- djangorestframework-simplejwt
- Pillow
- pytest
- pytest-django

### Frontend

- Node.js LTS
- Vue 3
- Vite
- Vue Router
- Pinia
- Axios
- Bootstrap 5.3
- Kakao Map JavaScript SDK

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

## 3. 권장 Backend 구조

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

Frontend의 실제 디렉터리와 Route는 Frontend 명세 v4.0을 따른다. 본 문서에 별도 Frontend 폴더 구조를 복제하지 않는다.

## 4. Django 앱 책임

### common

공통 추상 모델, 예외, pagination, 날짜·지역·문자열 유틸리티를 담당한다.

### tags

공통 태그 어휘와 객관·경험·분류 의미를 관리한다.

주요 모델:

- `Tag`

### accounts

인증, 프로필, 직접 선언한 선호를 담당한다.

주요 모델:

- `User`
- `UserProfile`
- `UserPreferredRegion`
- `UserPreferredTag`
- `UserPreferredPurpose`

핵심 규칙:

- 로그인 식별자는 이메일이다.
- `User.USERNAME_FIELD`와 실제 manager/serializer 구현을 이메일 기준으로 유지한다.
- `User`에 기본 지역이나 현재 좌표를 저장하지 않는다.
- Frontend 문서의 구형 username 예시를 근거로 User 모델을 변경하지 않는다.

### media_assets

공식 이미지, 시스템 기본 이미지와 라이선스·fallback 규칙을 담당한다.

주요 모델:

- `MediaAsset`
- `DefaultMediaAssetRule`

### libraries

도서관 canonical identity, 별칭, 외부 코드, 운영시간, 휴관, 공휴일, 운영표, 통계, 시설, 태그, 이미지를 담당한다.

주요 모델:

- `Library`
- `LibraryAlias`
- `LibraryExternalIdentifier`
- `LibraryOpeningHour`
- `LibraryClosureRule`
- `PublicHolidayCalendar`
- `PublicHoliday`
- `LibraryDailySchedule`
- `LibraryStatisticSnapshot`
- `LibraryFacilityProfile`
- `LibraryTag`
- `LibraryImage`

도서관 관계의 기준은 내부 `Library.id`다.

### books

책 메타데이터, KDC 태그, 소장 관계와 인기 스냅샷을 담당한다.

주요 모델:

- `Book`
- `BookTag`
- `LibraryHolding`
- `PopularBookSnapshot`
- `PopularBookItem`

전체 장서를 사전 적재하지 않는다.

### programs

문화 프로그램, 상태, 분류, 대상과 이미지 연결을 담당한다.

주요 모델:

- `Program`
- `ProgramTag`
- `ProgramImage`

서비스 내부 신청·예약·결제·참여 이력은 범위가 아니다.

### recommendations

방문 목적, 홈 공개 테마, 일일 추천 규칙과 결과를 담당한다.

주요 모델:

- `Purpose`
- `PurposeTagRule`
- `PurposeMetricRule`
- `DailyRecommendationTheme`
- `DailyRecommendationMetricRule`
- `DailyRecommendationTagRule`
- `DailyLibraryRecommendationSet`
- `DailyLibraryRecommendationItem`

홈 공개 테마는 `study`, `book`, `kids`, `mood`, `nearby`다.

### community

후기, 조회수, 좋아요, 관련 책·프로그램과 태그를 담당한다.

주요 모델:

- `UserReview`
- `UserReviewLike`
- `UserReviewImage`
- `ReviewBookReference`
- `ReviewProgramReference`
- `ReviewTag`

후기 저장 모델은 만들지 않는다. 후기 이미지 모델이 존재하더라도 현재 공개 업로드 API가 없으면 Frontend 업로드 기능은 보류한다.

### myoutings

저장한 도서관·책·프로그램을 담당한다.

주요 모델:

- `UserLibrarySave`
- `UserBookSave`
- `UserProgramSave`

좋아요한 후기는 `community.UserReviewLike`에서 조회한다.

### preferences

행동 기반 자동 성향 상태와 태그 점수를 담당한다.

주요 모델:

- `UserPreference`
- `UserPreferenceItem`

현재 통합 Dashboard API가 공개되지 않았다면 Frontend에는 목록형 나의 나들이만 제공한다.

### integrations

외부 API client, loader, normalizer, import와 동기화 실행 이력을 담당한다.

주요 모델:

- `SourceSyncRun`

미매칭·오류·merge 후보는 도메인 행의 검수 상태가 아니라 report, 구조화 로그, 관리 명령 출력으로 관리한다.

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

교차 앱 FK는 문자열 참조를 사용한다. 사용자 FK는 `settings.AUTH_USER_MODEL`을 사용한다.

## 6. 권장 migration 순서

1. `common`
2. `accounts.0001`: `User`, `UserProfile`, `UserPreferredRegion`
3. `tags.0001`, `media_assets.0001`
4. `libraries.0001`
5. `books.0001`, `programs.0001`, `recommendations.0001`
6. `accounts.0002`: `UserPreferredTag`, `UserPreferredPurpose`
7. `community.0001`, `myoutings.0001`, `preferences.0001`, `integrations.0001`

기존 migration이 이미 생성되었다면 이 목록을 근거로 재작성하지 않는다. 실제 migration graph를 우선 확인한다.

## 7. Django 설정 기준

```python
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
```

DRF 인증·permission·pagination 설정은 실제 settings를 우선한다. 문서 예시를 근거로 운영 설정을 덮어쓰지 않는다.

## 8. 환경변수

### Backend

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost
DATABASE_URL=
REDIS_URL=

GMS_API_KEY=
GMS_OPENAI_BASE_URL=https://gms.ssafy.io/gmsapi/api.openai.com/v1

DATA4LIBRARY_API_KEY=
DATA4LIBRARY_BASE_URL=http://data4library.kr/api

DATA_GO_KR_API_KEY=
PUBLIC_HOLIDAY_API_BASE_URL=http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService
PUBLIC_HOLIDAY_API_OPERATION=getRestDeInfo

LIBRARY_STANDARD_DATA_FILE=
LIBRARY_IMAGE_DATA_FILE=
LIBRARY_FACILITY_DATA_FILE=
PROGRAM_DATA_FILE=

SERVICE_DEFAULT_SIDO=부산광역시
SERVICE_DEFAULT_REGION_CODE=21
```

추가 추천·캐시·업로드 변수는 Django 명세 v4.0과 실제 `.env.example`을 따른다.

### Frontend

```dotenv
VITE_API_BASE_URL=
VITE_KAKAO_MAP_JAVASCRIPT_KEY=
```

- `VITE_KAKAO_MAP_JAVASCRIPT_KEY`는 브라우저 지도 SDK용 공개 키다.
- Kakao Developers에서 허용 도메인을 제한한다.
- 서버 비밀키는 `VITE_` 변수로 만들지 않는다.
- `.env`는 Git에 포함하지 않고 `.env.example`에는 변수명만 둔다.

## 9. 외부 API

### 정보나루

Django Backend에서 호출한다.

현재 또는 장기 설계에서 사용하는 API:

- `libSrch`
- `srchBooks`
- `loanItemSrch`
- `srchDtlList`
- `recommandList?type=reader`
- `libSrchByBook`
- 필요 시 `loanItemSrchByLib`

부산 지역은 `region=21`을 사용하고 가능한 경우 `format=json`을 명시한다.

### 공휴일 API

Django Backend에서 `getRestDeInfo`를 사용한다. 1~12월 수집이 모두 성공한 연도만 완전한 달력으로 처리한다.

### GMS

Django Backend에서만 호출한다.

허용:

- 비사실성 설명 문구 보조
- 사용자 친화적 문장 생성

금지:

- 추천 순위 결정
- 사실 필드 생성
- 시설·운영 여부 판단

### Kakao Map

Frontend에서 Kakao Map JavaScript SDK를 직접 호출한다.

- 변수: `VITE_KAKAO_MAP_JAVASCRIPT_KEY`
- 사용 위치: 도서관 상세
- 입력 데이터: `Library.name`, `road_address`, `latitude`, `longitude`
- 좌표가 없으면 SDK를 호출하지 않는다.

## 10. 현재 공개 API

현재 Endpoint, HTTP Method, Request·Response, Error 계약은 다음 문서만 따른다.

- `library_outing_frontend_api_contract_v4.0.md`

본 문서에 Endpoint 목록을 중복 작성하지 않는다. Django 명세의 API 예시는 장기 설계 참고이며 현재 공개 주소로 사용하지 않는다.

### 인증 계약 주의

프론트 전달용 API 계약의 구형 인증 예시에 `username`이 남아 있더라도 현재 Django 로그인 식별자는 이메일이다. 인증 연결 전에 현재 serializer와 API 테스트를 확인하고 계약 문서를 갱신한다. User 모델을 username 기반으로 변경하지 않는다.

## 11. Frontend 구조

Frontend 디렉터리, Route, Store, Service, DTO, Component와 UI/UX는 다음 문서를 따른다.

- `library_outing_frontend_spec_v4.0.md`

본 문서에 Frontend Route나 폴더 구조를 복제하지 않는다.

현재 API 응답에 없는 `is_saved`, `is_liked`, `moderation_status`를 있다고 가정하지 않는다. 저장·좋아요 초기 상태는 Frontend 명세의 `interactionStore` hydration 전략을 따른다.

## 12. 현재 구현 범위와 장기 범위

### 현재 Frontend 활성 범위

- 이메일 기반 JWT 인증과 refresh Cookie
- 홈 추천 응답 표시
- 도서관 기본 목록·상세
- Kakao 지도
- 책 검색·상세·소장 도서관
- 프로그램 목록·상세
- 도서관·책·프로그램 저장
- 후기 JSON CRUD와 좋아요
- 선호 설정
- 나의 나들이 목록

### 현재 Frontend 보류 범위

- 후기 이미지 업로드
- 통합 나의 나들이 Dashboard
- 행동 기반 성향 분석
- 정밀 운영 상태와 고급 필터
- 인기 도서
- 비슷한 도서관
- hidden 후기 UI
- 프로필 이미지·자기소개
- 실시간 좌석·대출 상태
- 내부 프로그램 신청

Backend는 장기 기능을 계속 구현할 수 있다. 다만 현재 API 계약에 추가되기 전에는 Frontend 활성 기능으로 취급하지 않는다.

## 13. import / fixture 정책

사용 데이터:

- 부산 도서관 표준 데이터 JSON
- 도서관 시설 데이터 JSON
- 도서관 외관 이미지 CSV 또는 JSON
- 문화 프로그램 JSON
- 공휴일 API
- 정보나루 API

외부 `library_name`은 FK로 사용하지 않는다.

```text
원천 파일/API
→ normalize
→ Library exact match
→ LibraryAlias match
→ 검수된 correction map
→ Library.id 확정
→ upsert
```

모호한 데이터는 자동 연결하지 않고 report에 남긴다. import는 idempotent하게 작성한다.

## 14. 테스트 우선순위

1. 이메일 로그인·refresh Cookie·로그아웃
2. 모델 생성과 실제 migration graph
3. 도서관 import 매칭
4. 시설 nullable boolean 처리
5. 공휴일 complete와 운영표 계산
6. 홈 추천 후보와 공개 API 범위
7. 후기 작성 검증
8. 후기 좋아요 idempotent 처리
9. 저장·좋아요 hydration
10. 외부 API 오류와 정상 빈 결과 구분
11. Kakao 지도 fallback
12. 태그 의미 분리
13. GMS 실패 fallback

## 15. 작업 우선순위

작업 우선순위는 현재 이슈와 구현 상태를 먼저 확인한다. 과거 단계별 목록을 그대로 재실행하지 않는다.

일반 원칙:

1. 실제 코드·migration·테스트 상태 확인
2. 현재 API 계약 공백 확인
3. 작은 단위 구현 또는 수정
4. 관련 테스트 실행
5. 문서와 실제 구현 차이 보고

## 16. README에 포함할 내용

- 프로젝트 소개와 문제 정의
- 주요 기능과 현재 보류 기능
- 기술 스택
- 데이터 출처
- API Key 설정 방법
- 실행 방법
- migration·fixture/import 방법
- 추천 알고리즘 설명
- GMS와 Kakao Map 사용 경계
- 구현 한계와 향후 개선점

Git 협업 방식은 사용자가 별도로 관리하며, Codex가 임의로 작성하거나 변경하지 않는다.
