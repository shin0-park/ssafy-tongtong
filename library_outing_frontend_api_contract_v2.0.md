# 도서관 나들이 프론트 전달용 API 계약 문서 v4.0

- 문서 버전: 4.0
- 기준일: 2026-07-06
- 기준 구현: 현재 Django REST API `/api/v1`
- 문서 성격: 프론트엔드가 지금부터 기준으로 삼을 최종 API 계약서

## 0. 공통 규칙

### Base URL

```text
/api/v1
```

### 인증

로그인 식별자는 `email`이다. `username` 로그인은 사용하지 않는다.

로그인과 회원가입 성공 시 access token은 응답 body로 전달된다. refresh token은 응답 body가 아니라 HttpOnly Cookie로 관리된다.

```http
Authorization: Bearer <access_token>
```

### 서버 비밀키

다음 값은 프론트엔드에 전달하지 않는다.

- `DATA4LIBRARY_API_KEY`
- `DATA_GO_KR_API_KEY`
- `GMS_API_KEY`
- Django secret key
- Kakao REST API Key
- Kakao Admin Key

Kakao Map JavaScript SDK용 JavaScript Key만 브라우저에 노출할 수 있다. 프론트 환경변수는 `VITE_KAKAO_MAP_JAVASCRIPT_KEY`처럼 공개 식별자임이 드러나는 이름을 사용한다.

### AI Recommendation Layer v4 사용 경계

v4에서는 AI를 사용자 성향 분석, 우선 태그 산출, 후보 재랭킹, 추천 이유 생성에 사용할 수 있다. 프론트엔드는 AI/GMS를 직접 호출하지 않고 항상 Django API만 호출한다.

추천 흐름:

```text
Vue → Django API → RecommendationProvider → Django validation → Vue
```

세부 단계:

```text
AI Preference Planner
→ DB Retrieval
→ AI Reranker
→ Django Validation
```

경계:

- 전체 도서관 raw data를 AI에 직접 전달하지 않는다.
- AI Preference Planner 입력은 사용자 행동 요약, 수동 선호, 사용 가능한 `Tag.code` 목록으로 제한한다.
- DB Retrieval은 Django가 담당하며 시설, 운영 여부, 장서 수, 좌석 수, 지역, 거리 계산은 DB와 기존 service가 기준이다.
- AI Reranker 입력은 후보 10~20개의 요약 feature로 제한한다.
- AI는 도서관 존재 여부, 시설 여부, 운영 여부, 책·프로그램·후기 존재 여부, 이미지·출처·라이선스 같은 원천 사실을 생성하거나 수정하지 않는다.
- AI 출력은 구조화 JSON이며 Django에서 `library_id`, `tag_code`, 활성 도서관, 운영 필수 조건, JSON schema를 검증한다.
- `GMS_API_KEY`가 없거나 만료되어도 mock/fallback provider 기준으로 같은 API 응답 형태가 성립해야 한다.

### Pagination

목록형 API는 기본적으로 DRF page number pagination wrapper를 사용한다.

```json
{
  "count": 220,
  "next": "http://testserver/api/v1/libraries/?page=2",
  "previous": null,
  "results": []
}
```

공통 query:

```text
page
page_size
```

기본 `page_size`는 20, 최대 `page_size`는 100이다.

### Error

대표 오류 형식:

```json
{
  "detail": "Error message."
}
```

Serializer validation 오류는 field별 object로 반환될 수 있다.

```json
{
  "tag_codes": ["Invalid review tag code."]
}
```

상태 코드:

| Status | 의미 |
|---|---|
| 400 | validation 실패, invalid query, unsupported query |
| 401 | 인증 필요 또는 access token 없음/만료 |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 502 | 외부 API 호출 실패 |
| 503 | 외부 API key 미설정 또는 사용 불가 |

## 1. 인증/사용자 API

### 1.1 회원가입

```http
POST /api/v1/auth/signup/
```

Request:

```json
{
  "email": "outing@example.com",
  "password": "password1234",
  "nickname": "도서관나들이"
}
```

Response `201`:

```json
{
  "access": "access_token",
  "user": {
    "id": 1,
    "email": "outing@example.com",
    "nickname": "도서관나들이",
    "profile": {
      "bio": "",
      "profile_image_url": "",
      "profile_image_alt": ""
    }
  }
}
```

### 1.2 로그인

```http
POST /api/v1/auth/login/
```

