# 도서관 나들이 프론트 전달용 API 계약 문서 v1.1

## 0. 공통 규칙

### Base URL

```text
/api/v1
```

### 인증 방식

로그인 후 발급받은 access token을 필요한 요청에 아래처럼 포함한다.

```http
Authorization: Bearer <access_token>
```

refresh token은 응답 body가 아니라 HttpOnly Cookie로 관리된다.

인증 식별자는 이메일이다. 로그인 요청에는 `email`과 `password`를 사용하며, `username`은 현재 API 계약에서 사용하지 않는다.

### Pagination 응답

목록형 API는 기본적으로 아래 wrapper를 사용한다.

```json
{
  "count": 220,
  "next": "http://.../api/v1/libraries/?page=2",
  "previous": null,
  "results": []
}
```

공통 query parameter:

```text
page
page_size
```

기본 page_size는 API별 기본값을 따르며, 일부 API는 최대 100으로 제한된다.

### thumbnail 공통 구조

도서관 카드에는 thumbnail이 포함될 수 있다.

```json
{
  "url": "/static/media_assets/placeholders/default_library_small.png",
  "is_fallback": true,
  "fallback_key": "library/small",
  "license_code": "internal",
  "attribution_text": null
}
```

`is_fallback=true`면 실제 도서관 사진이 아니라 기본 이미지다.

---

# 1. 인증 API

## 1.1 회원가입

```http
POST /api/v1/auth/signup/
```

### Request

```json
{
  "email": "outing@example.com",
  "password": "password1234",
  "nickname": "도서관나들이"
}
```

`username`은 전송하지 않는다.

### Response `201`

```json
{
  "access": "access_token",
  "user": {
    "id": 1,
    "email": "outing@example.com",
    "nickname": "도서관나들이"
  }
}
```

refresh token은 HttpOnly Cookie로 설정된다.

---

## 1.2 로그인

```http
POST /api/v1/auth/login/
```

### Request

```json
{
  "email": "outing@example.com",
  "password": "password1234"
}
```

로그인 식별자는 이메일이다.

### Response `200`

```json
{
  "access": "access_token",
  "user": {
    "id": 1,
    "email": "outing@example.com",
    "nickname": "도서관나들이"
  }
}
```

---

## 1.3 토큰 갱신

```http
POST /api/v1/auth/token/refresh/
```

refresh token cookie가 있으면 access token을 새로 발급한다.

### Response `200`

```json
{
  "access": "new_access_token"
}
```

---

## 1.4 로그아웃

```http
POST /api/v1/auth/logout/
```

### Response `200`

```json
{
  "detail": "Successfully logged out."
}
```

refresh token cookie가 삭제된다.

---

## 1.5 내 정보 조회

```http
GET /api/v1/users/me/
```

인증 필요.

### Response `200`

```json
{
  "id": 1,
  "email": "outing@example.com",
  "nickname": "도서관나들이"
}
```

---

## 1.6 내 정보 수정

```http
PATCH /api/v1/users/me/
```

인증 필요.

### Request

```json
{
  "nickname": "김나들이"
}
```

### Response `200`

```json
{
  "id": 1,
  "email": "outing@example.com",
  "nickname": "김나들이"
}
```

---

# 2. 홈/추천 API

## 2.1 홈 추천 조회

```http
GET /api/v1/home/
```

비로그인 조회 가능. 로그인 사용자는 access token을 포함하면 personal 추천이 활성화될 수 있다.

### Query Parameters

```text
lat optional
lng optional
```

`lat`, `lng`가 있으면 nearby 추천에서 거리순 정렬을 시도한다.

### Response `200`

