## 도서관 나들이 ERD 수정본  
  
## 0. 서비스 페이지와 데이터 역할  
도서관 나들이는 사용자의 방문 목적에 맞는 도서관을 추천하고, 도서관·책·프로그램 정보를 탐색할 수 있도록 하는 웹 서비스이다.  
## 주요 페이지  

| 페이지 명 | 메인 기능 | 부가 및 세부 기능 |
| ------ | ---------------- | ------------------------------------------------- |
| 홈 | 방문 목적 기반 추천 | 공부, 책 탐색, 아이 동반, 문화프로그램, 공간 분위기, 가까운 도서관 등 목적별 추천 |
| 도서관 찾기 | DB 도서관 정보 검색 | 지역, 도서관 유형, 운영시간, 시설, 태그 등 조건 필터 |
| 책 둘러보기 | 원하는 책이 있는 도서관 검색 | 도서 검색, 인기대출도서, 마니아 추천도서, 다독자 추천도서 |
| 프로그램 | 문화 프로그램 검색 | 도서관별 프로그램, 대상, 기간, 신청 상태 필터 |
| 나의 나들이 | 사용자 정보 저장 | 저장한 도서관, 작성 후기, 후기 이미지, 선호 경향 확인 |
  
## 1. 핵심 개체  
## User  
서비스 사용자 정보를 저장한다. 가입 시 기본 거주 지역을 받을 수 있으며, 홈 화면의 지역 기반 추천이나 나의 나들이 페이지에 활용한다.  

| 필드명             | 설명     |
| --------------- | ------ |
| id              | 사용자 PK |
| username        | 사용자 이름 |
| email           | 이메일    |
| nickname        | 닉네임    |
| default_sido    | 기본 시도  |
| default_sigungu | 기본 시군구 |
| created_at      | 가입일    |
| updated_at      | 수정일    |
  
****관계****  
* User 1 : N UserLibrarySave
* User 1 : N UserBookSave
* User 1 : N UserProgramSave
* User 1 : N UserReview
* User 1 : 1 UserPreference
  
## Library  
도서관의 기본 정보를 저장한다. 전국도서관 표준데이터, 부산 도서관 API, 정보나루 API 등을 기반으로 적재한다.  

| 필드명                  | 설명       |
| -------------------- | -------- |
| id                   | 도서관 PK   |
| name                 | 도서관명     |
| sido                 | 시도명      |
| sigungu              | 시군구명     |
| library_type         | 도서관 유형   |
| address              | 주소       |
| latitude             | 위도       |
| longitude            | 경도       |
| phone                | 전화번호     |
| homepage_url         | 홈페이지 주소  |
| closed_days          | 휴관일      |
| weekday_open_time    | 평일 개관시간  |
| weekday_close_time   | 평일 폐관시간  |
| saturday_open_time   | 토요일 개관시간 |
| saturday_close_time  | 토요일 폐관시간 |
| holiday_open_time    | 공휴일 개관시간 |
| holiday_close_time   | 공휴일 폐관시간 |
| reading_seat_count   | 열람좌석 수   |
| book_count           | 도서 자료 수  |
| non_book_count       | 비도서 자료 수 |
| serial_count         | 연속간행물 수  |
| loan_available_count | 대출 가능 권수 |
| loan_available_days  | 대출 가능 일수 |
| site_area            | 부지 면적    |
| building_area        | 건물 면적    |
| operating_agency     | 운영 기관    |
| data_reference_date  | 데이터 기준일자 |
| created_at           | 생성일      |
| updated_at           | 수정일      |
  
****관계****  
* Library 1 : N LibraryExternalCode  
* Library 1 : N LibraryFacility  
* Library 1 : N LibraryTag  
* Library 1 : N LibraryImage  
* Library 1 : N Program  
* Library 1 : N ReadingRoomStatusSnapshot  
* Library 1 : N LibraryBook  
* Library 1 : N BookRankingSnapshot  
* Library 1 : N UserLibrarySave  
* Library 1 : N UserReview  
## 비고  
* 홈페이지, 전화번호, 부지면적, 건물면적, 운영기관은 결측 가능성이 있으므로 비어 있을 수 있다.  
* 운영시간이 00:00~00:00으로 제공되는 경우 해당 요일 또는 공휴일은 미운영으로 해석한다.  
* 공휴일 운영시간이 00:00~00:00인 경우 화면에서는 “공휴일 휴관”으로 표시한다.  
  
