# 도서관 나들이 Frontend 개발 명세서 v3

- 문서 버전: 3.0
- 작성 기준일: 2026-06-25
- 대상 애플리케이션: Vue 3 SPA
- 연동 백엔드: Django REST API `/api/v1`
- 최상위 API 기준: `library_outing_frontend_api_contract_v2.0.md`
- 실행·시연 기준: `README.md`
- 페이지 구조 기준: `도서관 나들이 주요 페이지 구조.txt`
- 디자인 기준: `DESIGN.md`
- 도메인 참고: `library_outing_Django_spec_v3.md`, `library_outing_ERD_v3.md`

## 0. 문서 사용 규칙

### 0.1 목적

이 문서는 API 계약 v2.0 기준으로 도서관 나들이 프론트엔드의 최종 구현 범위, Route, Service, Store, DTO, UI 상태, 사용자 행동, 검증 기준을 정의한다.

v2.1 문서는 보존하되, v3 구현 판단은 이 문서를 우선한다.

### 0.2 판단 우선순위

문서나 구현이 충돌하면 다음 순서로 판단한다.

1. 검증된 현재 코드, migration, serializer, API 실행 결과
2. `library_outing_frontend_api_contract_v2.0.md`
3. `README.md`의 실행·fixture·smoke test 순서
4. `library_outing_Django_spec_v3.md`, `library_outing_ERD_v3.md`
5. 본 Frontend 명세 v3
6. `DESIGN.md`
7. 과거 명세와 목업

API 계약에 없는 Endpoint, Request, Response field는 프론트에서 만들지 않는다. 단, API v2.0에 추가된 기능은 더 이상 v2.1의 보류 항목으로 취급하지 않는다.

### 0.3 구현 경계

- Backend model, migration, serializer, view, URL을 프론트 작업 중 수정하지 않는다.
- 서버 secret/API key는 프론트에 노출하지 않는다.
- Kakao Map JavaScript Key만 `VITE_KAKAO_MAP_JAVASCRIPT_KEY`로 사용할 수 있다.
- GMS는 프론트에서 직접 호출하지 않는다.
- GMS는 `summary_sentence` 문장 표현 보조일 뿐 추천 후보, 순위, 점수, 운영/시설/책/프로그램 사실 판단에 쓰이지 않는다.
- 응답의 `null`, `false`, 빈 배열, 필드 부재를 같은 의미로 합치지 않는다.
- `is_saved`, `is_liked` 필드에 의존하지 않는다. 저장·좋아요 초기 상태는 나의 나들이 목록 hydration으로 보완한다.

## 1. 기술 스택과 프로젝트 구조

### 1.1 기술 스택

- Vue 3
- Vite
- Vue Router
- Pinia
- Axios
- Bootstrap 5.3
- Kakao Map JavaScript SDK

### 1.2 권장 Frontend 구조

```text
frontend/src/
├─ assets/styles/
│  ├─ tokens.css
│  ├─ base.css
│  ├─ bootstrap-overrides.css
│  └─ components.css
├─ components/
│  ├─ cards/
│  ├─ feedback/
│  ├─ media/
│  ├─ navigation/
│  └─ forms/
├─ pages/
│  ├─ home/
│  ├─ libraries/
│  ├─ books/
│  ├─ programs/
│  ├─ community/
│  ├─ myoutings/
│  ├─ preferences/
│  ├─ auth/
│  └─ profile/
├─ router/
├─ services/
├─ stores/
└─ utils/
```

### 1.3 CSS import 순서

```js
import 'bootstrap/dist/css/bootstrap.min.css'
import './assets/styles/tokens.css'
import './assets/styles/base.css'
import './assets/styles/bootstrap-overrides.css'
import './assets/styles/components.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
```

Bootstrap 기본 blue, 기본 focus ring, 기본 card 시각은 design token으로 override한다. Bootstrap `.card`에 전역 padding을 직접 주지 않는다.

## 2. 인증, 세션, 오류 처리

### 2.1 인증 API