```json
{
  "today_recommendations": {
    "theme": {
      "code": "family_outing",
      "title": "가족 나들이처럼 들르기 좋은 도서관이에요",
      "subtitle": "어린이자료실과 가족 방문에 어울리는 공간을 기준으로 골랐어요."
    },
    "items": [
      {
        "id": 1,
        "name": "송정동어린이작은도서관",
        "library_type": "small",
        "sido": "부산광역시",
        "sigungu": "해운대구",
        "road_address": "...",
        "latitude": "35.1836603",
        "longitude": "129.2037147",
        "book_count": 2813,
        "reading_seat_count": 20,
        "thumbnail": {},
        "recommendation_reason": "아이와 함께 가기 좋은 도서관이에요."
      }
    ]
  },
  "theme_recommendations": [
    {
      "purpose": {
        "code": "study",
        "label": "공부하기 좋은 곳"
      },
      "items": []
    },
    {
      "purpose": {
        "code": "book",
        "label": "책을 빌리러 가요"
      },
      "items": []
    },
    {
      "purpose": {
        "code": "kids",
        "label": "아이와 함께 가요"
      },
      "items": []
    },
    {
      "purpose": {
        "code": "mood",
        "label": "분위기 좋은 곳에 머물고 싶어요"
      },
      "items": []
    },
    {
      "purpose": {
        "code": "nearby",
        "label": "가까운 곳이 좋아요"
      },
      "items": []
    }
  ],
  "personal_recommendations": {
    "available": false,
    "reason": "로그인 후 선호 목적과 지역을 설정하면 맞춤 추천을 볼 수 있어요.",
    "items": []
  }
}
```

### 비고

* 오늘의 추천: 최대 3개
* 테마별 추천: 5개 테마, 각 최대 6개
* 개인 추천: 최대 3개
* `program` purpose는 홈 테마 추천에서 제외된다.
* 추천은 GMS/AI가 아니라 규칙 기반이다.

---

# 3. 도서관 API

## 3.1 도서관 목록 조회

```http
GET /api/v1/libraries/
```

### Query Parameters

```text
page
page_size
q
sigungu
library_type
```

### Response `200`

```json
{
  "count": 220,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "송정동어린이작은도서관",
      "library_type": "small",
      "sido": "부산광역시",
      "sigungu": "해운대구",
      "road_address": "...",
      "latitude": "35.1836603",
      "longitude": "129.2037147",
      "book_count": 2813,
      "reading_seat_count": 20,
      "thumbnail": {
        "url": "/static/media_assets/placeholders/default_library_small.png",
        "is_fallback": true,
        "fallback_key": "library/small",
        "license_code": "internal",
        "attribution_text": null
      }
    }
  ]
}
```

---

## 3.2 도서관 상세 조회

```http
GET /api/v1/libraries/{library_id}/
```

### Response `200`

```json
{
  "id": 1,
  "name": "송정동어린이작은도서관",
  "library_type": "small",
  "sido": "부산광역시",
  "sigungu": "해운대구",
  "road_address": "...",
  "latitude": "35.1836603",
  "longitude": "129.2037147",
  "phone": "...",
  "homepage_url": "...",
  "operating_agency": "...",
  "short_description": "...",
  "book_count": 2813,
  "reading_seat_count": 20,
  "thumbnail": {},
  "statistics": {
    "book_count": 2813,
    "non_book_count": 0,
    "serial_count": 0,
    "reading_seat_count": 20,
    "building_area": null,
    "site_area": null
  },
  "facility_profile": {
    "has_reading_room": true,
    "has_children_room": false,
    "has_digital_room": false,
    "has_parking": false,
    "has_cafe": false,
    "has_wifi": true,
    "has_nursing_room": false,
    "has_accessible_facility": false,
    "has_elevator": false,
    "has_lounge": false,
    "has_outdoor_space": false
  },
  "opening_hours": [],
  "closure_rules": []
}
```

---

## 3.3 도서관 저장

```http
POST /api/v1/libraries/{library_id}/save/
```

인증 필요.

### Response `201` 또는 `200`

```json
{
  "saved": true,
  "target_type": "library",
  "target_id": 1
}
```

이미 저장되어 있어도 `200`으로 안정 응답한다.

---

## 3.4 도서관 저장 취소

```http
DELETE /api/v1/libraries/{library_id}/save/
```

인증 필요.

