# 도서관 나들이 코드 리딩 노트

이 문서는 학습용 코드 읽기를 돕기 위한 해설이다. 기준은 실제 저장소 코드, `library_outing_frontend_api_contract_v2.0.md`, `library_outing_Django_spec_v3.md`, `library_outing_ERD_v3.md`, `library_outing_frontend_spec_v3.md`, `README.md`, `AGENTS.md`다. 기능 동작, API 계약, 모델, migration, serializer, view의 의미를 바꾸지 않는다.

## 1. 프로젝트 전체 구조

루트에는 실행·시연 설명인 `README.md`, Codex 작업 기준인 `AGENTS.md`, 기술 스택 요약인 `SKILLS.md`, API 계약과 Django/Frontend/ERD 명세가 있다.

`backend/`는 Django REST API다. `backend/config/urls.py`에서 `/api/v1/` 아래에 앱별 URL을 연결하고, `backend/config/settings.py`에서 앱, JWT, CORS, media, 외부 API, GMS 환경변수를 읽는다. 실제 앱 코드는 `backend/apps/` 아래에 도메인별로 있다.

`frontend/`는 Vue 3 SPA다. `frontend/src/router/index.js`가 화면 route와 인증 guard를 담당하고, `frontend/src/services/`가 Axios API 호출을 캡슐화한다. `frontend/src/stores/`는 Pinia 상태, `frontend/src/pages/`는 route 단위 화면, `frontend/src/components/`는 재사용 UI다.

`fixtures/`에는 도서관, 도서, 프로그램, 공휴일, 데모 활동 데이터가 있고, `backend/db.sqlite3`는 로컬 개발 DB 파일이다. `.env`는 읽거나 수정하지 않는다.

## 2. 백엔드 앱별 역할

`accounts`는 이메일 기반 사용자, 프로필, 직접 선택한 선호 목적·지역·태그를 다룬다. `User.username = None`, `USERNAME_FIELD = "email"`이며, 로그인 serializer도 email 값을 인증에 사용한다.

`libraries`는 도서관 canonical 데이터, 운영시간, 휴관 규칙, 일일 운영표, 시설 profile, 통계, 이미지, 비슷한 도서관 계산을 맡는다. 시설은 명시적 `True`, 명시적 `False`, `NULL`, profile 행 부재를 구분한다.

`books`는 로컬 책 데이터, 인기 도서 스냅샷, 정보나루 책 검색과 소장 도서관 조회를 다룬다. 외부 검색 결과는 `Data4LibraryClient`를 통해 가져오고 필요한 책은 로컬에 upsert한다.

`programs`는 문화 프로그램 목록·상세와 필터를 담당한다. 실제 코드에서는 `is_visible=True`, `deleted_at__isnull=True`인 프로그램만 조회한다.

`community`는 후기, 댓글, 좋아요, 관련 책·프로그램, 후기 태그를 맡는다. `UserReviewLike`가 좋아요 원본 관계이고 `like_count`는 집계 캐시다. 상세 조회는 `view_count`를 DB에서 직접 증가시킨다.

`myoutings`는 도서관·책·프로그램 저장 목록, 작성 후기, 좋아요한 후기, 대시보드 응답을 제공한다. 저장 생성·삭제 후에는 성향 재계산 상태를 commit 이후 pending으로 예약한다.

`preferences`는 행동 기반 성향 집계를 계산한다. 저장한 도서관·책·프로그램, 작성 후기, 좋아요한 후기를 신호로 사용하고, 365일 관측창과 90일 반감기 기반 최근성 가중치를 적용한다.

`recommendations`는 홈 오늘의 추천, 공개 테마 추천, 개인화 추천을 만든다. 홈 공개 테마 코드는 `study`, `book`, `kids`, `mood`, `nearby`다.

`integrations`는 정보나루, 공휴일 API, GMS 같은 외부 연동을 감싼다. GMS는 성향 요약 문장을 다듬는 보조 단계다.

## 3. 프론트엔드 주요 디렉터리와 파일 역할

`frontend/src/main.js`는 Vue 앱, Pinia, router, Bootstrap, 전역 CSS를 연결한다.

`router/index.js`는 공개 route와 회원 route를 정의한다. `requiresAuth` route 진입 시 `authStore.bootstrapSession()`을 먼저 시도하고, 인증 실패 시 내부 `redirect` query와 함께 로그인 화면으로 보낸다.

`services/apiClient.js`는 Axios 인스턴스다. access token을 `Authorization: Bearer`로 붙이고, 401 응답을 받으면 refresh를 한 번 시도한 뒤 원 요청을 재시도한다. 동시에 여러 요청이 401을 받아도 하나의 refresh promise를 공유한다.