| 기능 | Endpoint | Method | 비고 |
|---|---|---|---|
| 회원가입 | `/auth/signup/` | POST | email, password, nickname |
| 로그인 | `/auth/login/` | POST | email, password |
| 토큰 갱신 | `/auth/token/refresh/` | POST | refresh HttpOnly Cookie |
| 로그아웃 | `/auth/logout/` | POST | refresh Cookie 제거 |
| 내 정보 | `/users/me/` | GET | 인증 필요 |
| 내 정보 수정 | `/users/me/` | PATCH | JSON 또는 multipart |

로그인 식별자는 이메일이다. username 입력 UI를 만들지 않는다.

### 2.2 토큰 처리

- access token은 Pinia auth store 또는 메모리 상태에 보관한다.
- refresh token은 HttpOnly Cookie이며 프론트 JS가 직접 읽지 않는다.
- API 요청에는 `Authorization: Bearer {access}`를 붙인다.
- 401 발생 시 refresh를 1회 시도하고 원 요청을 1회 재시도한다.
- refresh 실패 시 인증 상태와 사용자별 store를 초기화하고 로그인 화면으로 이동한다.
- 로그인 후 복귀는 내부 `redirect` query만 허용한다.

### 2.3 Validation과 Error UX

- 400: field error를 form input 근처에 표시한다.
- 401: refresh 성공 시 사용자에게 별도 오류를 보이지 않는다.
- 403: 권한 없음 화면 또는 inline error.
- 404: 자원별 문구를 사용한다. 예: "후기를 찾을 수 없어요."
- 503: 외부 API 설정 누락/실패는 해당 영역만 오류 처리한다.
- 네트워크 오류와 정상 빈 결과를 구분한다.

### 2.4 공통 상태

모든 API 화면은 다음 상태를 가진다.

- loading
- empty
- error
- success

목록 empty는 오류가 아니다. 특히 프로그램, 후기, 저장 목록은 초기 데이터가 0건일 수 있다.

## 3. Route 표

| 이름 | Route | Page | 권한 |
|---|---|---|---|
| home | `/` | `HomeView` | 공개 |
| libraries | `/libraries` | `LibraryListView` | 공개 |
| library-detail | `/libraries/:id` | `LibraryDetailView` | 공개 |
| books | `/books` | `BookExploreView` | 공개 |
| book-detail | `/books/:isbn13` | `BookDetailView` | 공개 |
| programs | `/programs` | `ProgramListView` | 공개 |
| program-detail | `/programs/:id` | `ProgramDetailView` | 공개 |
| community | `/community` | `ReviewListView` | 공개 |
| review-detail | `/reviews/:id` | `ReviewDetailView` | 공개 |
| review-create | `/reviews/new` | `ReviewCreateView` | 회원 |
| review-edit | `/reviews/:id/edit` | `ReviewEditView` | 회원·작성자 UI |
| my-outings | `/my-outings` | redirect `/my-outings/dashboard` | 회원 |
| my-outings-dashboard | `/my-outings/dashboard` | `MyOutingsDashboardView` | 회원 |
| my-outings-libraries | `/my-outings/libraries` | `SavedLibrariesView` | 회원 |
| my-outings-books | `/my-outings/books` | `SavedBooksView` | 회원 |
| my-outings-programs | `/my-outings/programs` | `SavedProgramsView` | 회원 |
| my-outings-liked-reviews | `/my-outings/liked-reviews` | `LikedReviewsView` | 회원 |
| my-outings-reviews | `/my-outings/reviews` | `MyReviewsView` | 회원 |
| preferences | `/preferences` | `PreferenceSettingsView` | 회원 |
| onboarding-preferences | `/onboarding/preferences` | `PreferenceOnboardingView` | 회원 |
| login | `/auth/login` | `LoginView` | 비회원 권장 |
| signup | `/auth/signup` | `SignupView` | 비회원 권장 |
| profile | `/profile` | `ProfileView` | 회원 |
| profile-edit | `/profile/edit` | `ProfileEditView` | 회원 |
| forbidden | `/403` | `ForbiddenView` | 공개 |
| not-found | `/:pathMatch(.*)*` | `NotFoundView` | 공개 |

