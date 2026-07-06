# 도서관 나들이 Codex 작업 지침

- 적용 범위: 저장소 전체
- 최종 갱신: 2026-07-06
- 핵심 원칙: 현재 백엔드 구현을 보호하면서, 공개 API와 프론트 구현 범위를 문서별로 분리한다.

## 0. 문서 권한과 적용 범위

### 0.1 판단 우선순위

문서나 구현이 서로 다를 때 다음 순서로 판단한다.

1. **검증된 현재 코드·migration·테스트·실행 결과**
2. **현재 공개 API의 Endpoint, Method, Request, Response, Status**
   - `library_outing_frontend_api_contract_v2.0.md` 내부 문서 버전 v4.0
3. **모델, FK, 제약조건, import, 태그·추천 도메인 정책**
   - `library_outing_ERD_v3.md` 내부 문서 버전 v4.0
   - `library_outing_Django_spec_v3.md` 내부 문서 버전 v4.0
4. **Frontend Route, Store, Service, Component, UI/UX**
   - `library_outing_frontend_spec_v3.md` 내부 문서 버전 v4.0
5. **기술 스택과 프로젝트 구성 요약**
   - 루트 `SKILLS.md`
6. 초기 아이디어, 목업, 과거 버전 명세

검증된 현재 구현과 문서가 다르면 백엔드를 자동으로 문서에 맞추지 않는다. 먼저 차이를 보고하고, 현재 구현을 유지할지 문서를 갱신할지 확인한다.

### 0.2 관심사별 최상위 기준

| 관심사 | 최상위 기준 |
|---|---|
| 모델, FK, `on_delete`, `related_name`, 제약조건, migration | ERD v4.0, Django 명세 v4.0, 실제 migration |
| import, 정규화, 외부 식별자, 태그 의미, 추천 도메인 규칙 | Django 명세 v4.0, ERD v4.0 |
| 현재 공개 Endpoint·Method·Payload·응답·Status | 프론트 전달용 API 계약 + 실제 URL/serializer 테스트 |
| Frontend Route·Store·Service·Component·UI/UX | Frontend 명세 v4.0 |
| 패키지·런타임·기술 선택 | `SKILLS.md`, 실제 설정 파일 |

Frontend 작업 중 API 계약과 Django v4의 예정 API가 다르면 **현재 공개 API 계약**을 따른다. 이 규칙은 백엔드 모델, migration, serializer 또는 view를 임의로 수정할 권한을 뜻하지 않는다.

### 0.3 인증 식별자 확정

현재 Django 인증의 로그인 식별자는 **이메일**이다. Django admin에서도 이메일과 비밀번호로 로그인하는 것이 확인되었다.

따라서 다음 규칙을 지킨다.

- `accounts.User`에 username 로그인을 새로 도입하지 않는다.
- 로그인 UI의 사용자 입력 의미는 이메일이다.
- 회원가입의 기본 사용자 입력은 이메일, 닉네임, 비밀번호다.
- 과거 API 계약이나 Frontend 문서에 있는 `username` 로그인 예시는 현재 구현과 충돌하는 **구형 예시**로 취급한다.
- 인증 API를 연결하기 전 실제 로그인 serializer의 요청 필드명을 확인한다.
- serializer가 호환 목적으로 `username`이라는 키에 이메일을 받는 경우, 이는 전송 필드명일 뿐 로그인 식별자가 username이라는 뜻이 아니다.
- 인증 계약 불일치를 발견해도 User 모델이나 serializer를 자동 변경하지 않고 먼저 보고한다.

## 1. 프로젝트 개요

서비스명은 **도서관 나들이**이다.

도서관 나들이는 부산 지역 도서관 데이터를 기반으로 도서관, 책, 문화 프로그램과 이용 후기를 탐색하고 저장하는 웹 애플리케이션이다. 1차 범위는 부산 지역 MVP이며 전국 확장 가능한 구조를 지향한다.

Backend 장기 설계에는 운영표, AI Recommendation Layer, 행동 성향 분석 등이 포함될 수 있다. 그러나 Frontend에는 현재 공개 API에서 실제 제공하는 기능만 노출한다.

## 2. 현재 API 범위와 Backend Roadmap

### 2.1 해석 원칙

```text
Django 명세 v4.0 / ERD v4.0
= Backend 최종 목표 구조와 도메인 정책

Frontend API 계약
= 현재 Frontend에 공개된 Endpoint와 Payload

Frontend 명세 v4.0
= 현재 API로 구현할 화면과 상호작용
```

모델이 존재한다는 사실은 현재 생성·수정 API가 공개되었다는 의미가 아니다.

### 2.2 현재 Frontend에서 보류하는 기능