## LibraryExternalCode  
외부 API별 도서관 식별자를 저장한다. 정보나루, 열람실 API, 부산 도서관 API 등 외부 데이터와 내부 Library를 매칭하기 위한 테이블이다.  

| 필드명           | 설명               |
| ------------- | ---------------- |
| id            | PK               |
| library_id    | Library FK       |
| source_name   | 외부 데이터 출처명       |
| external_code | 외부 API 도서관 코드    |
| external_name | 외부 API에 등록된 도서관명 |
| created_at    | 생성일              |
| updated_at    | 수정일              |
  
****source_name 예시****  
* data4library  
* public_reading_room_api  
* busan_library_api  
* manual  
## 관계  
* Library 1 : N LibraryExternalCode  
## 비고  
* 하나의 내부 도서관은 여러 외부 API 코드를 가질 수 있다.  
* source_name + external_code 조합은 중복되지 않도록 관리한다.  
  
## 2. 시설 및 태그 개체  
## LibraryFacility  
공식 홈페이지 시설안내, 공공데이터, 수동 입력, 키워드 추출을 통해 확보한 도서관 시설 정보를 저장한다.  

| 필드명           | 설명         |
| ------------- | ---------- |
| id            | 시설 PK      |
| library_id    | Library FK |
| facility_type | 시설 유형 코드   |
| facility_name | 원문 시설명     |
| floor         | 층 정보       |
| description   | 설명         |
| source_type   | 출처 유형      |
| source_url    | 출처 URL     |
| confidence    | 신뢰도        |
| is_verified   | 검수 여부      |
| created_at    | 생성일        |
| updated_at    | 수정일        |
  
****facility_type 예시****  
* children_room  
* nursing_room  
* study_room  
* cafe  
* exhibition  
* auditorium  
* digital_room  
* lounge  
* parking  
## source_type 예시  
* official_homepage  
* public_api  
* manual  
* keyword_extraction  
## 관계  
* Library 1 : N LibraryFacility  
  
## Tag  
서비스 화면에 노출하거나 추천 계산에 사용하는 태그의 정의를 저장한다.  

| 필드명         | 설명         |
| ----------- | ---------- |
| id          | 태그 PK      |
| code        | 태그 코드      |
| label       | 사용자 화면 표시명 |
| tag_group   | 태그 그룹      |
| description | 태그 설명      |
| is_dynamic  | 실시간성 여부    |
| created_at  | 생성일        |
| updated_at  | 수정일        |
  
****tag_group 예시****  
* collection  
* reading_room  
* facility  
* program  
* space  
* location  
* realtime  
## 태그 예시  
* rich_books / 장서 풍부  
* many_seats / 열람좌석 많음  
* late_open / 늦게까지 운영  
* children_room / 어린이자료실  
* nursing_room / 수유실 있음  
* cafe / 카페 있음  
* exhibition / 전시공간  
* low_occupancy / 좌석 여유  
  
## LibraryTag  
특정 도서관에 어떤 태그가 붙었는지 저장하는 연결 테이블이다. 태그의 출처와 신뢰도를 함께 저장한다.  

| 필드명         | 설명             |
| ----------- | -------------- |
| id          | PK             |
| library_id  | Library FK     |
| tag_id      | Tag FK         |
| source_type | 태그 산출 출처       |
| source_url  | 출처 URL         |
| confidence  | 신뢰도            |
| score       | 태그 강도 또는 추천 점수 |
| is_active   | 현재 사용 여부       |
| expires_at  | 만료 시간          |
| created_at  | 생성일            |
| updated_at  | 수정일            |
  
****관계****  
* Library N : M Tag  
* Library 1 : N LibraryTag  
* Tag 1 : N LibraryTag  
## 비고  
* 시설 기반 태그, 수동 검수 태그, 장서 기반 태그는 일반 태그로 저장한다.  
* 실시간 태그는 expires_at을 사용한다.  
* 좌석 여유 태그처럼 실시간성이 있는 태그는 일정 시간 이후 만료한다.  
* MVP에서는 후기 기반 자동 태그는 후순위로 둔다.  
  
## 3. 추천 목적 개체  
## Purpose  
홈 화면에서 사용자가 선택하는 추천 목적을 저장한다.  

| 필드명           | 설명     |
| ------------- | ------ |
| id            | 목적 PK  |
| code          | 목적 코드  |
| label         | 화면 표시명 |
| description   | 설명     |
| display_order | 노출 순서  |
  