`stores/auth.js`는 access token, 사용자, bootstrap 상태를 관리한다. refresh token은 HttpOnly cookie이므로 JS에서 직접 읽지 않고 `/auth/token/refresh/`를 호출한다.

`stores/interaction.js`는 저장한 도서관 id, 저장한 책 ISBN, 저장한 프로그램 id, 좋아요한 후기 id를 Set으로 관리한다. 개별 카드 응답에 `is_saved`, `is_liked`가 없기 때문에 나의 나들이 목록을 호출해 초기 상태를 hydration한다.

`utils/query.js`의 `cleanParams`는 서비스별 허용 query key만 남겨 API 계약에 없는 query가 나가지 않도록 돕는다.

## 4. 요청 흐름

일반 조회 흐름은 다음과 같다.

```text
Vue page/component
→ frontend/src/services/*Service.js
→ apiClient
→ Django URLConf
→ APIView 또는 DRF generic view
→ serializer/service/model
→ JSON response
→ page/store 상태 반영
```

예를 들어 도서관 목록은 `LibraryListView.vue`에서 `libraryService.fetchLibraries()`를 호출하고, 서비스는 `GET /libraries/`에 허용 query만 보낸다. Django는 `LibraryListAPIView`에서 queryset을 만들고 `apply_advanced_library_filters()`로 시설·운영·목적 점수 필터를 적용한 뒤 `LibraryListSerializer`로 응답한다.

## 5. 인증 흐름: signup/login/refresh/logout/me

회원가입은 `POST /api/v1/auth/signup/`이다. `SignupSerializer`가 email 중복과 password validation을 확인하고, 사용자·프로필·성향 row를 transaction 안에서 만든다. 응답 body에는 `access`와 `user`가 내려가고 refresh token은 cookie로 설정된다.

로그인은 `POST /api/v1/auth/login/`이다. 요청 필드는 `email`, `password`다. 코드에서 `authenticate(username=attrs["email"])` 형태를 쓰지만 현재 User의 `USERNAME_FIELD`가 email이므로 username 로그인을 도입한 것이 아니다.

refresh는 `POST /api/v1/auth/token/refresh/`다. 서버는 `library_outing_refresh` cookie에서 refresh token을 읽고 유효한 active user이면 새 access token만 body로 반환한다.

logout은 `POST /api/v1/auth/logout/`이다. 서버는 refresh cookie를 삭제하고 프론트는 `clearSession()`으로 access token, user, interaction store를 초기화한다.

내 정보는 `GET/PATCH /api/v1/users/me/`다. `MeUpdateSerializer`는 nickname, bio, profile image 관련 필드를 부분 수정한다.

## 6. 도서관 목록/상세 흐름

도서관 API는 `/api/v1/libraries/`, `/api/v1/libraries/{library_id}/`, `/api/v1/libraries/{library_id}/similar/`이다.

목록 queryset은 active 도서관만 대상으로 하고, 시설 profile, 현재 통계, 썸네일 이미지, 운영시간, 휴관 규칙, 필요한 날짜의 일일 운영표, 활성 태그를 미리 가져온다.

시설 필터는 `has_wifi=true` 같은 명시적 true query만 허용한다. 이는 `NULL`이나 profile 행 부재를 시설 없음으로 해석하지 않기 위한 구현이다.

운영 상태는 `open_today`와 `open_now`를 나누어 응답한다. 일일 운영표가 있으면 그것을 우선하고, 없으면 휴관 규칙과 요일별 운영시간에서 계산한다. `00:00~00:00`은 24시간 운영으로 확정하지 않고 시간 미상처럼 처리한다.

비슷한 도서관은 저장 테이블 없이 요청 시 계산한다. 지역·도서관 유형, 명시적 True 시설, 활성 태그, 목적별 점수 벡터를 비교한다.

## 7. 책 검색/인기 도서/소장 도서관 흐름

책 목록은 `GET /api/v1/books/`로 로컬 `Book` 중 active 항목을 반환한다.

인기 도서는 `GET /api/v1/books/popular/`다. `PopularBookSnapshot` 중 region 기준 최신 snapshot을 고르고 rank 순서로 item을 반환한다. snapshot이 없으면 오류가 아니라 `snapshot: null`, `items: []`를 반환한다.

책 검색은 `GET /api/v1/books/search/`다. 검색 조건이 없으면 400을 반환한다. 정보나루 API key가 없으면 503, 외부 요청 실패는 502다. 성공 시 외부 결과를 로컬 책으로 upsert하고, 외부 결과와 로컬 id를 함께 직렬화한다.