### Response `200`

```json
{
  "saved": false,
  "target_type": "library",
  "target_id": 1
}
```

이미 저장 취소 상태여도 `200`으로 안정 응답한다.

---

# 4. 책 API

## 4.1 책 목록 조회

```http
GET /api/v1/books/
```

DB에 저장된 책 목록을 조회한다.

### Query Parameters

```text
page
page_size
q
```

### Response `200`

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

---

## 4.2 책 상세 조회

```http
GET /api/v1/books/{isbn13}/
```

### Response `200`

```json
{
  "isbn13": "9788936434120",
  "title": "책 제목",
  "authors_text": "저자",
  "publisher": "출판사",
  "publication_year": "2020",
  "kdc_class_no": "800",
  "kdc_class_name": "문학",
  "cover_image_url": "...",
  "source_detail_url": "...",
  "loan_count": 123
}
```

---

## 4.3 정보나루 책 검색

```http
GET /api/v1/books/search/
```

### Query Parameters

```text
search_type=title|author|isbn|keyword|publisher
q
title
author
isbn13
keyword
publisher
page
page_size
```

예시:

```http
GET /api/v1/books/search/?search_type=title&q=테스트
```

### Response `200`

```json
{
  "source": "data4library",
  "num_found": 520,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "isbn13": "978...",
      "title": "책 제목",
      "authors_text": "저자",
      "publisher": "출판사",
      "publication_year": "2020",
      "kdc_class_no": "800",
      "kdc_class_name": "문학",
      "cover_image_url": "...",
      "source_detail_url": "...",
      "loan_count": 123,
      "local_book_id": null
    }
  ]
}
```

### API Key Missing `503`

```json
{
  "detail": "Data4Library API key is not configured."
}
```

---

## 4.4 책 소장 도서관 조회

```http
GET /api/v1/books/{isbn13}/libraries/
```

공개 조회 API.

정보나루 `libSrchByBook`을 사용하며, 현재는 부산 지역 `region=21` 기준으로 조회한다.

### Query Parameters

```text
page
page_size
```

`page_size` 최대 100.

### Response `200`

```json
{
  "isbn13": "9788936434120",
  "source": "data4library",
  "count": 2,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "matched": true,
      "library": {
        "id": 1,
        "name": "부산광역시립시민도서관",
        "library_type": "public",
        "sido": "부산광역시",
        "sigungu": "부산진구",
        "road_address": "...",
        "latitude": "...",
        "longitude": "...",
        "thumbnail": {}
      },
      "external_library": {
        "provider_code": "data4library",
        "external_library_key": "123456",
        "name": "부산광역시립시민도서관",
        "address": "...",
        "homepage_url": "...",
        "phone": "...",
        "latitude": "...",
        "longitude": "..."
      },
      "holding": {
        "call_number": null,
        "loan_available": null,
        "loan_status": null
      }
    },
    {
      "matched": false,
      "library": null,
      "external_library": {
        "provider_code": "data4library",
        "external_library_key": "999999",
        "name": "외부 도서관명",
        "address": "...",
        "homepage_url": "...",
        "phone": "...",
        "latitude": "...",
        "longitude": "..."
      },
      "holding": {
        "call_number": null,
        "loan_available": null,
        "loan_status": null
      }
    }
  ]
}
```

### 비고

현재 `LibraryExternalIdentifier`가 비어 있으면 대부분 `matched=false`가 정상이다.
추후 매칭 데이터가 채워지면 같은 API 구조에서 내부 도서관 상세 연결이 가능해진다.

---

## 4.5 책 저장

```http
POST /api/v1/books/{isbn13}/save/
```

인증 필요.

### Response `201` 또는 `200`

```json
{
  "saved": true,
  "target_type": "book",
  "target_id": "9788936434120"
}
```

---

## 4.6 책 저장 취소

```http
DELETE /api/v1/books/{isbn13}/save/
```

인증 필요.

### Response `200`

```json
{
  "saved": false,
  "target_type": "book",
  "target_id": "9788936434120"
}
```