****목적 예시****  
* study / 조용히 공부하고 싶어요  
* wish / 보고 싶은 책이 있어요  
* kids / 아이와 함께 가요  
* program / 문화프로그램을 즐기고 싶어요  
* mood / 넓고 쾌적했으면 좋겠어요  
* nearby / 가까운 곳이 좋아요  
  
## PurposeTagRule  
추천 목적과 태그의 관계 및 가중치를 저장한다.  

| 필드명         | 설명         |
| ----------- | ---------- |
| id          | PK         |
| purpose_id  | Purpose FK |
| tag_id      | Tag FK     |
| weight      | 추천 가중치     |
| is_required | 필수 조건 여부   |
| created_at  | 생성일        |
| updated_at  | 수정일        |
  
****관계****  
* Purpose N : M Tag  
* Purpose 1 : N PurposeTagRule  
* Tag 1 : N PurposeTagRule  
## 예시  
* kids → children_room, weight 3  
* kids → nursing_room, weight 2  
* mood → cafe, weight 2  
* mood → exhibition, weight 2  
* study → many_seats, weight 3  
* study → late_open, weight 2  
  
## 4. 프로그램 개체  
## Program  
도서관 문화프로그램 정보를 저장한다.  

| 필드명                 | 설명                        |
| ------------------- | ------------------------- |
| id                  | 프로그램 PK                   |
| library_id          | Library FK                |
| external_program_id | 외부 API 또는 원문 사이트의 프로그램 ID |
| title               | 프로그램명                     |
| category            | 프로그램 분류                   |
| target              | 대상                        |
| start_date          | 시작일                       |
| end_date            | 종료일                       |
| apply_start_date    | 신청 시작일                    |
| apply_end_date      | 신청 종료일                    |
| place               | 장소                        |
| capacity            | 모집 정원                     |
| fee                 | 참가비 또는 수강료                |
| status              | 신청 상태                     |
| description         | 설명                        |
| source_url          | 출처 URL                    |
| apply_url           | 신청 페이지 URL                |
| created_at          | 생성일                       |
| updated_at          | 수정일                       |
  
****관계****  
* Library 1 : N Program  
## Program에서 파생 가능한 태그  
* 프로그램 운영  
* 어린이 프로그램  
* 가족 프로그램  
* 강좌 운영  
* 전시 운영  
* 이번 주 행사  
  
## 5. 열람실 실시간 스냅샷 개체  
## ReadingRoomStatusSnapshot  
실시간 열람실 API 응답을 일정 시간 동안 저장하는 스냅샷 테이블이다. 도서관별 열람실 좌석 현황을 저장하며, 도서관 상세 페이지에서 열람실 정보를 제공할 때 사용한다.  
이 테이블은 도서관의 고정 정보가 아니라 API 호출 시점의 상태를 기록하는 테이블이므로, 동일한 도서관과 동일한 열람실에 대해 여러 시점의 데이터가 누적될 수 있다.  
## 필드  

| 필드명                   | 설명                   |
| --------------------- | -------------------- |
| id                    | PK                   |
| library_id            | Library FK           |
| external_library_id   | 외부 API에서 제공하는 도서관 ID |
| external_room_id      | 외부 API에서 제공하는 열람실 ID |
| room_no               | 열람실 번호               |
| room_name             | 열람실명                 |
| room_type             | 열람실 유형               |
| floor_info            | 열람실 층/위치 설명          |
| current_visitor_count | 현재 방문자 수             |
| total_seats           | 전체 좌석 수              |
| used_seats            | 사용 중 좌석 수            |
| reserved_seats        | 예약 좌석 수              |
| available_seats       | 이용 가능 좌석 수           |
| occupancy_rate        | 좌석 사용률               |
| status                | 데이터 상태 또는 운영 상태      |
| source_updated_at     | API 원천 데이터 기준 시각     |
| fetched_at            | 서비스 서버의 데이터 수집 시각    |
  
****관계****  
* Library 1 : N ReadingRoomStatusSnapshot  
## 주요 필드 설명  

