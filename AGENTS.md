## 0. 최상위 기준 문서

이 프로젝트의 최상위 기준 문서는 다음 두 파일이다.

* `docs/library_outing_ERD_v3.md`
* `docs/library_outing_Django_spec_v3.md`

모델, 앱 구조, API, import, 추천 로직, 태그 정책, 저장 정책, 삭제 정책, 환경변수, migration 순서는 위 두 문서를 우선한다.

두 문서와 충돌하는 구현을 하지 않는다. 충돌하거나 애매한 경우 코드를 수정하지 말고 먼저 질문한다.

## 1. 프로젝트 개요

서비스명은 **도서관 나들이**이다.

도서관 나들이는 부산 지역 도서관 데이터를 기반으로 사용자의 방문 목적에 맞는 도서관, 책, 문화 프로그램, 후기를 탐색하고 추천하는 웹 애플리케이션이다.

1차 서비스 범위는 부산 지역 MVP이며, 전국 확장 가능한 코드 구조를 지향한다.

핵심 기능은 다음과 같다.

* 홈의 오늘의 추천 도서관
* 로그인 회원 대상 개인화 추천 “여기는 어때요?”
* 도서관 검색·필터·상세
* 책 검색·상세·부산 소장 도서관 조회
* 문화 프로그램 검색·필터
* 도서관 후기 커뮤니티
* 도서관·책·프로그램 저장
* 좋아요한 후기와 작성 후기 기반 나의 나들이 분석
* 공휴일 기반 운영표 계산
* 공공누리 출처문구와 유형별 대체 이미지
* 외부 데이터의 도서관명·지역 오류를 내부 `Library.id`로 안전하게 매칭하는 import 파이프라인

## 2. 필수 요구사항

SSAFY 13회차 프로젝트의 필수 요구사항을 만족해야 한다.

* 사용자 추천 기능
* API 활용
* 커뮤니티 기능
* RESTful 원칙 준수
* Git 활용
* API Key 관리
* 충분한 데이터 확보
* 최소 5개 이상의 URL 및 페이지 구성
* load 가능한 fixture 또는 import 가능한 데이터 포함

배포는 심화 기능이므로 기본 구현 이후 여력이 있을 때 진행한다.

## 3. 작업 원칙

### 3.1 v3 명세 우선

기존 ERD와 Django 명세를 임의로 단순화하지 않는다.

특히 다음 항목은 임의 변경 금지다.

* Django 앱 구조
* 모델 소유권
* FK 방향
* `on_delete` 정책
* `related_name`
* migration 순서
* 환경변수 이름
* 태그 의미 분리 원칙
* 후기 저장 제거 및 좋아요 구조
* `Library.id` 기반 import 매칭
* 공휴일·운영표 정책
* GMS 사용 위치

### 3.2 모델 변경 규칙

모델을 수정하기 전에는 다음을 확인한다.

1. `library_outing_ERD_v3.md`에 해당 모델이 있는가?
2. `library_outing_Django_spec_v3.md`에 필드, 제약조건, related_name, on_delete가 정의되어 있는가?
3. 기존 migration 순서와 충돌하지 않는가?
4. 다른 앱의 FK 의존성이 깨지지 않는가?

모델 변경이 필요하면 바로 수정하지 말고 다음 형식으로 먼저 제안한다.

```text
변경 제안:
- 대상 모델:
- 변경 내용:
- 변경 이유:
- v3 명세와 충돌 여부:
- 영향 받는 serializer/view/import/recommendation:
```

### 3.3 기능 구현 순서

큰 기능은 다음 순서로 구현한다.

1. 모델 확인
2. serializer 작성
3. service 함수 작성
4. view/API 작성
5. URL 연결
6. fixture/import 또는 테스트 데이터 확인
7. 프론트 연결
8. 최소 UI 확인
9. README 또는 작업 기록 업데이트

한 번에 전체 기능을 구현하려고 하지 않는다.

## 4. 도메인 핵심 규칙

### 4.1 도서관 식별자

외부 파일과 API의 `library_name`, `sigungu`는 import 매칭 입력일 뿐 FK가 아니다.

매칭 이후 모든 관계는 내부 `Library.id`를 사용한다.

```text
source library_name + sigungu
→ normalize
→ Library exact / LibraryAlias / 검수된 correction map
→ Library.id 확정
→ 이후 모든 관계는 library_id 사용
```

모호하면 자동 연결하지 않고 reject report 또는 warning log에 남긴다.

주소·좌표만 같다는 이유로 자동 병합하지 않는다.

### 4.2 태그 정책