Request:

```json
{
  "email": "outing@example.com",
  "password": "password1234"
}
```

Response `200`:

```json
{
  "access": "access_token",
  "user": {
    "id": 1,
    "email": "outing@example.com",
    "nickname": "도서관나들이",
    "profile": {
      "bio": "",
      "profile_image_url": "",
      "profile_image_alt": ""
    }
  }
}
```

### 1.3 토큰 갱신

```http
POST /api/v1/auth/token/refresh/
```

refresh token cookie가 유효하면 access token을 재발급한다.

Response `200`:

```json
{
  "access": "new_access_token"
}
```

### 1.4 로그아웃

```http
POST /api/v1/auth/logout/
```

Response `200`:

```json
{
  "detail": "Successfully logged out."
}
```

### 1.5 내 정보 조회

```http
GET /api/v1/users/me/
```

인증 필요.

Response `200`:

```json
{
  "id": 1,
  "email": "outing@example.com",
  "nickname": "도서관나들이",
  "profile": {
    "bio": "도서관 산책을 좋아해요.",
    "profile_image_url": "/media/profiles/example.jpg",
    "profile_image_alt": "프로필 이미지"
  }
}
```

### 1.6 내 정보 수정

```http
PATCH /api/v1/users/me/
```

인증 필요. JSON과 `multipart/form-data`를 모두 지원한다.

JSON request:

```json
{
  "nickname": "김나들이",
  "bio": "도서관 산책을 좋아해요.",
  "profile_image_alt": "프로필 이미지",
  "remove_profile_image": false
}
```

Multipart request:

```text
nickname=김나들이
bio=도서관 산책을 좋아해요.
profile_image_alt=프로필 이미지
profile_image=<file>
```

프로필 이미지 정책:

- 허용: `jpg`, `jpeg`, `png`, `webp`
- 금지: `gif`, `svg`
- 1장 최대 크기: `MEDIA_MAX_UPLOAD_MB`, 기본 10MB
- `remove_profile_image=true`이면 DB 참조와 storage 파일 삭제를 시도한다.

Response `200`: `GET /users/me/`와 동일한 user object.

## 2. 홈 추천 API

### 2.1 홈 추천 조회

```http
GET /api/v1/home/
```

비로그인 조회 가능. 로그인 사용자는 access token을 포함하면 personal 추천이 활성화될 수 있다.

Query:

| 이름 | 필수 | 설명 |
|---|---|---|
| `lat` | optional | nearby 테마 거리 점수 계산용 위도 |
| `lng` | optional | nearby 테마 거리 점수 계산용 경도 |

Response `200`:

```json
{
  "today_recommendations": {
    "theme": {
      "code": "rich_collection",
      "title": "장서가 풍부한 도서관",
      "subtitle": "책 탐색에 좋은 곳"
    },
    "items": []
  },
  "theme_recommendations": [
    {
      "purpose": {
        "code": "study",
        "label": "공부"
      },
      "items": []
    }
  ],
  "personal_recommendations": {
    "available": true,
    "reason": "선호 설정과 나들이 활동을 함께 반영했어요.",
    "priority_tags": [
      {
        "code": "facility_lounge",
        "label": "휴게공간",
        "weight": 0.7
      }
    ],
    "fallback_used": false,
    "items": [
      {
        "id": 12,
        "name": "부산도서관",
        "sigungu": "사상구",
        "address": "부산광역시 사상구 ...",
        "thumbnail": null,
        "recommendation_reason": "최근 조용한 학습공간과 휴게공간 선호가 함께 보여 추천했어요.",
        "ai_rank": 1,
        "ai_confidence": 0.82,
        "matched_priority_tags": [
          {
            "code": "facility_lounge",
            "label": "휴게공간"
          }
        ]
      }
    ]
  }
}
```

`personal_recommendations`는 수동 선호와 행동 기반 성향을 함께 반영한다.

- 수동 선호만 있으면 수동 선호 기반으로 제공된다.
- 행동 신호만 있어도 제공될 수 있다.
- 둘 다 없으면 `available=false`와 빈 `items`를 반환한다.
- AI Preference Planner는 `priority_purposes`, `priority_tags`, `preferred_regions`, `weights`를 JSON으로 반환할 수 있다.
- Django는 AI가 반환한 우선 태그와 가중치를 이용해 DB 후보를 10~20개로 줄인다.
- AI Reranker는 후보 요약 feature만 입력받아 최종 `ai_rank`, `ai_confidence`, `matched_priority_tags`, `recommendation_reason`을 JSON으로 반환할 수 있다.
- Django validation을 통과한 결과만 프론트에 반환한다.
- AI 실패, timeout, key 없음, schema 위반, 검증 실패 시 `fallback_used=true`와 함께 mock 또는 rule-based fallback 결과를 반환한다.