| 필드명 | 설명 |
| --------------------- | ------------------------------------------------------------------- |
| external_library_id | API 응답의 외부 도서관 ID이다. 내부 Library ID와 별개로 API 응답 추적 및 재매칭에 사용한다. |
| external_room_id | API 응답의 열람실 ID이다. 같은 도서관 안에서 열람실을 구분하기 위해 사용한다. |
| room_name | 열람실명이다. 예: 제1열람실, 일반열람실, 개인학습실 등 |
| room_type | 열람실 유형이다. 일반, 어린이, 노트북석 등 유형이 제공될 경우 저장한다. |
| floor_info | 층 또는 위치 설명이다. 예: 3층, 4층 등 |
| current_visitor_count | 현재 방문자 수이다. 제공되지 않거나 빈 값이면 null로 저장한다. |
| total_seats | 전체 좌석 수이다. |
| used_seats | 현재 사용 중인 좌석 수이다. |
| reserved_seats | 예약된 좌석 수이다. |
| available_seats | 남은 좌석 수이다. |
| occupancy_rate | used_seats / total_seats * 100으로 계산한다. 전체 좌석 수가 없거나 0이면 null로 저장한다. |
| status | API 응답값과 계산 결과를 바탕으로 데이터의 사용 가능 상태를 저장한다. |
| source_updated_at | API 제공기관에서 집계한 데이터 기준 시각이다. |
| fetched_at | 우리 서비스 서버가 API를 호출해 데이터를 저장한 시각이다. |
  
****status 값 예시****  

| status      | 의미                                          |
| ----------- | ------------------------------------------- |
| available   | 좌석 수 데이터가 정상적으로 제공되어 화면 표시와 계산에 사용할 수 있는 상태 |
| crowded     | 좌석 사용률이 높아 혼잡한 상태                           |
| full        | 이용 가능 좌석이 0석인 상태                            |
| unknown     | 좌석 수가 비어 있거나 계산이 불가능한 상태                    |
| stale       | 수집 시각이 오래되어 사용하지 않는 상태                      |
| unavailable | 열람실 미운영 또는 사용 불가로 판단되는 상태                   |
  
****사용 정책****  
* 열람실 실시간 정보는 도서관 상세 페이지에서만 제공한다.  
* 상세 페이지 진입 시 해당 도서관의 최신 스냅샷을 조회한다.  
* fetched_at 기준 1시간 이내의 스냅샷이 있으면 API를 호출하지 않고 저장된 스냅샷을 재사용한다.  
* 저장된 스냅샷을 재사용할 때는 “몇 시 기준 정보인지”를 함께 표시한다.  
* fetched_at 기준 1시간 이내의 스냅샷이 없으면 열람실 API를 호출하고, 응답 결과를 새 스냅샷으로 저장한다.  
* 추천 메인 로직에서는 기본적으로 사용하지 않으며, 도서관 상세 페이지의 부가 정보로 활용한다.  
* 필요하면 상세 페이지 내부에서만 좌석 여유 여부를 표시한다.  
* 오래된 스냅샷은 주기적으로 삭제할 수 있다.  
## 표시 예시  
* 잔여 63석 / 전체 114석  
* 좌석 사용률 42%  
* 23:26 기준 정보  
* 정보가 오래되어 새로 불러왔습니다  
* 좌석 정보가 제공되지 않습니다  
## 비고  
* 실시간 열람실 API는 도서관 단위가 아니라 열람실 단위로 응답할 수 있다.  
* 하나의 도서관에 여러 개의 열람실 스냅샷이 저장될 수 있다.  
* 화면 표시에는 library_id, external_room_id, fetched_at 기준 최신 스냅샷을 사용한다.  
* 좌석 수 관련 필드가 빈 문자열로 제공되는 경우, 정수 변환이 불가능한 값은 null로 저장한다.  
  
## 6. 도서 및 장서 개체  
도서 및 장서 관련 데이터는 정보나루 도서 검색 API, 도서 상세 API, 도서관별 장서/대출 데이터 API, 도서관별 소장여부 및 대출 가능여부 API, 인기대출도서 API, 추천도서 API를 기반으로 구성한다.  
도서 기본 정보는 사용자가 검색하거나 추천 목록에 노출된 도서를 중심으로 캐시한다. 인기대출도서, 마니아 추천도서, 다독자 추천도서처럼 일정 기간 기준으로 산출되는 목록성 데이터는 스냅샷 형태로 저장한다.  
## Book  
책의 기본 서지 정보를 저장한다. 정보나루 도서 검색 API, 도서 상세 API, 인기대출도서 API, 추천도서 API 응답을 기반으로 생성하거나 갱신한다.  