---

# 5. 프로그램 API

## 5.1 프로그램 목록 조회

```http
GET /api/v1/programs/
```

### Query Parameters

```text
page
page_size
q
library_id
sigungu
category
target
application_status
operation_status
```

### Response `200`

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "문화 프로그램명",
      "library": {
        "id": 1,
        "name": "도서관명",
        "sigungu": "해운대구"
      },
      "category": "lecture",
      "category_display": "강연/인문학",
      "target": ["adult"],
      "target_display": ["성인"],
      "application_start_date": "2026-06-01",
      "application_end_date": "2026-06-10",
      "application_status": "available",
      "operation_start_date": "2026-06-15",
      "operation_end_date": "2026-06-30",
      "operation_status": "upcoming",
      "source_board": "독서문화행사",
      "source_url": "https://..."
    }
  ]
}
```

현재 프로그램 데이터는 import 전이면 `count=0`일 수 있다.

---

## 5.2 프로그램 상세 조회

```http
GET /api/v1/programs/{program_id}/
```

### Response `200`

```json
{
  "id": 1,
  "title": "문화 프로그램명",
  "library": {
    "id": 1,
    "name": "도서관명",
    "sigungu": "해운대구"
  },
  "category": "lecture",
  "category_display": "강연/인문학",
  "target": ["adult"],
  "target_display": ["성인"],
  "application_start_date": "2026-06-01",
  "application_end_date": "2026-06-10",
  "application_status": "available",
  "operation_start_date": "2026-06-15",
  "operation_end_date": "2026-06-30",
  "operation_status": "upcoming",
  "source_sido": "부산광역시",
  "source_sigungu": "해운대구",
  "source_library_name": "도서관명",
  "provider_code": "busan_library_portal",
  "external_program_key": "...",
  "source_board": "독서문화행사",
  "source_url": "https://...",
  "post_date": "2026-06-01",
  "collected_at": "2026-06-24T00:00:00+09:00",
  "tags": []
}
```

---

## 5.3 프로그램 저장

```http
POST /api/v1/programs/{program_id}/save/
```

인증 필요.

### Response `201` 또는 `200`

```json
{
  "saved": true,
  "target_type": "program",
  "target_id": 1
}
```

---

## 5.4 프로그램 저장 취소

```http
DELETE /api/v1/programs/{program_id}/save/
```

인증 필요.

### Response `200`

```json
{
  "saved": false,
  "target_type": "program",
  "target_id": 1
}
```

---

# 6. 커뮤니티 후기 API

## 6.1 후기 목록 조회

```http
GET /api/v1/reviews/
```

### Query Parameters

```text
page
page_size
q
library_id
tag
user_id
ordering
```

`ordering` 허용값:

```text
-created_at
-view_count
-like_count
```

### Response `200`

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "library": {
        "id": 1,
        "name": "도서관명",
        "sigungu": "해운대구"
      },
      "user": {
        "id": 1,
        "nickname": "김나들이"
      },
      "content": "조용하고 좋았어요.",
      "view_count": 0,
      "like_count": 0,
      "comment_count": 0,
      "created_at": "2026-06-24T00:00:00+09:00",
      "updated_at": "2026-06-24T00:00:00+09:00",
      "tags": [],
      "images": [],
      "related_books": [],
      "related_programs": []
    }
  ]
}
```

---

## 6.2 후기 상세 조회

```http
GET /api/v1/reviews/{review_id}/
```

### Response `200`

```json
{
  "id": 1,
  "library": {
    "id": 1,
    "name": "도서관명",
    "sigungu": "해운대구"
  },
  "user": {
    "id": 1,
    "nickname": "김나들이"
  },
  "content": "조용하고 좋았어요.",
  "view_count": 0,
  "like_count": 0,
  "comment_count": 0,
  "created_at": "2026-06-24T00:00:00+09:00",
  "updated_at": "2026-06-24T00:00:00+09:00",
  "tags": [],
  "images": [],
  "related_books": [],
  "related_programs": []
}
```