소장 도서관은 `GET /api/v1/books/{isbn13}/libraries/`다. 부산 region `21` 기준으로 정보나루 소장 도서관을 조회하고 직렬화한다.

## 8. 문화 프로그램 목록/상세 흐름

문화 프로그램은 `/api/v1/programs/`, `/api/v1/programs/{program_id}/`로 조회한다. 조회 대상은 `is_visible=True`이고 `deleted_at`이 없는 프로그램이다.

목록 필터는 검색어, `library_id`, `sigungu`, `category`, `target`, `application_status`, `operation_status`를 사용한다. 정렬은 `title`, `library__name`, `-post_date`만 허용한다.

프론트는 `programService`에서 허용 query만 보내고, 상세 화면은 프로그램의 개최 도서관과 태그 정보를 표시한다.

## 9. 커뮤니티 후기/좋아요/조회수 흐름

후기 목록은 `GET /api/v1/reviews/`이고 visible 후기만 반환한다. 검색어는 후기 본문과 도서관명에 적용되고, tag filter는 comma string을 split하여 각 tag code를 모두 만족하도록 적용한다.

후기 작성은 `POST /api/v1/reviews/`이며 인증이 필요하다. `UserReviewWriteSerializer`가 검증과 저장을 담당한다. 작성 후에는 사용자 성향 재계산 상태가 pending으로 예약된다.

후기 상세 `GET /api/v1/reviews/{review_id}/`는 조회수를 `F("view_count") + 1`로 증가시킨 뒤 최신 row를 다시 읽어 응답한다.

좋아요는 `POST/DELETE /api/v1/reviews/{review_id}/like/`다. 생성은 `get_or_create`로 idempotent하게 처리하고, 생성된 경우에만 `like_count`를 증가시킨다. 삭제는 관계가 실제로 삭제된 경우에만 `like_count`를 감소시킨다.

댓글은 `/reviews/{review_id}/comments/` 아래에서 목록, 생성, 수정, 삭제가 가능하다. 수정·삭제는 작성자만 허용한다.

## 10. 나의 나들이와 성향 분석 흐름

저장은 도서관·책·프로그램 세 대상만 있다. 각 저장 API는 `BaseSaveAPIView`를 상속해 target 조회, `get_or_create`, delete, 공통 응답을 재사용한다.

나의 나들이 목록 API는 저장한 도서관, 책, 프로그램, 내가 쓴 후기, 좋아요한 후기, 내가 쓴 댓글을 페이지네이션으로 반환한다. 프론트의 interaction store는 저장/좋아요 초기 상태를 이 목록으로 맞춘다.

대시보드 `GET /api/v1/my-outings/dashboard/`는 `ensure_user_preference_current()`로 성향 결과를 준비한 뒤 `build_my_outings_dashboard()`로 profile summary, activity summary, preference summary, 4축 비율, summary sentence, 분석 근거를 반환한다.

성향 분석은 저장한 도서관의 지역·명시적 True 시설, 저장한 책의 태그/KDC, 저장한 프로그램 카테고리, 작성·좋아요한 후기의 태그와 관련 책·프로그램을 사용한다. 좋아요한 후기 중 내가 쓴 후기는 dashboard 행동 liked review 계산에서 제외된다.

## 11. 추천 기능 흐름

홈 추천 API는 `GET /api/v1/home/`이다. 응답은 오늘의 추천, 테마 추천, 개인화 추천 세 묶음이다.

오늘의 추천은 해당 날짜의 `DailyLibraryRecommendationSet`이 있으면 저장된 세트를 먼저 사용한다. 없으면 활성 `DailyRecommendationTheme` 목록에서 날짜 ordinal 기준으로 하나를 골라 후보 도서관을 점수화한다.

테마 추천은 `HOME_PURPOSE_CODES = ("study", "book", "kids", "mood", "nearby")` 순서로 만든다. `nearby`는 좌표가 있을 때 거리 역수를 쓰고, 좌표가 없으면 좌표 보유 여부만 점수화한다.

개인화 추천은 로그인 사용자의 직접 선호 목적·지역·태그와 행동 기반 성향 tag score를 결합한다. 직접 선호와 행동 성향은 원본 데이터를 섞어 저장하지 않고 추천 점수 계산에서만 가중 결합한다.

## 12. 외부 API와 GMS 사용 경계

정보나루 API는 책 검색과 소장 도서관 조회에 사용된다. `DATA4LIBRARY_API_KEY`가 없으면 관련 API는 503을 반환한다. 외부 API 실패는 정상 빈 결과와 구분해 502로 응답한다.

data.go.kr 공휴일 API는 공휴일 데이터 수집에 쓰인다. API key는 `DATA_GO_KR_API_KEY`이며 서버 전용이다.

