# 도서관 나들이

SSAFY 1학기 관통 프로젝트 **도서관 나들이** 저장소입니다.

이 README는 새 컴퓨터에서 백엔드 API를 재현하고 시연하기 위한 실행 가이드입니다. 현재 최종 프론트 API 계약은 `library_outing_frontend_api_contract_v2.0.md`를 기준으로 합니다.

## 1. 환경

- Python 3.11.9 기준
- Django REST API base URL: `/api/v1`
- 로컬 DB: SQLite `backend/db.sqlite3`
- 사용자 업로드 파일: `backend/media/`

## 2. 백엔드 실행 준비

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Python 실행 파일 이름이 환경마다 다르면 `python3.11` 대신 설치된 Python 3.11.9 경로를 사용합니다.

## 3. `.env` 필요 변수

`.env` 파일은 `backend/.env`에 둡니다. 실제 key, token, secret 값은 README나 커밋에 적지 않습니다.

현재 settings에서 읽는 변수:

```text
JWT_REFRESH_COOKIE_SECURE
JWT_REFRESH_COOKIE_SAMESITE
MEDIA_MAX_UPLOAD_MB
DATA4LIBRARY_API_KEY
DATA4LIBRARY_BASE_URL
DATA_GO_KR_API_KEY
PUBLIC_HOLIDAY_API_BASE_URL
PUBLIC_HOLIDAY_API_OPERATION
PUBLIC_HOLIDAY_API_NUM_OF_ROWS
GMS_API_KEY
GMS_OPENAI_BASE_URL
GMS_MODEL
GMS_SUMMARY_ENABLED
GMS_TIMEOUT_SECONDS
```

운영/배포 분리 권장 변수:

```text
SECRET_KEY
```

외부 API 관련 주의:

- `DATA4LIBRARY_API_KEY`: 정보나루 책 검색, 소장 도서관, 인기 도서 import에 필요합니다.
- `DATA_GO_KR_API_KEY`: 공공데이터 공휴일 동기화에 필요합니다.
- `GMS_API_KEY`: 나의 나들이 `summary_sentence` 표현 보조에만 사용합니다.
- GMS가 없어도 핵심 API는 동작합니다. `GMS_SUMMARY_ENABLED=false` 또는 key 없음이면 규칙 기반 문장을 반환합니다.
- 서버 secret/API key는 프론트로 전달하지 않습니다.
- Kakao Map JavaScript Key만 프론트 공개 환경변수로 사용할 수 있습니다.

## 4. DB 초기화

```bash
cd backend
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py seed_service_defaults
```

## 5. Fixture loaddata 순서

아래 순서를 기준으로 로딩합니다.

```bash
python manage.py loaddata fixtures/library_seed/standard_library_data.json
python manage.py loaddata fixtures/library_seed/library_facilities.json
python manage.py loaddata fixtures/library_seed/library_images.json

python manage.py loaddata fixtures/book_seed/popular_books_import_2026_06_pages2.json
python manage.py loaddata fixtures/book_seed/books_popular_enriched_2026_06_24.json
python manage.py loaddata fixtures/book_seed/book_enrich_import_2026_06_24_budget350.json

python manage.py loaddata fixtures/program_seed/busan_programs_2026_05_31_2026_06_30.json
python manage.py loaddata fixtures/library_identifier_seed/data4library_identifiers_page1_fixture.json

python manage.py loaddata fixtures/public_holiday_seed/public_holidays_2026.json
python manage.py loaddata fixtures/daily_schedule_seed/library_daily_schedules_2026.json.gz
```

참고:

- `SourceSyncRun` 실행 로그는 fixture 대상이 아닙니다.
- `LibraryDailySchedule`은 파생 데이터지만, 시연 재현성을 위해 gzip fixture를 제공합니다.
- `program_seed`의 dry-run/report JSON은 로딩 대상이 아닙니다.

## 6. 운영 command

### 서비스 기본값 seed

```bash
python manage.py seed_service_defaults
```

목적, 태그, 추천 테마 등 서비스 기본 데이터를 생성합니다.

### 공휴일 동기화

```bash
python manage.py sync_public_holidays --year 2026
python manage.py sync_public_holidays --start-year 2026 --end-year 2027
```

옵션이 없으면 현재 연도와 다음 연도를 동기화합니다. 12개월 모두 성공한 연도만 complete calendar로 취급합니다.

### 일자별 운영표 생성

```bash
python manage.py build_library_daily_schedules --year 2026 --dry-run
python manage.py build_library_daily_schedules --year 2026
python manage.py build_library_daily_schedules --year 2026 --library-id 1
python manage.py build_library_daily_schedules --start-date 2026-01-01 --end-date 2026-12-31
```

complete calendar 연도만 생성할 수 있습니다. 재실행해도 `(library, date)` 기준으로 중복 생성되지 않습니다.

### 정보나루 도서관 식별자 import

```bash
python manage.py import_data4library_identifiers --region 21 --dry-run
python manage.py import_data4library_identifiers --region 21
```

정보나루 API key가 필요합니다. 시연용 fixture를 사용하면 외부 API 호출 없이 도서관 식별자 관계를 재현할 수 있습니다.

### 행동 기반 성향 rebuild

```bash
python manage.py rebuild_user_preferences --user-id 1
python manage.py rebuild_user_preferences --all
```

저장/후기/좋아요 행동 데이터를 기반으로 `UserPreference`와 `UserPreferenceItem`을 재계산합니다. API 요청 시 lazy rebuild도 수행됩니다.

### 인기 도서 import