| 필드명                  | 설명                   |
| -------------------- | -------------------- |
| id                   | 책 PK                 |
| isbn13               | 13자리 ISBN            |
| isbn                 | 10자리 ISBN 또는 기타 ISBN |
| set_isbn13           | 세트 ISBN              |
| title                | 도서명                  |
| author               | 저자                   |
| publisher            | 출판사                  |
| publication_year     | 출판년도                 |
| publication_date     | 출판일자                 |
| volume               | 권                    |
| kdc_class_no         | KDC 주제분류 코드          |
| kdc_class_name       | KDC 주제분류명            |
| isbn_addition_symbol | ISBN 부가기호            |
| description          | 책 소개                 |
| cover_url            | 표지 이미지 URL           |
| book_detail_url      | 정보나루 도서 상세 페이지 URL   |
| source_type          | 도서 정보 출처             |
| created_at           | 생성일                  |
| updated_at           | 수정일                  |
  
****비고****  
* isbn13을 우선 식별자로 사용한다.  
* 동일한 ISBN의 도서가 여러 API에서 반복 조회될 수 있으므로 isbn13 기준으로 중복 생성을 방지한다.  
* 책 소개, 상세 페이지 URL 등은 도서 상세 조회 시점에만 채워질 수 있으므로 nullable 또는 blank 허용 필드로 둔다.  
* 사용자가 검색하거나 추천 목록에서 클릭한 도서는 Book에 저장하여 이후 재조회 비용을 줄인다.  
  
## LibraryBook  
특정 책이 어느 도서관에 소장되어 있는지 저장한다. 도서관별 장서/대출 데이터 API 또는 도서관별 도서 소장여부 및 대출 가능여부 API를 기반으로 생성하거나 갱신한다.  

| 필드명                     | 설명             |
| ----------------------- | -------------- |
| id                      | PK             |
| library_id              | Library FK     |
| book_id                 | Book FK        |
| external_library_code   | 정보나루 도서관 코드    |
| call_number             | 청구기호           |
| separate_shelf_code     | 별치기호           |
| separate_shelf_name     | 별치기호명          |
| book_code               | 도서기호           |
| shelf_location_code     | 배가기호           |
| shelf_location_name     | 배가기호명          |
| copy_code               | 복본기호           |
| registered_date         | 도서관 등록일자       |
| has_book                | 소장 여부          |
| is_loan_available       | 대출 가능 여부       |
| availability_checked_at | 대출 가능 여부 확인 시각 |
| source_type             | 출처             |
| updated_at              | 갱신일            |
  
****관계****  
* Library N : M Book  
* Library 1 : N LibraryBook  
* Book 1 : N LibraryBook  
## 비고  
* has_book은 해당 도서관이 특정 ISBN의 책을 소장하는지 나타낸다.  
* is_loan_available은 조회 시점 기준의 대출 가능 여부이므로, 영구적인 값이 아니라 갱신 가능한 상태값으로 취급한다.  
* 정보나루의 대출 가능 여부는 조회일 기준 전날의 대출 상태를 기준으로 제공되므로, 화면에는 “최근 확인 기준”을 함께 표시한다.  
* availability_checked_at이 오래된 경우, 상세 화면 진입 시 API를 다시 호출해 갱신할 수 있다.  
* 도서관별 전체 장서를 모두 저장하기보다, 사용자가 검색한 책 또는 추천 목록에 노출된 책 중심으로 저장한다.  
  
## BookRankingSnapshot  
책 둘러보기 탭에 노출할 인기/추천 도서 목록을 저장하는 스냅샷 테이블이다. 인기대출도서, 지역별 인기대출도서, 도서관별 인기대출도서, 마니아 추천도서, 다독자 추천도서, 신착도서, 대출 급상승 도서 등을 일정 주기 또는 필요 시점에 저장한다.  

| 필드명                | 설명                   |
| ------------------ | -------------------- |
| id                 | PK                   |
| book_id            | Book FK              |
| library_id         | Library FK, nullable |
| region_sido        | 시도                   |
| region_sigungu     | 시군구                  |
| region_code        | 지역 코드                |
| detail_region_code | 세부지역 코드              |
| ranking_type       | 랭킹/추천 유형             |
| source_isbn13      | 추천 기준 ISBN           |
| ranking            | 순위                   |
| loan_count         | 대출 횟수                |
| score              | 추천 점수 또는 가중치         |
| period_start       | 집계 시작일               |
| period_end         | 집계 종료일               |
| age_group          | 연령 조건                |
| gender             | 성별 조건                |
| kdc_class_no       | KDC 주제분류 조건          |
| target_group       | 화면용 대상 그룹            |
| created_at         | 생성일                  |
| fetched_at         | 데이터 수집 시각            |
  
****ranking_type 예시****  