---

## 6.3 후기 작성

```http
POST /api/v1/reviews/
```

인증 필요.

### Request

```json
{
  "library_id": 1,
  "content": "조용하고 좋았어요.",
  "tag_codes": ["quiet", "study"],
  "book_ids": ["9788936434120"],
  "program_ids": [1]
}
```

### Response `201`

```json
{
  "id": 1,
  "library": {},
  "user": {},
  "content": "조용하고 좋았어요.",
  "view_count": 0,
  "like_count": 0,
  "comment_count": 0,
  "created_at": "2026-06-24T00:00:00+09:00",
  "updated_at": "2026-06-24T00:00:00+09:00",
  "tags": [],
  "images": [],
  "related_books": [],
  "related_programs": []
}
```

### 작성 제한

* `library_id` 필수
* `content` 1~200자
* `tag_codes` 1~5개
* 후기 선택 가능 태그만 허용
* 연결 프로그램은 같은 도서관의 프로그램만 허용

---

## 6.4 후기 수정

```http
PATCH /api/v1/reviews/{review_id}/
```

인증 필요. 작성자만 수정 가능.

### Request

```json
{
  "content": "수정한 후기입니다.",
  "tag_codes": ["quiet"]
}
```

### Response `200`

```json
{
  "id": 1,
  "content": "수정한 후기입니다."
}
```

실제 응답은 후기 상세 구조와 동일하다.

---

## 6.5 후기 삭제

```http
DELETE /api/v1/reviews/{review_id}/
```

인증 필요. 작성자만 삭제 가능.

### Response `204`

body 없음.

현재는 사용자 삭제 시 물리 삭제한다.

---

## 6.6 후기 댓글 목록

```http
GET /api/v1/reviews/{review_id}/comments/
```

공개 조회 가능. 후기 댓글은 추천, 취향, 태그, 좋아요와 연결하지 않는다.