`Tag.code`는 의미 기준이다. 표시문구가 비슷하다는 이유로 같은 태그를 사용하지 않는다.

객관 시설 존재와 후기 체감은 반드시 분리한다.

예시:

```text
facility_parking           # 주차장 존재
review_parking_convenient  # 주차 편의 체감

facility_wifi              # 무료 와이파이 제공
review_wifi_reliable       # 와이파이 품질 체감

facility_children_room     # 어린이자료실 존재
review_children_room_good  # 어린이자료실 만족
```

동일 `tag_id`가 여러 source_method로 생성된 경우에만 화면에서 병합할 수 있다.

서로 다른 `tag_id`는 문구가 유사해도 병합하지 않는다.

`nearby`, `open_now`, `current_popular`처럼 시점이나 요청에 따라 달라지는 값은 영구 태그로 저장하지 않는다.

### 4.3 시설 데이터

`LibraryFacilityProfile`은 선택적 OneToOne이다.

시설 값은 `True`, `False`, `NULL`, 프로필 행 부재를 구분한다.

긍정 시설 필터는 명시적 `True`만 통과시킨다.

`NULL`이나 프로필 부재를 `False`로 해석하지 않는다.

### 4.4 운영 여부

`open_today`와 `open_now`를 구분한다.

* `open_today`: 오늘 날짜의 `LibraryDailySchedule.status=open`
* `open_now`: 현재 시각이 알려진 운영 시간 구간 안에 있음

`open_now`는 운영 시작·종료 시간이 모두 알려진 경우에만 확정한다.

휴관 규칙과 운영시간이 충돌하면 `unknown`으로 보수적으로 판정한다.

공휴일 관련 운영 판정은 해당 연도 `PublicHolidayCalendar.is_complete=True`일 때만 신뢰한다.

### 4.5 추천 후보 제한

홈의 오늘의 추천과 “여기는 어때요?”는 해당 날짜 `LibraryDailySchedule.status=open`인 도서관만 후보로 사용한다.

`closed`, `unknown`, 운영표 누락 도서관으로 결과를 채우지 않는다.

추천 결과가 부족하면 부족한 개수 그대로 반환한다.

### 4.6 홈 공개 테마

홈 공개 테마는 다음 5개만 사용한다.

```text
study
book
kids
mood
nearby
```

`program` 목적은 삭제하지 않는다. 다만 홈 공개 테마와 도서관 찾기의 공개 `purpose` 필터에서는 제외한다.

`program`은 프로필 직접 선호, 프로그램형 분석, 회원 개인화에 사용한다.

### 4.7 후기 정책

후기는 다음 구조를 따른다.

* 본문 1~200자
* 경험 태그 1~5개
* 선택적 관련 책
* 선택적 관련 프로그램
* 별도 제목 없음
* 별점 없음
* 방문 목적 FK 없음

후기 저장 모델은 만들지 않는다.

`UserReviewLike`가 좋아요 원본 관계이고, `UserReview.like_count`는 정렬 성능을 위한 집계 캐시다.

`UserReview.view_count`는 공개 상세 조회에서 원자적으로 증가시킨다.

후기 목록은 최신순, 조회수순, 좋아요순 정렬을 지원한다.

### 4.8 나의 나들이 행동 신호

나의 나들이 행동 신호는 다음만 사용한다.

* 저장한 도서관
* 저장한 책
* 저장한 문화 프로그램
* 좋아요한 후기
* 공개 가능한 작성 후기

후기 저장 신호는 존재하지 않는다.

최근성 기본 규칙은 다음과 같다.

```text
recency_weight = 0.5 ** (age_days / 90)
age_days > 365 → 행동 계산에서 제외
```

수동 선호 목적·지역·태그는 행동 성향과 별도로 저장한다.

### 4.9 이미지 정책

공식 외부 이미지와 시스템 대체 이미지, 사용자 업로드 이미지를 구분한다.

공식 외부 이미지가 활성 상태라면 `license_code`, `attribution_text`가 필요하다.

이미지 공개 응답은 `attribution_text`, `license_code`를 제공한다.

`source_page_url`은 내부 추적용으로 남길 수 있으나 공개 UI 링크 계약은 아니다.

대체 이미지는 엔터티별 이미지 관계에 실제 이미지처럼 삽입하지 않고 serializer/service에서 fallback으로 해석한다.

ⓘ 표시는 링크가 아니라 hover·focus·tap 시 전체 출처문구를 이미지 위 오버레이로 표시하는 UI 계약이다.

## 5. GMS 사용 규칙