| 값                     | 설명           |
| --------------------- | ------------ |
| popular_national      | 전국 인기대출도서    |
| popular_region        | 지역별 인기대출도서   |
| popular_library       | 도서관별 인기대출도서  |
| mania_recommendation  | 마니아를 위한 추천도서 |
| reader_recommendation | 다독자를 위한 추천도서 |
| new_arrival           | 신착도서         |
| hot_trend             | 대출 급상승 도서    |
| co_loan               | 함께 대출된 도서    |
  
****관계****  
* Book 1 : N BookRankingSnapshot  
* Library 1 : N BookRankingSnapshot
## 사용 예시  
* 책 둘러보기 탭에서 최근 1주 또는 1개월 기준 인기대출도서를 보여준다.  
* 특정 책을 클릭했을 때 source_isbn13 기준으로 마니아 추천도서 또는 다독자 추천도서를 보여준다.  
* 사용자가 도서명을 검색하면 도서 검색 API를 호출하고, 검색 결과를 Book에 캐시한다.  
* 추천 목록에 포함된 도서는 Book에 저장하고, 목록 자체는 BookRankingSnapshot에 저장한다.  
* 오래된 스냅샷은 추천 목록에서 제외하거나 주기적으로 삭제한다.  
  
## 7. 이미지 개체  
## LibraryImage  
도서관 사진 정보를 저장한다. 공공누리 사진, 공공기관 제공 이미지, 수동 수집 이미지를 사용한다.  

| 필드명              | 설명         |
| ---------------- | ---------- |
| id               | 이미지 PK     |
| library_id       | Library FK |
| image_url        | 원본 이미지 URL |
| local_path       | 저장 경로      |
| image_type       | 이미지 유형     |
| source_name      | 출처명        |
| source_url       | 출처 URL     |
| license_type     | 라이선스 유형    |
| attribution_text | 출처 표기 문구   |
| is_main          | 대표 이미지 여부  |
| is_active        | 사용 여부      |
| display_order    | 이미지 표시 순서  |
| created_at       | 생성일        |
  
****image_type 예시****  
* main  
* exterior  
* interior  
* children_room  
* reading_room  
* program  
* facility  
## 관계  
* Library 1 : N LibraryImage  
## 비고  
* 후기 이미지는 UserReviewImage에 저장하고, LibraryImage에는 공식/수동 수집 이미지를 저장한다.  
* 대표 이미지는 is_main=True이거나 display_order가 가장 낮은 이미지를 사용할 수 있다.  
* 공공누리 이미지는 출처 표기 문구를 attribution_text에 저장한다.  
  
## 8. 사용자 저장 개체  
## UserLibrarySave  
사용자가 마음에 드는 도서관을 저장한 정보를 기록한다. 나의 나들이 페이지에서 저장한 도서관 목록을 보여줄 때 사용한다.  

| 필드명        | 설명         |
| ---------- | ---------- |
| id         | 저장 PK      |
| user_id    | User FK    |
| library_id | Library FK |
| memo       | 사용자 메모     |
| created_at | 저장일        |
| updated_at | 수정일        |
  
****관계****  
* User 1 : N UserLibrarySave  
* Library 1 : N UserLibrarySave  
## 비고  
* 같은 사용자가 같은 도서관을 중복 저장하지 않도록 user_id + library_id 조합을 unique로 관리한다.  
* MVP에서는 저장 여부와 메모만 관리한다.  
* 추후 방문 예정일, 방문 완료 여부, 저장 폴더 등을 확장할 수 있다.  
  
## UserBookSave  
사용자가 관심 있는 책을 저장한 정보를 기록한다.나의 나들이 페이지에서 찜한 책 목록을 보여주고, 사용자의 관심 주제와 독서 취향을 집계할 때 사용한다.  

| 필드명        | 설명      |
| ---------- | ------- |
| id         | 저장 PK   |
| user_id    | User FK |
| book_id    | Book FK |
| memo       | 사용자 메모  |
| created_at | 저장일     |
| updated_at | 수정일     |
  
****관계****  
* User 1 : N UserBookSave  
* Book 1 : N UserBookSave  
## 비고  
* 같은 사용자가 같은 책을 중복 저장하지 않도록 user_id + book_id 조합을 unique로 관리한다.  
* MVP에서는 저장 여부와 메모만 관리한다.  
* 책의 KDC 주제분류, 저자, 출판년도 등을 활용해 사용자의 관심 도서 주제를 집계할 수 있다.  
* 추후 읽음 여부, 읽은 날짜, 개인 평점, 독서 상태 등을 확장할 수 있다.  
  