기존 `/reviews`는 v3에서 커뮤니티 목록 Route가 아니다. 필요하면 `/reviews`를 `/community`로 redirect한다.

## 4. Query 규칙

- 기본값은 URL에서 생략할 수 있다.
- 빈 문자열, `undefined`, `null`은 query에서 제거한다.
- 검색, 필터, 정렬 변경 시 `page=1`로 초기화한다.
- API v2.0이 comma string을 명시한 필터는 배열 UI를 comma string으로 직렬화한다.
- unsupported query는 보내지 않는다. 예: `radius_km`, `late_open_after`.
- 위치 좌표는 `nearby` 목적 또는 거리 계산 요청 단위로만 사용하고 계정에 저장하지 않는다.

## 5. DTO 요약

### 5.1 LibrarySummaryDto

```ts
interface LibrarySummaryDto {
  id: number
  name: string
  library_type: string
  sido: string
  sigungu: string
  road_address: string
  latitude: string | null
  longitude: string | null
  book_count: number | null
  reading_seat_count: number | null
  thumbnail: MediaSummaryDto | null
  purpose_score?: string | null
  distance_km?: number | null
  open_today: boolean | null
  open_now: boolean | null
  today_hours: LibraryTodayHoursDto | null
  closed_reason: string | null
  operation_status_reason: string | null
  holiday_operation_status?: HolidayOperationStatusDto
}
```

### 5.2 BookDto

```ts
interface BookDto {
  id?: number
  isbn13: string
  title: string
  authors_text: string | null
  publisher: string | null
  publication_year: string | null
  publication_date?: string | null
  kdc_class_no: string | null
  kdc_class_name: string | null
  cover_image_url: string | null
  description?: string | null
  source_detail_url?: string | null
  tags?: unknown[]
  loan_count?: number | null
}
```

### 5.3 ProgramDto

```ts
interface ProgramDto {
  id: number
  title: string
  library: { id: number; name: string; sigungu: string }
  category: string
  category_display: string
  target: string[]
  target_display: string
  application_required: boolean
  application_start_date: string | null
  application_end_date: string | null
  application_status: string | null
  application_status_display: string | null
  operation_start_date: string | null
  operation_end_date: string | null
  operation_status: string | null
  operation_status_display: string | null
  source_board: string | null
  source_url: string | null
  post_date: string | null
}
```

### 5.4 ReviewDto

```ts
interface ReviewDto {
  id: number
  library: { id: number; name: string; sigungu: string }
  user: { id: number; nickname: string }
  content: string
  view_count: number
  like_count: number
  created_at: string
  updated_at: string
  tags: ReviewTagDto[]
  images: ReviewImageDto[]
  related_books: unknown[]
  related_programs: unknown[]
}

interface ReviewTagDto {
  id: number
  code: string
  label: string
  review_label: string
}

interface ReviewImageDto {
  id: number
  url: string
  alt_text: string
  display_order: number
}
```

## 6. 홈

### 6.1 Route

`/`

### 6.2 API

```http
GET /api/v1/home/
GET /api/v1/home/?lat={lat}&lng={lng}
```

### 6.3 구성

```text
Hero
→ 오늘의 추천 도서관
→ 여기는 어때요?
→ 테마별 추천
```

### 6.4 Today Recommendations

- `today_recommendations.theme.title`
- `today_recommendations.theme.subtitle`
- `today_recommendations.items` 최대 3개 우선 표시
- item은 Library 카드와 `recommendation_reason`을 표시한다.

### 6.5 Theme Recommendations

5개 홈 공개 목적만 사용한다.

- `study`
- `book`
- `kids`
- `mood`
- `nearby`

테마 클릭은 `/libraries?purpose={code}`로 이동한다. `nearby`는 위치 동의 후 `lat`, `lng`를 붙인다. 위치 거절 시 안내 후 일반 도서관 탐색을 유지한다.

### 6.6 Personal Recommendations

- 로그인 access token이 있으면 요청에 포함한다.
- `personal_recommendations.available=true`일 때만 섹션을 표시한다.
- 수동 선호와 행동 기반 성향이 함께 반영될 수 있다.
- GMS는 추천 순위에 사용되지 않는다.