GMS가 없어도 핵심 기능은 모두 동작해야 한다.

GMS는 사실 필드, 시설 여부, 운영 여부, 추천 점수에 영향을 주면 안 된다.

GMS는 추천 결과를 결정하는 도구가 아니라 설명 문구 생성 보조 도구로만 사용한다.

권장 흐름:

```text
Vue → Django API → GMS API → Django → Vue
```

Vue에서 GMS API를 직접 호출하지 않는다.

GMS API Key는 프론트엔드에 전달하지 않는다.

## 6. API Key 보안

다음 값은 Vue에 전달하지 않는다.

* `DATA4LIBRARY_API_KEY`
* `DATA_GO_KR_API_KEY`
* `GMS_API_KEY`

`.env`는 Git에 포함하지 않는다.

`.env.example`에는 변수명만 둔다.

로그, cache key, 오류 응답에 API Key를 남기지 않는다.

다음 키워드는 로그에서 마스킹한다.

```text
authKey
serviceKey
ServiceKey
Authorization
GMS_API_KEY
DATA4LIBRARY_API_KEY
DATA_GO_KR_API_KEY
```

## 7. REST API 원칙

URL은 리소스 중심으로 설계한다.

HTTP Method는 의미에 맞게 사용한다.

* 조회: GET
* 생성: POST
* 전체 수정: PUT
* 부분 수정: PATCH
* 삭제: DELETE

응답 status code는 처리 결과를 명확히 표현한다.

페이지용 URL과 데이터 API URL의 역할을 혼동하지 않는다.

외부 API 호출 실패 시 프론트가 깨지지 않도록 명확한 오류 응답 또는 빈 결과를 반환한다.

## 8. 코드 작성 규칙

* 의미가 드러나는 변수명과 함수명을 사용한다.
* view 안에 외부 API 호출 로직을 길게 작성하지 않는다.
* 외부 API client는 `integrations` 또는 service 모듈로 분리한다.
* 추천 점수 계산은 service 함수로 분리한다.
* import·normalization·matching 로직은 view와 분리한다.
* serializer는 목록용, 상세용, 생성/수정용을 필요하면 분리한다.
* 교차 앱 FK는 `"app_label.ModelName"` 문자열 참조를 사용한다.
* 사용자 FK는 `settings.AUTH_USER_MODEL`을 사용한다.
* 모든 관계에는 v3 명세의 `related_name`을 따른다.
* canonical 데이터는 물리 삭제보다 `is_active=False` 또는 domain별 soft delete를 우선한다.

## 9. 테스트와 검증

중요 로직은 최소한 service 단위 테스트를 작성한다.

우선 테스트 대상:

* 도서관명 정규화와 매칭
* 시설 `True/False/NULL` 처리
* 운영표 계산
* 공휴일 완전성 판정
* 후기 작성 검증
* 후기 좋아요 idempotent 처리
* 추천 후보에서 휴관·unknown 제외
* 태그 병합 규칙
* GMS 실패 시 fallback

## 10. Git 작업 규칙

기능 단위 브랜치를 사용한다.

예시:

```text
feature/backend-models
feature/import-libraries
feature/library-api
feature/community-api
feature/recommendation-service
feature/frontend-library-search
fix/library-matching
```

커밋 메시지는 목적이 드러나게 작성한다.

예시:

```text
feat: add library canonical models
feat: implement facility profile import
feat: add review like API
fix: prevent unknown schedules from recommendations
refactor: split data4library client
docs: update setup guide
```

큰 변경 후에는 변경한 파일, 구현한 기능, 남은 문제를 요약한다.

## 11. 절대 하지 말 것

* v3 명세와 다른 모델을 임의 생성하지 말 것
* 후기 저장 모델을 만들지 말 것
* 후기 별점, 제목, 방문 목적 FK를 추가하지 말 것
* 외부 `library_name`을 서비스 FK처럼 사용하지 말 것
* API Key를 프론트엔드에 노출하지 말 것
* GMS를 추천 순위 결정에 사용하지 말 것
* `NULL` 시설을 `False`로 처리하지 말 것
* `00:00~00:00`을 24시간 운영으로 자동 해석하지 말 것
* 운영표 `closed`, `unknown`, 누락 도서관을 오늘 추천 후보에 넣지 말 것
* 객관 시설 태그와 후기 체감 태그를 합치지 말 것
* 대체 이미지를 실제 엔터티 이미지 관계에 삽입하지 말 것
* 주소·좌표만 같다는 이유로 도서관을 자동 병합하지 말 것
* 전체 장서를 사전 적재하려고 하지 말 것