## UserProgramSave  
사용자가 관심 있거나 참여 예정인 도서관 프로그램을 저장한 정보를 기록한다.나의 나들이 페이지에서 저장한 프로그램 목록을 보여주고, 사용자의 프로그램 관심사를 집계할 때 사용한다.  

| 필드명        | 설명             |
| ---------- | -------------- |
| id         | 저장 PK          |
| user_id    | User FK        |
| program_id | Program FK     |
| status     | 사용자 기준 프로그램 상태 |
| memo       | 사용자 메모         |
| created_at | 저장일            |
| updated_at | 수정일            |
  
****status 예시****  

| 값            | 설명    |
| ------------ | ----- |
| interested   | 관심 있음 |
| planned      | 참여 예정 |
| participated | 참여 완료 |
| canceled     | 취소    |
  
****관계****  
* User 1 : N UserProgramSave  
* Program 1 : N UserProgramSave  
## 비고  
* 같은 사용자가 같은 프로그램을 중복 저장하지 않도록 user_id + program_id 조합을 unique로 관리한다.  
* MVP에서는 저장 여부, 사용자 기준 상태, 메모만 관리한다.  
* 프로그램의 category, target, library_id를 활용해 사용자의 프로그램 관심사를 집계할 수 있다.  
* 추후 신청 여부, 알림 여부, 참여 후기 연결 등을 확장할 수 있다.  
  
## UserPreference  
사용자의 저장, 찜, 후기, 프로그램 관심 데이터를 바탕으로 계산한 취향 요약 정보를 저장한다.나의 나들이 페이지에서 사용자의 도서관 이용 성향을 보여주고, 개인화된 추천 문구 또는 추천 조건을 생성할 때 사용한다.  

| 필드명                | 설명                      |
| ------------------ | ----------------------- |
| id                 | 사용자 취향 PK               |
| user_id            | User FK                 |
| primary_purpose    | 대표 이용 목적                |
| preference_title   | 취향 요약 제목                |
| preference_summary | 취향 요약 문장                |
| ai_summary         | AI가 생성한 사용자용 취향 설명      |
| ai_prompt_context  | AI 요약 생성에 사용한 압축 입력 데이터 |
| calculated_at      | 취향 계산 시각                |
| created_at         | 생성일                     |
| updated_at         | 수정일                     |
  
****primary_purpose 예시****  

| 값       | 설명        |
| ------- | --------- |
| study   | 조용히 공부    |
| book    | 책 탐색      |
| kids    | 아이와 함께    |
| program | 문화프로그램    |
| mood    | 분위기 좋은 공간 |
| nearby  | 가까운 곳     |
  
****관계****  
* User 1 : 1 UserPreference  
* UserPreference 1 : N UserPreferenceItem  
## 비고  
* UserPreference는 사용자의 현재 취향 프로필을 저장한다.  
* 사용자가 도서관, 책, 프로그램을 저장하거나 후기를 작성하면 일정 시점에 다시 계산할 수 있다.  
* AI API를 사용하지 않아도 preference_title, preference_summary는 규칙 기반으로 생성할 수 있다.  
* AI API를 사용할 경우 ai_prompt_context를 기반으로 ai_summary를 생성한다.  
* ai_prompt_context는 상위 태그, 도서 주제, 프로그램 분류, 선호 지역 등을 JSON 형태로 저장한다.
* 추천 순위 계산은 AI가 아니라 태그, 목적, 지역, 도서 주제 등의 정량 집계 결과를 기반으로 수행한다.
* 같은 UserPreference 안에서 item_type + item_code 조합은 중복되지 않도록 관리한다.  
  
## UserPreferenceItem  
사용자 취향을 구성하는 세부 집계 항목을 저장한다.태그, 도서 주제, 프로그램 유형, 지역, 방문 목적 등 여러 종류의 선호 항목을 공통 구조로 저장한다.  

| 필드명                  | 설명                |
| -------------------- | ----------------- |
| id                   | 취향 항목 PK          |
| user_preference_id   | UserPreference FK |
| item_type            | 취향 항목 유형          |
| item_code            | 항목 코드             |
| item_label           | 화면 표시명            |
| score                | 선호 점수             |
| count                | 집계 횟수             |
| rank                 | 선호 순위             |
| source_count_library | 도서관 저장 기반 집계 수    |
| source_count_book    | 책 저장 기반 집계 수      |
| source_count_program | 프로그램 저장 기반 집계 수   |
| source_count_review  | 후기 기반 집계 수        |
| created_at           | 생성일               |
| updated_at           | 수정일               |
  
****item_type 예시****  