## 7. 도서관 찾기

### 7.1 Route

`/libraries`

### 7.2 API

```http
GET /api/v1/libraries/
```

### 7.3 Query

| Query | UI |
|---|---|
| `q` | 검색어 |
| `sigungu` | 구·군 multi select, comma string |
| `library_type` | 유형 multi select, comma string |
| `purpose` | 테마 목적 |
| `lat`, `lng` | nearby 거리 계산 |
| `has_reading_room` | 열람실 true 필터 |
| `has_children_room` | 어린이자료실 true 필터 |
| `has_digital_room` | 디지털자료실 true 필터 |
| `has_parking` | 주차장 true 필터 |
| `has_cafe` | 카페 true 필터 |
| `has_wifi` | 와이파이 true 필터 |
| `has_nursing_room` | 수유실 true 필터 |
| `has_accessible_facility` | 이동약자 편의시설 true 필터 |
| `has_elevator` | 엘리베이터 true 필터 |
| `has_lounge` | 휴게 공간 true 필터 |
| `has_outdoor_space` | 야외 공간 true 필터 |
| `min_book_count` | 최소 장서 수 |
| `min_reading_seat_count` | 최소 열람좌석 수 |
| `open_today` | 오늘 운영 |
| `open_now` | 현재 운영 |
| `weekend_open` | 주말 운영 |
| `holiday_status` | 공휴일 운영 상태 |
| `holiday_date` | 공휴일 날짜 |
| `ordering` | `name`, `-book_count`, `-reading_seat_count`, `purpose_score` |

시설 필터는 `true`만 보낸다. `false` query를 만들지 않는다. `purpose=nearby`에는 `lat`, `lng`가 필요하다.

### 7.4 표시

- 도서관명, 유형, 지역, 주소
- thumbnail과 attribution
- 장서 수, 열람좌석 수
- `distance_km` 값이 있을 때
- `purpose_score`는 사용자에게 점수 숫자 중심으로 노출하지 않고 정렬/추천 맥락으로 사용한다.
- `open_today`, `open_now`는 `true`, `false`, `null`을 구분한다.
- `today_hours`가 있으면 오늘 운영 시간 표시
- `holiday_operation_status`는 holiday query가 있을 때만 표시
- 저장 버튼

### 7.5 운영 상태 표시

| 값 | 표시 |
|---|---|
| `open_today=true` | 오늘 운영 |
| `open_today=false` | 오늘 휴관 |
| `open_today=null` | 오늘 운영 확인 필요 |
| `open_now=true` | 지금 운영 중 |
| `open_now=false` | 지금 운영 중 아님 |
| `open_now=null` | 현재 운영 확인 필요 |

## 8. 도서관 상세

### 8.1 Route

`/libraries/:id`

### 8.2 API

```http
GET /api/v1/libraries/{id}/
GET /api/v1/libraries/{id}/similar/?limit=3
GET /api/v1/programs/?library_id={id}
GET /api/v1/reviews/?library_id={id}
POST /api/v1/libraries/{id}/save/
DELETE /api/v1/libraries/{id}/save/
```

### 8.3 구성

```text
상단 요약
→ 기본 정보
→ 운영 정보
→ 장서/열람·공간 규모
→ 시설/공간 정보
→ 위치 정보
→ 관련 문화 프로그램
→ 관련 후기
→ 비슷한 도서관
```

### 8.4 표시 규칙

- thumbnail이 fallback이면 실제 도서관 사진처럼 설명하지 않는다.
- `attribution_text`가 있으면 출처 오버레이를 제공한다.
- `facility_profile.confirmed_facilities` 또는 true field만 시설 칩으로 표시한다.
- `false`, `null`, profile 부재를 시설 없음으로 단정하지 않는다.
- 관련 프로그램/후기 API 실패는 상세 전체 실패로 승격하지 않는다.
- Kakao 지도는 좌표가 있을 때만 표시한다.
- 좌표가 없거나 SDK 실패 시 주소와 외부 지도 검색 안내를 유지한다.