다음 기능은 Backend 설계나 모델이 있더라도 현재 API 계약에 없으면 활성 UI로 구현하지 않는다.

- 후기 이미지 업로드
- 통합 나의 나들이 Dashboard
- 정밀 운영 상태와 고급 운영 필터
- 주간 인기 도서
- 비슷한 도서관
- hidden 후기 상태 UI
- 실시간 열람실 좌석
- 실시간 대출 가능 여부
- 내부 프로그램 신청·예약·결제

행동 기반 성향 분석, 사용자 취향 요약 문장, AI 개인 추천 순위는 v4 API 계약에 포함된 범위에서만 활성화한다.

## 3. 작업 원칙

### 3.1 Backend 보호

다음 항목은 명시적 요청 없이 변경하지 않는다.

- Django 앱 구조와 모델 소유권
- FK 방향
- `on_delete`
- `related_name`
- migration 순서와 기존 migration
- 환경변수 이름
- 태그 의미 분리 원칙
- 후기 저장 제거 및 좋아요 구조
- `Library.id` 기반 import 매칭
- 공휴일·운영표 정책
- AI Recommendation Layer / GMS 사용 경계
- 현재 공개 API Endpoint와 serializer 계약

모델 변경이 필요하면 먼저 다음 형식으로 제안한다.

```text
변경 제안:
- 대상 모델:
- 변경 내용:
- 변경 이유:
- v4 명세와 충돌 여부:
- 실제 migration 영향:
- 영향 받는 serializer/view/import/recommendation:
```

### 3.2 Frontend 작업 경계

Frontend 작업에서는 다음을 지킨다.

- Backend 모델, migration, serializer, view, URL을 임의로 수정하지 않는다.
- API 계약에 없는 Endpoint를 가정하지 않는다.
- 지원되지 않는 Query를 보내지 않는다.
- 응답에 없는 필드를 있다고 가정하지 않는다.
- 보류 기능을 카드, 버튼, 필터 또는 Route로 되살리지 않는다.
- API 계약 공백은 임의 구현하지 않고 `TBD` 또는 이슈로 남긴다.

### 3.3 기능 구현 순서

Backend 기능:

1. 모델·migration 확인
2. serializer 확인
3. service 함수 작성
4. view/API 작성
5. URL 연결
6. fixture/import 또는 테스트 데이터 확인
7. API 테스트
8. Frontend 연결

Frontend 기능:

1. API 계약과 현재 응답 확인
2. DTO 정의
3. service 함수 작성
4. Store 상태·Action 작성
5. Route·Page 연결
6. loading·empty·error 상태 구현
7. 권한·재시도·접근성 검증

## 4. 도메인 핵심 규칙

### 4.1 도서관 식별자

외부 파일과 API의 `library_name`, `sigungu`는 import 매칭 입력일 뿐 FK가 아니다. 매칭 이후 모든 관계는 내부 `Library.id`를 사용한다.

```text
source library_name + sigungu
→ normalize
→ Library exact / LibraryAlias / 검수된 correction map
→ Library.id 확정
→ 이후 모든 관계는 library_id 사용
```

모호하면 자동 연결하지 않고 reject report 또는 warning log에 남긴다. 주소·좌표만 같다는 이유로 자동 병합하지 않는다.

### 4.2 태그 정책

`Tag.code`는 의미 기준이다. 객관 시설 존재와 후기 체감은 반드시 분리한다.

```text
facility_parking           # 주차장 존재
review_parking_convenient  # 주차 편의 체감

facility_wifi              # 무료 와이파이 제공
review_wifi_reliable       # 와이파이 품질 체감
```

동일 `tag_id`가 여러 `source_method`로 생성된 경우에만 병합할 수 있다. 서로 다른 `tag_id`는 문구가 유사해도 병합하지 않는다.

`nearby`, `open_now`, `current_popular`처럼 요청이나 시점에 따라 달라지는 값은 영구 태그로 저장하지 않는다.

### 4.3 시설 데이터

`LibraryFacilityProfile`은 선택적 OneToOne이다.

- `True`: 시설 존재가 명시적으로 확인됨
- `False`: 원천에서 부재가 명시됨
- `NULL`: 필드가 확인되지 않음
- profile 행 부재: 해당 도서관 시설 데이터 자체가 미수집

긍정 시설 필터는 명시적 `True`만 통과시킨다. `NULL`이나 profile 부재를 `False`로 해석하지 않는다.

### 4.4 운영 여부

`open_today`와 `open_now`를 구분한다.

- `open_today`: 오늘 날짜의 `LibraryDailySchedule.status=open`
- `open_now`: 현재 시각이 알려진 운영 시간 구간 안에 있음