```bash
python manage.py import_popular_books --start-date 2026-06-01 --end-date 2026-06-07 --region 21 --max-pages 1
python manage.py enrich_book_details --source popular --limit 80
```

정보나루 API key가 필요합니다. 시연용 fixture를 사용하면 외부 API 호출 없이 인기 도서 API를 재현할 수 있습니다.

### 프로그램 import

```bash
python manage.py import_busan_programs --start-date 2026-05-31 --end-date 2026-06-30
```

시연용 fixture를 사용하면 import command 없이 프로그램 목록을 재현할 수 있습니다.

## 7. 서버 실행

```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

기본 주소:

```text
http://127.0.0.1:8000/api/v1/
```

DEBUG 환경에서는 `backend/media/` 업로드 파일이 `/media/` URL로 제공됩니다.

## 8. Smoke test 순서

### 8.1 인증

```http
POST /api/v1/auth/signup/
POST /api/v1/auth/login/
POST /api/v1/auth/token/refresh/
GET /api/v1/users/me/
PATCH /api/v1/users/me/
POST /api/v1/auth/logout/
```

확인:

- 로그인 식별자는 email입니다.
- access token은 body, refresh token은 HttpOnly Cookie입니다.
- 기존 `id`, `email`, `nickname` 필드와 `profile` 확장을 확인합니다.

### 8.2 도서관

```http
GET /api/v1/libraries/
GET /api/v1/libraries/?purpose=study
GET /api/v1/libraries/?purpose=nearby&lat=35.1&lng=129.0
GET /api/v1/libraries/?has_wifi=true
GET /api/v1/libraries/?min_book_count=10000
GET /api/v1/libraries/?open_today=true
GET /api/v1/libraries/?open_now=true
GET /api/v1/libraries/?weekend_open=true
GET /api/v1/libraries/?holiday_status=open&holiday_date=2026-01-01
GET /api/v1/libraries/1/
GET /api/v1/libraries/1/similar/?limit=3
```

확인:

- invalid query는 조용히 무시하지 않고 400을 반환합니다.
- `open_today`, `open_now`의 `null`은 unknown입니다.
- `holiday_operation_status`는 holiday query가 있을 때만 포함됩니다.

### 8.3 책

```http
GET /api/v1/books/
GET /api/v1/books/popular/
GET /api/v1/books/popular/?limit=1000
GET /api/v1/books/search/?search_type=title&q=파이썬
GET /api/v1/books/{isbn13}/
GET /api/v1/books/{isbn13}/libraries/
```

확인:

- 인기 도서는 내부 snapshot만 사용합니다.
- `limit=1000`은 최대 50으로 cap 됩니다.
- 정보나루 key가 없으면 외부 검색/소장 API는 503을 반환할 수 있습니다.

### 8.4 프로그램

```http
GET /api/v1/programs/
GET /api/v1/programs/?library_id=1
GET /api/v1/programs/{id}/
```

### 8.5 후기

```http
GET /api/v1/reviews/
POST /api/v1/reviews/
GET /api/v1/reviews/{id}/
PATCH /api/v1/reviews/{id}/
POST /api/v1/reviews/{id}/like/
DELETE /api/v1/reviews/{id}/like/
DELETE /api/v1/reviews/{id}/
```

확인:

- 상세 GET에서만 `view_count`가 증가합니다.
- 목록, 수정, 삭제, like/unlike는 조회수를 증가시키지 않습니다.
- multipart `images` 업로드와 `replace_images=true` 교체/전체 삭제를 확인합니다.
- 허용 확장자는 `jpg`, `jpeg`, `png`, `webp`입니다.

### 8.6 나의 나들이

```http
GET /api/v1/my-outings/libraries/
GET /api/v1/my-outings/books/
GET /api/v1/my-outings/programs/
GET /api/v1/my-outings/reviews/
GET /api/v1/my-outings/liked-reviews/
GET /api/v1/my-outings/dashboard/
```

확인:

- dashboard는 `profile_summary`, `activity_summary`, `preference_summary`, `outing_type_summary`, `summary_sentence`, `analysis_basis`, `preference_status`를 반환합니다.
- 저장/후기/좋아요 변경 후 pending 상태가 lazy rebuild로 갱신될 수 있습니다.

### 8.7 홈 개인 추천과 GMS fallback

```http
GET /api/v1/home/
```

확인:

- 비로그인 또는 선호/행동 없음: `personal_recommendations.available=false`
- 수동 선호만 있음: personal 추천 가능
- 행동 신호만 있음: personal 추천 가능
- 수동 선호 + 행동 신호: 둘 다 반영
- GMS 비활성/key 없음/timeout/failure: dashboard `summary_sentence`는 규칙 기반 fallback

## 9. 커밋 제외 파일

다음 파일과 디렉터리는 커밋 대상이 아닙니다.

```text
.env
backend/.venv/
backend/db.sqlite3
backend/media/
__pycache__/
.DS_Store
```

루트에 제출 산출물 원본 PDF 같은 파일이 있을 수 있습니다. 백엔드/API 작업과 무관하면 수정, 삭제, add, commit하지 않습니다.

## 10. 문서

- 최종 API 계약: `library_outing_frontend_api_contract_v2.0.md`
- 기존 API 계약 기준선: `library_outing_frontend_api_contract_v1.1.md`
- Django 장기 명세: `library_outing_Django_spec_v3.md`
- ERD 장기 명세: `library_outing_ERD_v3.md`
- Frontend 명세: `library_outing_frontend_spec_v2.1.md`
- 디자인 기준: `DESIGN.md`

실제 구현과 문서가 다르면 실제 코드, migration, serializer, smoke 결과를 우선합니다.