## 9. 책 둘러보기

### 9.1 Route

`/books`

### 9.2 API

```http
GET /api/v1/books/
GET /api/v1/books/popular/?limit=10&region=21
GET /api/v1/books/search/
```

### 9.3 구성

```text
PageHeader
→ 이번 주 인기 도서
→ 도서 검색
→ 검색 결과 또는 서비스 등록 책 목록
```

### 9.4 인기 도서

- 내부 DB의 최신 snapshot만 사용한다.
- snapshot이 없으면 섹션을 숨기거나 empty 안내를 표시한다.
- `limit` 최대 50 cap을 고려한다.

### 9.5 검색

Query:

- `search_type` + `q`
- 또는 직접 field: `title`, `author`, `isbn13`, `keyword`, `publisher`
- `sort`: `loan`, `title`, `author`, `pub`, `pubYear`, `isbn`
- `order`: `asc`, `desc`
- `page`, `page_size`

검색어가 없으면 외부 전체 검색을 호출하지 않는다.

## 10. 책 상세

### 10.1 Route

`/books/:isbn13`

### 10.2 API

```http
GET /api/v1/books/{isbn13}/
GET /api/v1/books/{isbn13}/libraries/
POST /api/v1/books/{isbn13}/save/
DELETE /api/v1/books/{isbn13}/save/
```

### 10.3 표시

- 표지, 도서명, 저자, 출판사, 출판연도
- `description`
- KDC 분류
- source detail link
- 태그
- 소장 도서관
- 저장/저장취소

소장 도서관의 `matched=false`는 내부 도서관 상세 링크를 만들지 않는다.

## 11. 문화 프로그램

### 11.1 Route

`/programs`, `/programs/:id`

### 11.2 API

```http
GET /api/v1/programs/
GET /api/v1/programs/{id}/
POST /api/v1/programs/{id}/save/
DELETE /api/v1/programs/{id}/save/
```

### 11.3 목록 Query

- `q`
- `library_id`
- `sigungu` comma filter
- `category` comma filter
- `target` comma filter
- `application_status` comma filter
- `operation_status` comma filter
- `page`, `page_size`

### 11.4 표시

- 프로그램명
- 운영 도서관 링크
- 지역
- category display
- target display
- `application_required`
- 신청 기간과 `application_status_display`
- 운영 기간과 `operation_status_display`
- 원문 게시글 링크
- 저장/저장취소

서비스 내부 신청, 예약, 결제 버튼은 만들지 않는다. 원문 링크는 새 탭으로 연다.

## 12. 커뮤니티 후기

### 12.1 Route

- `/community`
- `/reviews/:id`
- `/reviews/new`
- `/reviews/:id/edit`

### 12.2 API

```http
GET /api/v1/reviews/
POST /api/v1/reviews/
GET /api/v1/reviews/{id}/
PATCH /api/v1/reviews/{id}/
DELETE /api/v1/reviews/{id}/
POST /api/v1/reviews/{id}/like/
DELETE /api/v1/reviews/{id}/like/
```

### 12.3 후기 목록

Query:

- `q`
- `library_id`
- `tag` comma filter
- `user_id`
- `ordering`: `-created_at`, `-view_count`, `-like_count`
- `page`, `page_size`

표시:

- 도서관 링크
- 작성자 nickname
- 본문
- 작성일
- 태그
- 조회수
- 좋아요 수
- 이미지 preview
- 관련 책/프로그램 mini card

### 12.4 후기 상세

- GET detail은 `view_count`를 증가시킨다.
- 중복 요청과 hover prefetch를 피한다.
- 작성자·작성일·수정일
- 도서관 링크
- 본문
- 태그
- 이미지 gallery
- 관련 책과 관련 프로그램
- 조회수와 좋아요
- 작성자일 때 수정/삭제 진입 메뉴

`can_edit`, `can_delete`, `moderation_status`, `is_liked`는 응답에 없으므로 서버 응답 필드로 가정하지 않는다. 작성자 메뉴는 `auth.user.id === review.user.id`일 때만 보이며, 최종 권한은 서버 403을 따른다.