휴관 규칙과 운영시간이 충돌하면 `unknown`으로 판정한다. 공휴일 관련 운영 판정은 해당 연도 달력이 완전할 때만 신뢰한다.

현재 공개 API가 이 상태를 제공하지 않으면 Frontend에서 자체 계산하거나 표시하지 않는다.

### 4.5 홈 공개 테마

홈 공개 테마는 다음 5개다.

```text
study
book
kids
mood
nearby
```

`program` 목적은 프로필 선택과 프로그램형 분석·개인화에는 사용할 수 있지만 홈 공개 테마에는 포함하지 않는다.

### 4.6 후기 정책

- 본문 1~200자
- 경험 태그 1~5개
- 선택적 관련 책·프로그램
- 별도 제목 없음
- 별점 없음
- 방문 목적 FK 없음
- 후기 저장 모델 없음

`UserReviewLike`가 좋아요 원본 관계이고 `like_count`는 집계 캐시다. 후기 이미지 모델이 존재하더라도 현재 업로드 API가 보류되어 있으면 Frontend 업로드 UI를 만들지 않는다.

### 4.7 저장·좋아요 상태

현재 API 응답에 `is_saved`, `is_liked`가 없다면 이를 있다고 가정하지 않는다.

Frontend는 현재 계약에서 다음 목록을 이용해 상태를 hydration할 수 있다.

```text
/my-outings/libraries/      → savedLibraryIds
/my-outings/books/          → savedBookIsbns
/my-outings/programs/       → savedProgramIds
/my-outings/liked-reviews/  → likedReviewIds
```

추후 API가 `is_saved`, `is_liked`를 공식 추가하면 해당 필드를 우선하고 hydration을 fallback으로 축소한다.

### 4.8 이미지 정책

공식 외부 이미지, 시스템 대체 이미지, 사용자 업로드 이미지를 구분한다.

공식 외부 이미지가 활성 상태라면 `license_code`, `attribution_text`가 필요하다. 대체 이미지는 엔터티 관계에 삽입하지 않고 serializer/service에서 fallback으로 해석한다.

ⓘ는 hover·focus·tap 시 전체 출처문구를 이미지 위에 표시하는 UI 계약이다.

## 5. 인증과 세션 규칙

- 로그인 식별자: 이메일
- access token: Frontend 메모리 상태에서 사용
- refresh token: HttpOnly Cookie
- API 요청: `Authorization: Bearer <access_token>`
- 401: 단일 refresh 요청 후 원 요청 1회 재시도
- refresh 실패: 인증 상태와 사용자별 Store를 초기화하고 로그인으로 이동
- 로그인 후 복귀: 내부 `redirect` Query 사용
- 로그아웃: refresh Cookie 제거 요청 후 전체 Pinia Store 초기화

인증 Endpoint·Cookie 속성·CORS/CSRF 설정은 현재 Backend 코드와 API 테스트를 기준으로 확인한다.

## 6. 외부 API와 API Key

### 6.1 서버 비밀키

다음 값은 Frontend에 전달하지 않는다.

- `DATA4LIBRARY_API_KEY`
- `DATA_GO_KR_API_KEY`
- `GMS_API_KEY`
- Django Secret Key
- Kakao REST API Key
- Kakao Admin Key

로그, cache key, 오류 응답에서 인증 값을 마스킹한다.

### 6.2 Kakao JavaScript Key 예외

Kakao Map JavaScript Key는 브라우저 SDK용 공개 식별자이므로 다음 변수로 Frontend에서 사용할 수 있다.

```text
VITE_KAKAO_MAP_JAVASCRIPT_KEY
```

다음 조건을 지킨다.

- Kakao Developers에서 JavaScript SDK 허용 도메인을 제한한다.
- 개발 환경과 배포 환경 도메인을 등록한다.
- Kakao REST API Key와 Admin Key는 Frontend에 넣지 않는다.
- 지도 SDK는 도서관 상세에서 필요할 때 동적으로 로드한다.

### 6.3 AI Recommendation Layer와 GMS

v4에서는 AI를 단순 문장 표현 보조가 아니라 사용자 성향 분석, 우선 태그 산출, 후보 재랭킹, 추천 이유 생성에 사용할 수 있다.

추천 흐름은 다음 순서를 따른다.

권장 흐름:

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

다음 경계를 반드시 지킨다.