추천 item은 `RecommendationLibrary`이며 `LibraryList` 필드에 `recommendation_reason`이 추가된다.

AI fallback 정책:

- Planner 실패 시 수동 선호와 행동 기반 `UserPreferenceItem`으로 priority를 구성한다.
- Reranker 실패 시 DB Retrieval 점수와 안정 정렬 기준으로 순위를 만든다.
- 존재하지 않는 `library_id`, 존재하지 않는 `tag_code`, 비활성 도서관, 운영 필수 조건을 위반한 후보는 제거한다.
- 제거 후 결과가 부족해도 휴관·미확인 도서관이나 원천 사실이 불명확한 후보로 채우지 않는다.
- fallback 응답도 같은 response schema를 유지한다.

## 3. 도서관 API

### 3.1 도서관 목록

```http
GET /api/v1/libraries/
```

Query:

| 이름 | 값 | 설명 |
|---|---|---|
| `q` | string | 도서관명, 지역명, 주소, 운영기관 검색 |
| `sigungu` | comma string | 구·군 복수 필터 |
| `library_type` | comma string | `public`, `small`, `children`, `other` 등 |
| `purpose` | `study`, `book`, `kids`, `mood`, `nearby` | 목적 점수 계산과 정렬 |
| `lat` | number | 거리 계산용 위도 |
| `lng` | number | 거리 계산용 경도 |
| `has_reading_room` | `true` | 열람실 필터 |
| `has_children_room` | `true` | 어린이자료실 필터 |
| `has_digital_room` | `true` | 디지털자료실 필터 |
| `has_parking` | `true` | 주차장 필터 |
| `has_cafe` | `true` | 카페 필터 |
| `has_wifi` | `true` | 무료 와이파이 필터 |
| `has_nursing_room` | `true` | 수유실 필터 |
| `has_accessible_facility` | `true` | 이동약자 편의시설 필터 |
| `has_elevator` | `true` | 엘리베이터 필터 |
| `has_lounge` | `true` | 휴게 공간 필터 |
| `has_outdoor_space` | `true` | 야외 공간 필터 |
| `min_book_count` | integer | 최소 장서 수 |
| `min_reading_seat_count` | integer | 최소 열람 좌석 수 |
| `ordering` | `name`, `-book_count`, `-reading_seat_count`, `purpose_score` | 정렬 |
| `open_today` | `true` | 오늘 운영 중인 도서관만 |
| `open_now` | `true` | 현재 시각 운영 중인 도서관만 |
| `weekend_open` | `true` | 가까운 주말 중 운영 가능한 도서관 |
| `holiday_status` | `open`, `closed`, `unknown` | 지정 또는 다음 공휴일 운영 상태 |
| `holiday_date` | `YYYY-MM-DD` | complete calendar의 공휴일 날짜 |

정책:

- 시설 필터는 `true`만 지원한다. `false`는 400이다.
- `purpose=nearby`는 `lat`, `lng`가 필수다.
- `radius_km`, `late_open_after`는 현재 unsupported query이며 400이다.
- 좌표는 요청 단위 계산에만 사용하고 DB에 저장하지 않는다.
- `holiday_status` 필터 결과에서도 기존 `open_today`, `open_now`, `today_hours`는 오늘 기준이다.
- `holiday_status` 또는 `holiday_date`가 있을 때만 `holiday_operation_status`가 응답에 포함된다.

Response item:

```json
{
  "id": 1,
  "name": "부산도서관",
  "library_type": "public",
  "sido": "부산광역시",
  "sigungu": "사상구",
  "road_address": "부산광역시 ...",
  "latitude": "35.0000000",
  "longitude": "129.0000000",
  "book_count": 100000,
  "reading_seat_count": 300,
  "thumbnail": {
    "url": "/static/media_assets/placeholders/default_library_public.png",
    "is_fallback": true,
    "fallback_key": "library/public",
    "license_code": "internal",
    "attribution_text": null
  },
  "purpose_score": "3.5000",
  "distance_km": 1.23,
  "open_today": true,
  "open_now": false,
  "today_hours": {
    "open": "09:00",
    "close": "18:00",
    "closes_next_day": false
  },
  "closed_reason": null,
  "operation_status_reason": "daily_schedule:opening_hour",
  "holiday_operation_status": {
    "date": "2026-01-01",
    "status": "open",
    "open_time": "10:00",
    "close_time": "18:00",
    "closes_next_day": false,
    "reason_code": "public_holiday_opening_hour"
  }
}
```

`open_today`, `open_now`는 `true | false | null`이다. `null`은 데이터 부족 또는 판정 불가다.

### 3.2 도서관 상세

```http
GET /api/v1/libraries/{id}/
```

Response는 목록 item 필드에 다음 필드가 추가된다.

```json
{
  "phone": "051-000-0000",
  "homepage_url": "https://example.org",
  "operating_agency": "부산광역시",
  "short_description": "",
  "statistics": {
    "reference_date": "2026-01-01",
    "reading_seat_count": 300,
    "book_count": 100000,
    "serial_count": 200,
    "non_book_count": 1000,
    "loan_limit_count": 5,
    "loan_period_days": 14,
    "site_area": "1000.00",
    "building_area": "500.00"
  },
  "facility_profile": {
    "has_reading_room": true,
    "has_children_room": false,
    "has_digital_room": null,
    "confirmed_facilities": ["has_reading_room"]
  },
  "opening_hours": [],
  "closure_rules": []
}
```

관련 프로그램과 후기는 상세 응답에 embedded하지 않는다. 프론트는 다음 기존 API를 사용한다.

```http
GET /api/v1/programs/?library_id={id}
GET /api/v1/reviews/?library_id={id}
```

### 3.3 비슷한 도서관

```http
GET /api/v1/libraries/{id}/similar/
```

Query:

| 이름 | 기본 | 최대 | 설명 |
|---|---:|---:|---|
| `limit` | 3 | 10 | 결과 수 |

`limit=bad`는 400이다.

Response `200`:

```json
{
  "count": 3,
  "results": [
    {
      "id": 2,
      "name": "비슷한도서관",
      "similarity_score": "7.5000",
      "similarity_reasons": [
        "same_sigungu",
        "same_library_type",
        "shared_facilities",
        "similar_collection",
        "similar_seats",
        "shared_tags"
      ]
    }
  ]
}
```

유사도는 내부 DB의 지역, 유형, 시설, 통계, 태그 기반 비영속 계산이다. 외부 API를 호출하지 않는다.

### 3.4 도서관 저장/해제

```http
POST /api/v1/libraries/{id}/save/
DELETE /api/v1/libraries/{id}/save/
```

인증 필요. 저장/해제 후 행동 기반 성향은 pending 처리되고, 이후 dashboard/home 요청에서 lazy rebuild될 수 있다.

## 4. 책 API

### 4.1 책 목록

```http
GET /api/v1/books/
```

내부 DB에 저장된 활성 책 목록을 반환한다.

Book item:

```json
{
  "id": 1,
  "isbn13": "9790000000000",
  "title": "책 제목",
  "authors_text": "저자",
  "publisher": "출판사",
  "publication_year": "2026",
  "kdc_class_no": "800",
  "kdc_class_name": "문학",
  "cover_image_url": "https://...",
  "is_active": true
}
```

### 4.2 책 상세

```http
GET /api/v1/books/{isbn13}/
```

목록 필드에 `publication_date`, `volume`, `addition_symbol`, `description`, `source_detail_url`, `provider_code`, `metadata_fetched_at`, `tags`가 추가된다.

### 4.3 책 검색

```http
GET /api/v1/books/search/
```

정보나루 API를 호출한다. 서버 API key가 없으면 503이다.

Query:

| 이름 | 설명 |
|---|---|
| `search_type` + `q` | `title`, `author`, `isbn`, `keyword`, `publisher` 중 하나와 검색어 |
| `title` | 제목 직접 검색 |
| `author` | 저자 직접 검색 |
| `isbn13` | ISBN 직접 검색 |
| `keyword` | 키워드 직접 검색 |
| `publisher` | 출판사 직접 검색 |
| `page` | 기본 1 |
| `page_size` | 기본 20, 최대 100 |
| `sort` | `loan`, `title`, `author`, `pub`, `pubYear`, `isbn` |
| `order` | `asc`, `desc` |