### 12.5 후기 작성

JSON request:

```json
{
  "library_id": 1,
  "content": "조용하고 책 읽기 좋았어요.",
  "tag_codes": ["review_quiet_study"],
  "book_ids": [1],
  "program_ids": [8]
}
```

Multipart request:

```text
library_id=1
content=...
tag_codes=["review_quiet_study"]
book_ids=[1]
program_ids=[8]
images=<file>
```

규칙:

- 인증 필요
- 본문 1~200자
- 후기 태그 1~5개
- 관련 책·프로그램 선택 가능
- 관련 프로그램은 후기 도서관과 같은 도서관 프로그램만 허용
- 이미지 최대 5장
- 허용 확장자: `jpg`, `jpeg`, `png`, `webp`
- 금지 확장자: `gif`, `svg`

### 12.6 후기 수정과 이미지 교체

PATCH JSON:

```json
{
  "content": "수정된 후기입니다.",
  "tag_codes": ["review_quiet_study"],
  "book_ids": [],
  "program_ids": []
}
```

이미지 정책:

- `images` 생략: 기존 이미지 유지
- 새 `images`: `replace_images=true` 필요
- `replace_images=true` + 새 이미지: 전체 교체
- `replace_images=true` + 이미지 없음: 전체 삭제
- storage 파일 삭제는 서버가 시도한다.

### 12.7 후기 좋아요

- 로그인 필요
- POST/DELETE `/reviews/{id}/like/`
- 응답의 `like_count`로 현재 목록/상세 count를 갱신한다.
- 초기 liked 여부는 나의 나들이 liked reviews hydration으로 보완한다.

## 13. 나의 나들이

### 13.1 Route

- `/my-outings/dashboard`
- `/my-outings/libraries`
- `/my-outings/books`
- `/my-outings/programs`
- `/my-outings/liked-reviews`
- `/my-outings/reviews`

### 13.2 API

```http
GET /api/v1/my-outings/dashboard/
GET /api/v1/my-outings/libraries/
GET /api/v1/my-outings/books/
GET /api/v1/my-outings/programs/
GET /api/v1/my-outings/reviews/
GET /api/v1/my-outings/liked-reviews/
```

### 13.3 Dashboard 표시

- `profile_summary`
  - nickname
  - saved counts
  - review count
  - liked review count
- `activity_summary`
  - total saved/review/like/signal count
- `preference_summary`
  - top_regions
  - top_library_facilities
  - top_book_subjects
  - top_program_categories
  - top_review_tags
- `outing_type_summary`
  - study
  - book
  - program
  - rest
- `summary_sentence`
- `analysis_basis`
- `preference_status`

### 13.4 preference_status 표시

| status | 표시 |
|---|---|
| `collecting` | 행동 신호 수집 중 |
| `pending` | 변경사항 반영 대기 중 |
| `ready` | 분석 완료 |
| `failed` | 분석 실패, 이후 재시도 가능 |

`summary_sentence`는 GMS 성공 여부와 무관하게 API 필드만 표시한다.

## 14. 사용자/프로필

### 14.1 표시

- email
- nickname
- bio
- profile_image_url
- profile_image_alt

### 14.2 수정

Endpoint:

```http
PATCH /api/v1/users/me/
```

지원:

- nickname
- bio
- profile_image_alt
- profile_image upload
- remove_profile_image

이미지 규칙:

- 허용: `jpg`, `jpeg`, `png`, `webp`
- 금지: `gif`, `svg`
- 최대 크기: `MEDIA_MAX_UPLOAD_MB`
- media URL은 `/media/` 상대 경로일 수 있으므로 API base와 별도로 안전하게 resolve한다.

## 15. 선호 설정

### 15.1 API

```http
GET /api/v1/preferences/options/
GET /api/v1/users/me/preferences/
PUT /api/v1/users/me/preferences/
```

### 15.2 수동 선호

사용자가 직접 선택한 값이다.

- 목적: `purpose_codes`
- 지역: `{ sido, sigungu }[]`
- 시설 태그: `tag_codes`