### Response `200`

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "review_id": 10,
      "user": {
        "id": 1,
        "nickname": "김나들이"
      },
      "content": "저도 여기 좋았어요.",
      "created_at": "2026-06-25T00:00:00+09:00",
      "updated_at": "2026-06-25T00:00:00+09:00"
    }
  ]
}
```

---

## 6.7 후기 댓글 작성

```http
POST /api/v1/reviews/{review_id}/comments/
```

인증 필요.

### Request

```json
{
  "content": "저도 여기 좋았어요."
}
```

### Response `201`

댓글 상세 구조와 동일하다.

### 작성 제한

* `content` 1~200자
* 공백만 있는 댓글은 허용하지 않는다.

---

## 6.8 후기 댓글 상세·수정·삭제

```http
GET /api/v1/reviews/{review_id}/comments/{comment_id}/
PATCH /api/v1/reviews/{review_id}/comments/{comment_id}/
DELETE /api/v1/reviews/{review_id}/comments/{comment_id}/
```

상세 조회는 공개 가능. 수정·삭제는 인증 필요하며 작성자만 가능하다. 삭제는 물리 삭제한다.

### PATCH Request

```json
{
  "content": "수정한 댓글입니다."
}
```

### DELETE Response `204`

body 없음.

---

## 6.9 후기 좋아요

```http
POST /api/v1/reviews/{review_id}/like/
```

인증 필요.

### Response `201` 또는 `200`

```json
{
  "liked": true,
  "review_id": 1,
  "like_count": 1
}
```

이미 좋아요한 상태여도 안정 응답한다.

---

## 6.10 후기 좋아요 취소

```http
DELETE /api/v1/reviews/{review_id}/like/
```

인증 필요.

### Response `200`

```json
{
  "liked": false,
  "review_id": 1,
  "like_count": 0
}
```

이미 좋아요 취소 상태여도 안정 응답한다.

---

# 7. 선호 설정 API

## 7.1 선호 옵션 조회

```http
GET /api/v1/preferences/options/
```

비로그인 조회 가능.

### Response `200`

```json
{
  "purposes": [
    {
      "code": "study",
      "label": "공부하기 좋은 곳",
      "description": "...",
      "display_order": 0
    }
  ],
  "regions": [
    {
      "region_key": "21:해운대구",
      "sido": "부산광역시",
      "sigungu": "해운대구",
      "label": "해운대구"
    }
  ],
  "tags": [
    {
      "code": "facility_parking",
      "label": "주차장",
      "tag_group": "facility",
      "description": "...",
      "display_order": 0
    }
  ]
}
```

---

## 7.2 내 선호 조회

```http
GET /api/v1/users/me/preferences/
```

인증 필요.

### Response `200`

```json
{
  "purposes": [
    {
      "code": "study",
      "label": "공부하기 좋은 곳",
      "weight": "1.0000",
      "display_order": 0
    }
  ],
  "regions": [
    {
      "region_key": "21:해운대구",
      "sido": "부산광역시",
      "sigungu": "해운대구",
      "weight": "1.0000",
      "display_order": 0
    }
  ],
  "tags": [
    {
      "code": "facility_parking",
      "label": "주차장",
      "weight": "1.0000",
      "display_order": 0
    }
  ]
}
```

---

## 7.3 내 선호 수정

```http
PUT /api/v1/users/me/preferences/
```

인증 필요. 전체 교체 방식이다.

### Request

```json
{
  "purpose_codes": ["study", "book", "program"],
  "regions": [
    {
      "sido": "부산광역시",
      "sigungu": "해운대구"
    },
    {
      "sido": "부산광역시",
      "sigungu": "동래구"
    }
  ],
  "tag_codes": ["facility_parking", "facility_wifi", "facility_lounge"]
}
```

### Response `200`

수정 후 `GET /api/v1/users/me/preferences/`와 같은 구조를 반환한다.

### 비고

* 중복 입력은 순서 유지 후 제거된다.
* 빈 배열을 보내면 해당 선호 영역이 모두 비활성화된다.
* 존재하지 않는 purpose/tag/region은 `400`.

---

# 8. 나의 나들이 API

모든 API 인증 필요.

## 8.1 저장한 도서관 목록

```http
GET /api/v1/my-outings/libraries/
```

### Response `200`

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "memo": "",
      "created_at": "2026-06-24T00:00:00+09:00",
      "updated_at": "2026-06-24T00:00:00+09:00",
      "library": {
        "id": 1,
        "name": "도서관명",
        "library_type": "public",
        "sido": "부산광역시",
        "sigungu": "해운대구",
        "road_address": "...",
        "latitude": "...",
        "longitude": "...",
        "book_count": 10000,
        "reading_seat_count": 100,
        "thumbnail": {}
      }
    }
  ]
}
```

---

## 8.2 저장한 책 목록

```http
GET /api/v1/my-outings/books/
```

### Response `200`

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "memo": "",
      "created_at": "2026-06-24T00:00:00+09:00",
      "updated_at": "2026-06-24T00:00:00+09:00",
      "book": {
        "isbn13": "9788936434120",
        "title": "책 제목",
        "authors_text": "저자",
        "publisher": "출판사",
        "publication_year": "2020",
        "cover_image_url": "..."
      }
    }
  ]
}
```

---

## 8.3 저장한 프로그램 목록

```http
GET /api/v1/my-outings/programs/
```

### Response `200`

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "memo": "",
      "created_at": "2026-06-24T00:00:00+09:00",
      "updated_at": "2026-06-24T00:00:00+09:00",
      "program": {
        "id": 1,
        "title": "문화 프로그램명",
        "library": {
          "id": 1,
          "name": "도서관명",
          "sigungu": "해운대구"
        },
        "category": "lecture",
        "category_display": "강연/인문학",
        "target": [],
        "target_display": [],
        "operation_start_date": "2026-06-15",
        "operation_end_date": "2026-06-30",
        "operation_status": "upcoming"
      }
    }
  ]
}
```

---

## 8.4 내가 쓴 후기 목록