Response:

```json
{
  "source": "data4library",
  "num_found": 100,
  "page": 1,
  "page_size": 20,
  "results": []
}
```

### 4.4 소장 도서관

```http
GET /api/v1/books/{isbn13}/libraries/
```

정보나루 `libSrchByBook` 기반 부산 소장 도서관을 반환한다.

Response:

```json
{
  "isbn13": "9790000000000",
  "source": "data4library",
  "count": 3,
  "page": 1,
  "page_size": 20,
  "results": []
}
```

### 4.5 주간 인기 도서

```http
GET /api/v1/books/popular/
```

내부 DB의 가장 최근 `PopularBookSnapshot`만 사용한다. 외부 API를 호출하지 않는다.

Query:

| 이름 | 기본 | 최대 | 설명 |
|---|---:|---:|---|
| `limit` | 10 | 50 | 반환 item 수. 50 초과는 50으로 cap |
| `region` | `21` | - | 정보나루 지역 코드. 부산은 21 |

`limit=bad`는 400이다.

Response:

```json
{
  "snapshot": {
    "id": 1,
    "provider_code": "data4library",
    "scope_type": "region",
    "region_code": "21",
    "period_start": "2026-06-01",
    "period_end": "2026-06-07",
    "generated_at": "2026-06-24T12:00:00+09:00",
    "fetched_at": "2026-06-24T12:00:00+09:00",
    "fresh_until": "2026-07-01T12:00:00+09:00",
    "result_count": 100,
    "is_stale": false
  },
  "items": [
    {
      "rank": 1,
      "loan_count": 120,
      "book": {}
    }
  ]
}
```

스냅샷이 없으면 `snapshot=null`, `items=[]`이다.

### 4.6 책 저장/해제

```http
POST /api/v1/books/{isbn13}/save/
DELETE /api/v1/books/{isbn13}/save/
```

인증 필요.

## 5. 프로그램 API

### 5.1 프로그램 목록

```http
GET /api/v1/programs/
```

Query:

| 이름 | 설명 |
|---|---|
| `q` | 제목, 도서관명, 게시판, 원문 URL 검색 |
| `library_id` | 개최 도서관 |
| `sigungu` | 구·군 comma filter |
| `category` | category code comma filter |
| `target` | target code comma filter |
| `application_status` | 신청 상태 comma filter |
| `operation_status` | 운영 상태 comma filter |

Response item:

```json
{
  "id": 1,
  "title": "프로그램명",
  "library": {
    "id": 1,
    "name": "부산도서관",
    "sigungu": "사상구"
  },
  "category": "reading",
  "category_display": "독서",
  "target": ["adult"],
  "target_display": "성인",
  "application_required": true,
  "application_start_date": "2026-06-01",
  "application_end_date": "2026-06-10",
  "application_status": "open",
  "application_status_display": "신청중",
  "operation_start_date": "2026-06-15",
  "operation_end_date": "2026-06-20",
  "operation_status": "scheduled",
  "operation_status_display": "예정",
  "source_board": "reading",
  "source_url": "https://...",
  "post_date": "2026-05-31"
}
```

### 5.2 프로그램 상세

```http
GET /api/v1/programs/{id}/
```

목록 필드에 `source_sido`, `source_sigungu`, `source_library_name`, `provider_code`, `external_program_key`, `collected_at`, `tags`가 추가된다.

### 5.3 프로그램 저장/해제

```http
POST /api/v1/programs/{id}/save/
DELETE /api/v1/programs/{id}/save/
```

인증 필요.

## 6. 커뮤니티 후기 API

### 6.1 후기 목록/작성

```http
GET /api/v1/reviews/
POST /api/v1/reviews/
```

GET query:

| 이름 | 설명 |
|---|---|
| `q` | 본문, 도서관명 검색 |
| `library_id` | 도서관 필터 |
| `tag` | 후기 태그 code comma filter |
| `user_id` | 작성자 필터 |
| `ordering` | `-created_at`, `-view_count`, `-like_count` |

Review response:

```json
{
  "id": 1,
  "library": {
    "id": 1,
    "name": "부산도서관",
    "sigungu": "사상구"
  },
  "user": {
    "id": 1,
    "nickname": "도서관나들이"
  },
  "content": "조용하고 책 읽기 좋았어요.",
  "view_count": 10,
  "like_count": 2,
  "created_at": "2026-06-25T12:00:00+09:00",
  "updated_at": "2026-06-25T12:00:00+09:00",
  "tags": [
    {
      "id": 1,
      "code": "review_quiet_study",
      "label": "조용한 학습",
      "review_label": "조용히 공부하기 좋아요"
    }
  ],
  "images": [
    {
      "id": 1,
      "url": "/media/reviews/example.jpg",
      "alt_text": "",
      "display_order": 0
    }
  ],
  "related_books": [],
  "related_programs": []
}
```

JSON create request:

```json
{
  "library_id": 1,
  "content": "조용하고 책 읽기 좋았어요.",
  "tag_codes": ["review_quiet_study"],
  "book_ids": [1],
  "program_ids": [8]
}
```

Multipart create request:

```text
library_id=1
content=조용하고 책 읽기 좋았어요.
tag_codes=["review_quiet_study"]
book_ids=[1]
program_ids=[8]
images=<file>
images=<file>
```

후기 작성 정책:

- 인증 필요
- 본문 1~200자
- 후기 태그 1~5개
- 관련 책·프로그램은 선택
- 관련 프로그램은 후기 도서관과 같은 도서관 프로그램이어야 한다.

이미지 정책:

- 허용: `jpg`, `jpeg`, `png`, `webp`
- 금지: `gif`, `svg`
- 1장 최대 크기: `MEDIA_MAX_UPLOAD_MB`, 기본 10MB
- 후기 1개 최대 5장

### 6.2 후기 상세/수정/삭제

```http
GET /api/v1/reviews/{id}/
PATCH /api/v1/reviews/{id}/
DELETE /api/v1/reviews/{id}/
```

GET detail은 공개 후기 조회 시 `view_count`를 1 증가시키고, 응답에는 증가된 값이 반영된다. 목록 조회, 수정, 삭제, like/unlike는 조회수를 증가시키지 않는다.

PATCH JSON request:

```json
{
  "content": "수정된 후기입니다.",
  "tag_codes": ["review_quiet_study"],
  "book_ids": [],
  "program_ids": []
}
```

PATCH 이미지 정책:

- `images`를 생략하면 기존 이미지를 유지한다.
- 새 `images`를 보내려면 `replace_images=true`가 필요하다.
- `replace_images=true`와 새 `images`를 보내면 전체 교체한다.
- `replace_images=true`와 이미지 없음이면 전체 삭제한다.
- 기존 이미지 삭제 시 storage 파일 삭제를 시도한다.

작성자만 수정/삭제할 수 있다.

### 6.3 후기 좋아요/취소

```http
POST /api/v1/reviews/{id}/like/
DELETE /api/v1/reviews/{id}/like/
```

인증 필요.

Response:

```json
{
  "liked": true,
  "review_id": 1,
  "like_count": 3
}
```

## 7. 나의 나들이 API

모든 endpoint는 인증 필요.

```http
GET /api/v1/my-outings/libraries/
GET /api/v1/my-outings/books/
GET /api/v1/my-outings/programs/
GET /api/v1/my-outings/reviews/
GET /api/v1/my-outings/liked-reviews/
```

저장 목록은 저장 row의 `id`, `memo`, `created_at`, `updated_at`과 대상 summary를 포함한다. 좋아요한 후기는 `liked_at`과 review object를 포함한다.

### 7.1 나의 나들이 대시보드

```http
GET /api/v1/my-outings/dashboard/
```

Response:

```json
{
  "profile_summary": {
    "nickname": "도서관나들이",
    "saved_library_count": 1,
    "saved_book_count": 1,
    "saved_program_count": 1,
    "review_count": 1,
    "liked_review_count": 1
  },
  "activity_summary": {
    "total_saved_count": 3,
    "total_review_count": 1,
    "total_like_count": 1,
    "total_signal_count": 5
  },
  "preference_summary": {
    "top_regions": [],
    "top_library_facilities": [],
    "top_book_subjects": [],
    "top_program_categories": [],
    "top_review_tags": []
  },
  "outing_type_summary": {
    "study": 40.0,
    "book": 30.0,
    "program": 20.0,
    "rest": 10.0
  },
  "summary_sentence": "조용한 학습공간 중심으로 공부하기 좋은 도서관을 자주 찾고 있어요.",
  "analysis_basis": {
    "has_enough_data": true,
    "basis_text": "저장한 도서관, 책, 프로그램과 작성·좋아요한 후기를 바탕으로 분석했어요.",
    "signal_count": 5
  },
  "preference_status": {
    "status": "ready",
    "signal_count": 5,
    "calculated_at": "2026-06-25T12:00:00+09:00"
  }
}
```