PUT은 전체 교체 저장으로 이해한다.

### 15.3 행동 기반 성향

저장, 후기, 좋아요 활동으로 서버가 계산한다.

- dashboard
- home personal recommendations
- summary_sentence

수동 선호와 행동 기반 성향은 서로 다른 데이터다. UI 문구에서 이를 분리해 설명한다.

## 16. 저장과 좋아요 Interaction

### 16.1 저장 대상

- library id
- book isbn13
- program id

### 16.2 좋아요 대상

- review id

### 16.3 초기 상태

API v2.0 주의사항에 따라 `is_saved`, `is_liked` 필드에 의존하지 않는다.

Hydration source:

- `/my-outings/libraries/`
- `/my-outings/books/`
- `/my-outings/programs/`
- `/my-outings/liked-reviews/`

초기 hydration 전 상태는 `unknown`이다.

## 17. 이미지와 미디어

### 17.1 공통

- 서버 이미지 URL은 절대 URL 또는 `/media/`, `/static/` 상대 URL일 수 있다.
- 프론트는 URL을 깨뜨리지 않고 표시한다.
- 외부 이미지 다운로드나 프론트 asset 생성으로 대체하지 않는다.

### 17.2 도서관 이미지

- `thumbnail.is_fallback=true`이면 실제 도서관 사진처럼 alt를 쓰지 않는다.
- `attribution_text`가 있으면 hover/focus/tap 가능한 출처 오버레이를 표시한다.

### 17.3 책 표지

- `cover_image_url`이 없으면 CSS 기반 fallback을 표시한다.

### 17.4 후기 이미지

- 업로드 UI는 후기 작성/수정 form에서만 제공한다.
- 목록/상세에서는 서버가 준 `images` 배열만 표시한다.
- `alt_text`가 비어 있으면 "후기 이미지" 또는 문맥 기반 alt를 사용한다.

### 17.5 프로필 이미지

- `profile_image_url`이 있으면 표시한다.
- 없으면 initials/avatar fallback을 사용한다.
- 제거는 `remove_profile_image=true`.

## 18. Kakao Map

- Kakao JavaScript Key만 프론트 환경변수로 사용한다.
- Kakao REST API Key, Admin Key는 프론트에 넣지 않는다.
- 지도는 도서관 상세 위치 영역에서 좌표가 있을 때만 lazy load한다.
- 좌표 없음, SDK 실패, key 없음은 지도 fallback UI로 처리한다.
- 지도만으로 위치를 전달하지 않고 주소 텍스트와 외부 지도 링크를 함께 제공한다.

## 19. Page Structure 최종 구현 대상

`도서관 나들이 주요 페이지 구조.txt`의 모든 상위 페이지는 v3 최종 구현 대상이다.

구현 대상:

1. 홈
2. 도서관 찾기
3. 책 둘러보기
4. 문화 프로그램
5. 커뮤니티
6. 나의 나들이
7. 도서관 상세 페이지

다만 다음 항목은 API v2.0 제약에 맞게 조정한다.

- 늦게까지 운영 `18:00 이후` 필터는 `late_open_after`가 unsupported이므로 직접 query로 구현하지 않는다.
- 후기 태그 옵션 공급은 API v2.0에 전용 options endpoint가 없으므로 seed/tag 계약 확인 후 구현한다.
- 도서관 주요 태그 요약은 응답 field가 확정된 경우에만 표시한다.

## 20. Service 함수

권장 service:

- `authService`
- `accountService`
- `homeService`
- `libraryService`
- `bookService`
- `programService`
- `reviewService`
- `myOutingsService`
- `preferenceService`
- `mediaUrl`

각 service는 API v2.0 query allowlist를 갖고, unsupported query를 보내지 않는다.

필수 추가/수정:

- `fetchSimilarLibraries(id, { limit })`
- `fetchPopularBooks({ limit, region })`
- `fetchMyOutingsDashboard()`
- `fetchPreferenceOptions()`
- `fetchUserPreferences()`
- `saveUserPreferences(payload)`
- `createReview(payload, mode)`
- `updateReview(id, payload, mode)`
- `likeReview(id)`, `unlikeReview(id)`