- 전체 도서관 raw data를 AI 입력으로 직접 넣지 않는다.
- AI Planner 입력은 사용자 행동 요약, 수동 선호, 사용 가능한 `Tag.code` 목록으로 제한한다.
- AI Reranker 입력은 Django가 10~20개로 줄인 후보 도서관의 요약 feature로 제한한다.
- AI는 도서관 존재 여부, 시설 여부, 운영 여부, 책·프로그램·후기 존재 여부, 이미지·출처·라이선스 같은 원천 사실을 생성하거나 수정하지 않는다.
- AI 출력은 구조화 JSON이어야 하며 Django에서 `library_id`, `tag_code`, 활성 도서관, 운영 필수 조건, JSON schema를 검증한다.
- 검증 실패, timeout, quota 초과, `GMS_API_KEY` 만료·미설정 시 mock 또는 rule-based fallback provider로 응답 흐름이 성립해야 한다.
- 기존 rule-based 추천은 주 추천기가 아니라 fallback/baseline이다.
- provider 구조는 `GMSChatRecommendationProvider`, `MockRecommendationProvider`, `RuleBasedFallbackRecommendationProvider`, 추후 `FineTunedRecommendationProvider`로 교체 가능해야 한다.

## 7. REST API 원칙

- Base URL과 공개 Endpoint는 API 계약을 따른다.
- 조회: GET
- 생성·좋아요·저장: 계약에 정의된 POST
- 전체 수정: PUT
- 부분 수정: PATCH
- 삭제·저장 해제·좋아요 해제: DELETE
- status code와 응답 body는 실제 API 테스트를 기준으로 처리한다.
- 외부 API 실패를 정상 빈 결과와 구분한다.

## 8. 코드 작성 규칙

- 의미가 드러나는 이름을 사용한다.
- view 안에 외부 API 호출이나 도메인 계산을 길게 작성하지 않는다.
- 외부 API client는 `integrations` 또는 service 모듈로 분리한다.
- 추천, import, normalization, matching 로직은 view와 분리한다.
- serializer는 목록·상세·생성/수정 목적에 따라 분리할 수 있다.
- 교차 앱 FK는 문자열 참조를 사용한다.
- 사용자 FK는 `settings.AUTH_USER_MODEL`을 사용한다.
- canonical 데이터는 도메인 정책에 맞는 `is_active`, `is_visible`, `deleted_at`을 우선한다.
- Frontend 디렉터리, Route, Store, Service 구조는 Frontend 명세 v4.0을 따른다.

## 9. 테스트와 검증

우선 테스트 대상:

- 이메일 로그인과 refresh Cookie
- 인증 실패·refresh 실패·로그아웃
- 도서관명 정규화와 매칭
- 시설 `True/False/NULL` 처리
- 공휴일 완전성 및 운영표 계산
- 후기 작성 검증
- 후기 좋아요 idempotent 처리
- 추천 후보와 태그 규칙
- 외부 API 503과 정상 빈 결과 구분
- Kakao 지도 좌표 없음·SDK 실패 fallback
- 저장·좋아요 hydration

## 10. Git 작업 제한

Codex는 명시적으로 요청받지 않는 한 다음 작업을 수행하지 않는다.

- branch 생성·변경
- commit
- push
- merge
- rebase
- reset
- tag 생성

`git status`, `git diff`, `git log` 같은 읽기 작업은 검토 목적으로 사용할 수 있다.

## 11. 절대 하지 말 것

- 검증된 현재 Backend를 구형 문서에 맞추기 위해 자동 수정하지 말 것
- username 로그인을 새로 도입하지 말 것
- API 계약에 없는 Endpoint나 필드를 가정하지 말 것
- 현재 보류 기능을 활성 UI로 구현하지 말 것
- Backend 모델·migration을 Frontend 편의를 위해 임의 변경하지 말 것
- 후기 저장 모델을 만들지 말 것
- 후기 별점·제목·방문 목적 FK를 추가하지 말 것
- 후기 이미지 업로드 API가 없는데 업로드 UI를 만들지 말 것
- 외부 `library_name`을 FK처럼 사용하지 말 것
- 서버 비밀키를 Frontend에 노출하지 말 것
- Kakao JavaScript Key를 서버 비밀키처럼 Proxy하려고 하지 말 것
- AI/GMS가 원천 사실을 생성하거나 DB 사실을 수정하게 하지 말 것
- 전체 도서관 raw data를 AI에 직접 전달하지 말 것
- `NULL` 시설을 `False`로 처리하지 말 것
- `00:00~00:00`을 24시간 운영으로 자동 해석하지 말 것
- 객관 시설 태그와 후기 체감 태그를 합치지 말 것
- 대체 이미지를 실제 엔터티 이미지 관계에 삽입하지 말 것
- 주소·좌표만 같다는 이유로 도서관을 자동 병합하지 말 것
- 전체 장서를 사전 적재하지 말 것