`summary_sentence`는 API가 반환한 문장을 그대로 표시한다. v4 추천 판단은 `personal_recommendations`의 AI Recommendation Layer가 담당하며, 요약 문장 표현 보조와 추천 재랭킹은 Django 내부 provider 경계에서 분리해 관리한다. AI/GMS 실패·비활성·key 없음이면 규칙 기반 문장 또는 fallback provider 결과를 반환한다.

`preference_status.status` 값:

| 값 | 의미 |
|---|---|
| `collecting` | 행동 신호 수집 중 |
| `pending` | 변경 후 재계산 대기 |
| `ready` | 계산 완료 |
| `failed` | 계산 실패. 이후 요청에서 재시도 가능 |

## 8. 선호/개인화 API

### 8.1 선호 옵션

```http
GET /api/v1/preferences/options/
```

비로그인 조회 가능.

Response:

```json
{
  "purposes": [
    {
      "code": "study",
      "label": "공부",
      "description": "",
      "display_order": 1
    }
  ],
  "regions": [
    {
      "sido": "부산광역시",
      "sigungu": "강서구"
    }
  ],
  "tags": [
    {
      "code": "facility_wifi",
      "label": "무료 와이파이",
      "tag_group": "facility",
      "description": "",
      "display_order": 1
    }
  ]
}
```

### 8.2 내 수동 선호 조회/저장

```http
GET /api/v1/users/me/preferences/
PUT /api/v1/users/me/preferences/
```

인증 필요.

PUT request:

```json
{
  "purpose_codes": ["study", "book"],
  "regions": [
    {
      "sido": "부산광역시",
      "sigungu": "사상구"
    }
  ],
  "tag_codes": ["facility_wifi", "facility_lounge"]
}
```

Response:

```json
{
  "purposes": [
    {
      "code": "study",
      "label": "공부",
      "weight": "1.0000",
      "display_order": 0
    }
  ],
  "regions": [
    {
      "region_key": "21:사상구",
      "sido": "부산광역시",
      "sigungu": "사상구",
      "weight": "1.0000",
      "display_order": 0
    }
  ],
  "tags": [
    {
      "code": "facility_wifi",
      "label": "무료 와이파이",
      "weight": "1.0000",
      "display_order": 0
    }
  ]
}
```

수동 선호는 사용자가 직접 설정한 목적·지역·태그다. 행동 기반 성향은 저장/후기/좋아요 활동으로 계산되어 `UserPreference`/`UserPreferenceItem`에 저장되며, dashboard와 home personal 추천에서 사용된다.

## 9. Backend management command 계약

프론트에서 직접 호출하지 않는 운영용 command다. 실행 가이드와 시연 세팅에서 사용한다.

```bash
python manage.py seed_service_defaults
python manage.py sync_public_holidays --year 2026
python manage.py build_library_daily_schedules --year 2026
python manage.py rebuild_user_preferences --user-id 1
python manage.py rebuild_user_preferences --all
python manage.py import_popular_books --start-date 2026-06-01 --end-date 2026-06-07 --region 21
python manage.py enrich_book_details --source popular --limit 80
python manage.py import_busan_programs --start-date 2026-05-31 --end-date 2026-06-30
```

## 10. 프론트 연동 주의사항

- 저장/좋아요 상태는 `is_saved`, `is_liked` 필드에 의존하지 말고 나의 나들이 목록 hydration을 사용할 수 있다.
- 운영 상태의 `null`은 false가 아니라 unknown이다.
- 시설 `null`과 facility profile 부재는 false가 아니다.
- `holiday_operation_status`는 `holiday_status` 또는 `holiday_date` query가 있을 때만 목록 item에 포함된다.
- 후기 이미지와 프로필 이미지는 local dev에서 `/media/` URL로 제공된다.
- 프론트는 AI/GMS를 직접 호출하지 않는다. 프론트는 `summary_sentence`, `personal_recommendations.priority_tags`, `recommendation_reason`, `fallback_used`처럼 API가 반환한 필드만 표시한다.