| 값                | 설명        |
| ---------------- | --------- |
| library_tag      | 도서관 태그    |
| book_kdc         | 도서 KDC 주제 |
| program_category | 프로그램 분류   |
| region           | 선호 지역     |
| purpose          | 이용 목적     |
| facility         | 선호 시설     |
  
****관계****  
* UserPreference 1 : N UserPreferenceItem  
## 비고  
* 하나의 사용자는 여러 취향 항목을 가질 수 있다.  
* score는 추천 계산에 사용할 수 있는 가중 점수이다.  
* count는 단순 등장 횟수이다.  
* rank는 같은 item_type 내 선호 순위이다.  
* source_count 필드를 통해 어떤 행동에서 해당 취향이 강하게 나타났는지 확인할 수 있다.  
* AI 요약 생성 시 상위 UserPreferenceItem만 추려서 프롬프트에 전달한다.  
  
## 9. 사용자 후기 개체  
## UserReview  
도서관에 대한 사용자 후기를 저장한다. 사용자는 특정 도서관에 대해 평점, 후기 내용, 방문 목적을 작성할 수 있다. 후기 이미지는 별도 UserReviewImage 테이블로 분리하여 저장한다.  

| 필드명           | 설명         |
| ------------- | ---------- |
| id            | 후기 PK      |
| user_id       | User FK    |
| library_id    | Library FK |
| rating        | 평점         |
| content       | 후기 내용      |
| visit_purpose | 방문 목적      |
| created_at    | 작성일        |
| updated_at    | 수정일        |
  
****관계****  
* User 1 : N UserReview  
* Library 1 : N UserReview  
* UserReview 1 : N UserReviewImage  
## 비고  
* 하나의 사용자는 여러 도서관에 후기를 작성할 수 있다.  
* 하나의 도서관은 여러 사용자의 후기를 가질 수 있다.  
* 후기 이미지는 선택 사항이며, 이미지가 없는 텍스트 후기만 작성할 수도 있다.  
* 평점은 도서관의 평균 평점 계산에 사용한다.  
* 방문 목적은 추천 품질 개선 및 후기 필터링에 사용한다.  
  
## UserReviewImage  
사용자 후기에 첨부된 이미지를 저장한다. 하나의 후기는 여러 장의 이미지를 가질 수 있으므로 UserReview와 별도 테이블로 분리한다.  

| 필드명           | 설명            |
| ------------- | ------------- |
| id            | 후기 이미지 PK     |
| review_id     | UserReview FK |
| image         | 이미지 파일        |
| image_url     | 이미지 URL       |
| alt_text      | 이미지 대체 텍스트    |
| display_order | 이미지 표시 순서     |
| created_at    | 생성일           |
  
****관계****  
* UserReview 1 : N UserReviewImage  
## 비고  
* 이미지 파일을 직접 업로드하는 경우 image 필드에 저장한다.  
* 외부 이미지 URL을 사용하는 경우 image_url에 저장할 수 있다.  
* 하나의 후기에는 여러 이미지를 첨부할 수 있다.  
* display_order를 이용해 이미지 노출 순서를 제어한다.  
* 대표 이미지는 display_order가 가장 낮은 이미지를 사용하거나, 별도 is_thumbnail 필드를 둘 수 있다.  
  
## 10. 주요 관계 요약  
* User 1 : N UserLibrarySave  
* User 1 : N UserReview  
* Library 1 : N LibraryExternalCode  
* Library 1 : N LibraryFacility  
* Library 1 : N LibraryTag  
* Library 1 : N LibraryImage  
* Library 1 : N Program  
* Library 1 : N ReadingRoomStatusSnapshot  
* Library 1 : N LibraryBook  
* Library 1 : N BookRankingSnapshot  
* Library 1 : N UserLibrarySave  
* Library 1 : N UserReview  
* Tag 1 : N LibraryTag  
* Library N : M Tag through LibraryTag  
* Purpose 1 : N PurposeTagRule  
* Tag 1 : N PurposeTagRule  
* Purpose N : M Tag through PurposeTagRule  
* Book 1 : N LibraryBook  
* Library N : M Book through LibraryBook  
* Book 1 : N BookRankingSnapshot  
* Library 1 : N BookRankingSnapshot  
* UserReview 1 : N UserReviewImage  
* User 1 : N UserBookSave
* Book 1 : N UserBookSave
* User 1 : N UserProgramSave
* Program 1 : N UserProgramSave
* User 1 : 1 UserPreference
* UserPreference 1 : N UserPreferenceItem