GMS는 `apps.integrations.gms.enhance_summary_sentence()`에서만 확인했다. `GMS_SUMMARY_ENABLED`, `GMS_API_KEY`, `GMS_OPENAI_BASE_URL`, `GMS_MODEL`이 모두 있어야 호출한다. 실패하거나 응답 문장이 검증을 통과하지 못하면 규칙 기반 문장을 그대로 사용한다.

GMS 요청 payload는 top axis, top labels, signal count, rule sentence로 제한된다. 추천 후보, 추천 점수, 추천 순위, 도서관 운영 여부, 시설 정보, 책·프로그램 사실 판단에는 사용하지 않는다.

## 13. 환경변수 사용 위치와 보안 주의점

Backend `.env.example`의 `DJANGO_SECRET_KEY`, `DATA4LIBRARY_API_KEY`, `DATA_GO_KR_API_KEY`, `GMS_API_KEY`는 서버 전용이다. 실제 값은 `.env`에만 넣고 프론트 코드, 문서, 로그에 남기지 않는다.

`DATABASE_URL`은 DB 연결 설정이고, 없으면 SQLite `backend/db.sqlite3`를 사용한다.

`CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `CSRF_TRUSTED_ORIGINS`는 Vue 개발 서버와 Django API가 cookie를 주고받기 위한 설정이다.

`JWT_REFRESH_COOKIE_*`는 refresh token cookie 속성이다. refresh token은 HttpOnly cookie로 관리되고, access token은 응답 body와 프론트 메모리 상태에 있다.

Frontend `.env.example`의 `VITE_API_BASE_URL`과 `VITE_REQUEST_TIMEOUT_MS`는 공개 설정이다. `VITE_KAKAO_MAP_JAVASCRIPT_KEY`는 Kakao Map JavaScript SDK용 공개 식별자이며, Kakao REST API Key/Admin Key와 다르다. Kakao Developers에서 허용 도메인을 제한해야 한다.

## 14. null/false/빈 배열/미수집 상태 구분

`LibraryFacilityProfile.has_* = True`는 시설 존재가 명시적으로 확인된 상태다. `False`는 원천이 부재를 명시한 상태다. `NULL`은 해당 필드가 확인되지 않은 상태다. profile 행 부재는 그 도서관의 시설 데이터 자체가 미수집된 상태다.

도서관 통계의 `book_count = null`과 `book_count = 0`은 다르다. serializer는 현재 통계 snapshot이 없으면 `book_count`, `reading_seat_count`를 `null`로 응답한다.

운영 상태의 `open_today = null` 또는 `open_now = null`은 알 수 없다는 뜻이다. `false`는 닫힘이 확인된 상태다.

목록 응답의 빈 배열은 정상 빈 결과일 수 있다. 예를 들어 인기 도서 snapshot이 없을 때 `items: []`를 반환한다. 반면 외부 API key 미설정이나 외부 요청 실패는 503/502로 구분한다.

`is_saved`, `is_liked` 필드는 카드 응답에 의존하지 않는다. 프론트는 나의 나들이 목록으로 상태를 hydration한다.

## 15. 발표나 Q&A에서 설명할 만한 기술 포인트

이메일 기반 인증을 Django `AbstractUser` 위에서 구현하면서 `username` 필드를 제거했고, refresh token은 HttpOnly cookie로 분리했다.

Axios interceptor는 access token 만료 시 refresh를 1회만 시도하고 원 요청을 재시도한다. 동시 401 상황에서는 refresh promise를 공유해 중복 refresh 요청을 줄인다.

시설 데이터는 `True`, `False`, `NULL`, 행 부재를 구분한다. 이는 “미수집”을 “없음”으로 잘못 말하지 않기 위한 도메인 안전장치다.

후기 좋아요는 관계 테이블을 원본으로 두고 `like_count`를 캐시로 관리한다. 생성·삭제 여부에 따라 카운터를 원자적으로 갱신한다.

성향 분석은 행동 원본을 남겨두고 계산 결과만 `UserPreferenceItem`으로 재생성한다. transaction commit 이후 pending으로 예약해 rollback된 행동이 성향 상태를 바꾸지 않게 한다.

추천은 규칙 기반 점수 계산이다. GMS는 이미 계산된 성향 요약 문장을 다듬는 단계에만 쓰이며, 후보 선정이나 사실 판단을 하지 않는다.

외부 API 실패는 정상 빈 결과와 구분한다. 정보나루 key 미설정은 503, 외부 요청 실패는 502다.

대체 이미지는 엔터티 이미지 관계에 삽입하지 않고 serializer에서 fallback payload로 만든다. 같은 도서관은 id/name 기반 hash로 안정적인 placeholder를 받는다.