## 21. Store

권장 store:

- `authStore`
- `interactionStore`
- `homeStore`
- `libraryStore`
- `bookStore`
- `programStore`
- `communityStore`
- `myOutingsStore`
- `preferenceStore`

Store는 필수는 아니지만 다음 상태는 중앙화 권장이다.

- 인증 상태
- access token
- 현재 user
- 저장/좋아요 hydration set
- 나의 나들이 dashboard cache
- preference options
- toast/notification

## 22. 접근성

- RouterLink와 button 역할을 구분한다.
- 저장, 좋아요, 삭제는 button이다.
- 상세 이동과 외부 링크는 link다.
- 외부 링크는 `target="_blank" rel="noopener noreferrer"`.
- `aria-current="page"`를 현재 nav에 제공한다.
- 이미지 fallback alt를 실제 사진처럼 쓰지 않는다.
- focus-visible을 제거하지 않는다.
- 색상만으로 상태를 구분하지 않는다.

## 23. 보안과 개인정보

- access token을 localStorage에 장기 저장하지 않는다.
- refresh token은 HttpOnly Cookie다.
- 서버 API key, GMS key, Django secret은 프론트에 노출하지 않는다.
- 후기 작성 중 본문과 이미지 파일은 외부 오류 로그에 남기지 않는다.
- 프로필 이미지와 후기 이미지 업로드는 확장자와 크기 제한을 UI에서도 안내한다.
- 좌표는 요청에만 사용하고 사용자 계정에 저장하지 않는다.

## 24. 테스트와 검증

### 24.1 명령

```bash
cd frontend
npm run lint
npm run build
```

### 24.2 Route smoke

- `/`
- `/libraries`
- `/libraries/1`
- `/books`
- `/books/{isbn13}`
- `/programs`
- `/programs/1`
- `/community`
- `/reviews/1`
- `/my-outings/dashboard`
- `/preferences`
- `/profile`

### 24.3 API smoke 연계

README 순서를 기준으로 backend fixture와 smoke test를 먼저 준비한다.

1. backend migrate
2. `seed_service_defaults`
3. library/book/program/holiday/daily schedule fixture load
4. backend runserver
5. frontend dev server
6. API 화면별 empty/error/success 확인

### 24.4 핵심 E2E

- 이메일 회원가입/로그인/refresh/logout
- 도서관 고급 필터
- 도서관 상세 related programs/reviews/similar
- 인기 도서와 책 검색 503 분리
- 프로그램 필터와 원문 링크
- 후기 목록/상세/view count
- 후기 작성/이미지 업로드/수정 replace_images/삭제
- 후기 좋아요/취소
- 나의 나들이 dashboard
- 선호 설정 저장 후 home personal 변화

## 25. v2.1 대비 주요 변경

- API 기준을 v1.1에서 v2.0으로 변경했다.
- 도서관 고급 필터, 운영 상태, 공휴일 상태, 비슷한 도서관을 활성 범위로 편입했다.
- 주간 인기 도서를 활성 범위로 편입했다.
- 후기 이미지 업로드와 replace_images 정책을 활성 범위로 편입했다.
- 나의 나들이 dashboard와 행동 기반 성향 요약을 활성 범위로 편입했다.
- 프로필 bio와 profile image 수정/삭제를 활성 범위로 편입했다.
- 프로그램 DTO의 display field와 comma filter를 v2.0 기준으로 조정했다.
- 선호 설정과 행동 기반 성향의 역할을 분리했다.

## 26. 구현 순서 권장

1. API v2.0 service allowlist 정리
2. 공통 media URL, image fallback, attribution overlay 정리
3. 커뮤니티 목록/상세
4. 나의 나들이 dashboard
5. 도서관 고급 필터와 상세 related/similar
6. 인기 도서와 책 v2.0 보강
7. 프로그램 v2.0 필터/display 보강
8. 선호 설정
9. 후기 작성/수정/삭제/좋아요/이미지 업로드
10. 프로필 이미지와 bio 수정