```http
GET /api/v1/my-outings/reviews/
```

### Response `200`

기존 후기 serializer 구조를 pagination으로 반환한다.

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "library": {},
      "user": {},
      "content": "내가 쓴 후기",
      "view_count": 0,
      "like_count": 0,
      "comment_count": 0,
      "created_at": "2026-06-24T00:00:00+09:00",
      "updated_at": "2026-06-24T00:00:00+09:00",
      "tags": [],
      "images": [],
      "related_books": [],
      "related_programs": []
    }
  ]
}
```

---

## 8.5 내가 쓴 댓글 목록

```http
GET /api/v1/my-outings/comments/
```

인증 필요. 사용자가 작성한 댓글을 최신순 pagination으로 반환한다.

### Response `200`

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": {
        "id": 1,
        "nickname": "김나들이"
      },
      "content": "저도 좋았어요.",
      "created_at": "2026-06-25T00:00:00+09:00",
      "updated_at": "2026-06-25T00:00:00+09:00",
      "review": {
        "id": 10,
        "library": {},
        "user": {},
        "content": "댓글을 단 후기",
        "view_count": 0,
        "like_count": 0,
        "comment_count": 1,
        "created_at": "2026-06-24T00:00:00+09:00",
        "updated_at": "2026-06-24T00:00:00+09:00",
        "tags": [],
        "images": [],
        "related_books": [],
        "related_programs": []
      }
    }
  ]
}
```

---

## 8.6 좋아요한 후기 목록

```http
GET /api/v1/my-outings/liked-reviews/
```

### Response `200`

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "liked_at": "2026-06-24T00:00:00+09:00",
      "review": {
        "id": 10,
        "library": {},
        "user": {},
        "content": "좋아요한 후기",
        "view_count": 0,
        "like_count": 1,
        "comment_count": 0,
        "created_at": "2026-06-24T00:00:00+09:00",
        "updated_at": "2026-06-24T00:00:00+09:00",
        "tags": [],
        "images": [],
        "related_books": [],
        "related_programs": []
      }
    }
  ]
}
```

---

# 9. 에러 응답

## 인증 실패 `401`

```json
{
  "detail": "Authentication credentials were not provided."
}
```

또는 토큰 상태에 따라 JWT 관련 detail이 반환될 수 있다.

## 권한 없음 `403`

```json
{
  "detail": "You do not have permission to perform this action."
}
```

## 존재하지 않는 리소스 `404`

```json
{
  "detail": "Not found."
}
```

## 검증 실패 `400`

필드별 오류 구조가 반환될 수 있다.

```json
{
  "tag_codes": ["후기 태그는 1개 이상 선택해야 합니다."]
}
```

## 외부 API Key 없음 `503`

```json
{
  "detail": "Data4Library API key is not configured."
}
```

---

# 10. 프론트 우선 연결 추천 순서

## 1차 화면 연결

```text
1. 인증
2. 홈
3. 도서관 목록/상세
4. 책 검색
5. 책 소장 도서관
6. 프로그램 목록/상세
7. 저장/저장 목록
8. 후기 목록/작성/좋아요
9. 선호 설정
```

## 주의할 데이터 상태

```text
도서관 데이터: 있음
도서관 시설 데이터: 일부 있음
도서관 이미지: 일부 있음, 없으면 fallback 이미지
프로그램 데이터: import 전이면 0건 가능
책 데이터: 검색 시 정보나루 API 사용
책 소장 도서관: 현재 내부 매칭 데이터가 없어 matched=false가 많을 수 있음
후기 데이터: 초기 0건
LibraryTag: 현재 0건
운영표: 현재 0건
```

## 현재 의도적으로 보류된 기능

```text
open_today / open_now 정밀 계산
프로그램 크롤링/import
LibraryExternalIdentifier 매칭 seed/import
LibraryHolding 저장/캐싱
행동 기반 개인화 추천
사용자 취향 요약 문장
GMS/AI 문구 생성
후기 이미지 업로드
통합 나의 나들이 대시보드
```
