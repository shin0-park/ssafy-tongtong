# 도서관 나들이 ERD 수정결과본

- 문서 버전: 1.0
- 작성 기준일: 2026-06-21
- 기준 문서: 기존 ERD 수정본, ERD 재검토본, 정보나루 Open API 매뉴얼 v20260210, 전국도서관표준데이터 샘플, 서비스 목업
- 적용 범위: 홈 추천, 도서관 찾기, 책 둘러보기, 프로그램, 나의 나들이

---

## 1. 최종 설계 결론

최종 ERD는 데이터를 다음 세 성격으로 분리한다.

| 성격 | 설명 | 대표 엔터티 |
|---|---|---|
| 서비스 기준·원본 데이터 | 서비스가 무결성과 검색을 책임져야 하는 데이터 | `Library`, `Program`, `User`, 저장·후기·선호, 추천 규칙 |
| 외부 원천 미러 데이터 | 외부 원천을 주기적으로 동기화하되 내부 FK와 검색에 사용하는 현재값 | 도서관 기본정보, 운영시간, 시설, 프로그램, 외부 식별자 |
| API 캐시·스냅샷 데이터 | 조회 시점 또는 집계 조건에 따라 바뀌는 값 | 열람실 상태, 대출 가능 여부, 인기·추천·신착 목록 |

핵심 원칙은 다음과 같다.

1. 도서관·프로그램·사용자 데이터는 DB를 기준으로 조회한다.
2. 전국 전체 장서를 사전 적재하지 않는다. 사용자가 실제로 조회한 도서와 소장 관계만 선택적으로 저장한다.
3. 열람실 좌석은 도서관 상세 화면에서만 조회하며, 최근 스냅샷이 1시간 이내이면 재사용한다.
4. 홈 추천은 실시간 좌석 API를 호출하거나 좌석 스냅샷을 점수에 사용하지 않는다. 정적 좌석 수, 시설, 운영시간, 프로그램, 거리 등으로 계산한다.
5. 현재 위치 좌표는 요청 파라미터로만 사용하고 사용자 DB에 저장하지 않는다. 사용자의 선택형 기본 시·도/시·군·구만 저장할 수 있다.
6. `현재 운영 중`, `거리`, `특정 도서 대출 가능`, `현재 좌석 여유` 같은 값은 영구 태그로 저장하지 않는다.
7. 정보나루의 대출 가능 여부는 조회일 전날 상태이므로 실시간으로 표현하지 않고 기준일을 함께 제공한다.
8. 프로그램은 여러 제공처를 통합 검색해야 하므로 외부 API를 화면 요청마다 호출하지 않고 DB에 미러링하며 soft delete한다.
9. 공식 이미지와 사용자 후기 이미지를 분리하고, 공식 이미지에는 출처와 이용허락 정보를 저장한다.

---

## 2. 페이지별 데이터 사용 의도

| 페이지 | DB 기준 데이터 | API·스냅샷 데이터 | 비고 |
|---|---|---|---|
| 홈 | 도서관, 시설, 최신 통계, 운영시간, 태그, 프로그램, 추천 규칙 | 사용하지 않음 | 실시간 열람실 상태는 홈 추천에서 제외 |
| 도서관 찾기 | 도서관, 운영시간, 시설, 태그, 최신 통계, 대표 이미지 | 필요 시 운영상태의 오래된 보조 표시만 가능 | 기본 검색은 외부 API 없이 동작 |
| 도서관 상세 | 도서관 전체 기준정보, 프로그램, 후기, 이미지 | 열람실 운영·좌석 최신 스냅샷 | 1시간 fresh 정책, 실패 시 stale 표시 가능 |
| 책 둘러보기 | 캐시된 도서, 저장 정보 | 도서 검색, 상세, 소장, 대출 가능, 인기·추천 목록 | 목록은 헤더·항목 스냅샷으로 저장 |
| 프로그램 | 미러된 프로그램·회차·도서관 정보 | 동기화 작업에서만 원천 API 호출 | 신청은 원천 페이지로 이동 |
| 나의 나들이 | 저장한 도서관·책·프로그램, 후기, 선호 프로필 | 없음 | 내부 DB가 원본 |

---

## 3. 데이터 출처별 최종 저장 정책

| 원천·데이터 | 최종 방식 | 갱신·캐시 정책 | 엔터티 |
|---|---|---|---|
| 전국도서관표준데이터 | raw staging + 정규화된 현재값 + 기준일 스냅샷 | 월 1회 변경 확인, 새 파일 기준 upsert | `LibrarySourceRecord`, `Library`, `LibraryOpeningHour`, `LibraryClosureRule`, `LibraryStatisticSnapshot` |
| 정보나루 참여 도서관 | 외부 코드 미러 | 주 1회 또는 월 1회 | `LibraryExternalIdentifier` |
| 실시간 열람실 도서관·열람실 정의 | 조회 시 또는 주기적 upsert | 상세 조회 과정에서 신규 방 발견 시 갱신 | `ReadingRoom`, `LibraryExternalIdentifier` |
| 실시간 열람실 운영·좌석 | 단기 스냅샷 | 1시간 fresh, 원본 스냅샷 1~7일 보관 | `LibraryOperationalStatusSnapshot`, `ReadingRoomStatusSnapshot` |
| 정보나루 도서 검색·상세 | 선택적 영구 캐시 | 도서 메타데이터 30~90일 후 재확인 | `Book` |
| 도서 소장·청구기호·복본 | 조회 기반 미러 | 7~30일 후 재확인 | `LibraryHolding`, `LibraryHoldingCopy` |
| 대출 가능 여부 | 시점 스냅샷 | 24시간 fresh, 기준일 표시 | `BookAvailabilitySnapshot` |
| 인기·추천·급상승·신착 목록 | 목록 스냅샷 | 유형에 따라 1일~1주 fresh | `BookListSnapshot`, `BookListItem` |
| 부산 지역 프로그램·각 도서관 홈페이지 | DB 미러 + soft delete | 제공처별 하루 1~4회 | `Program`, `ProgramSession` |
| 공식 시설·공간 정보 | 검증된 현재값 + 근거 | 주·월 단위 재확인 | `LibraryFacility` |
| 공공누리·공공기관 이미지 | 선별 저장 | 수집 시 이용조건 검증, 링크 월 1회 점검 | `MediaAsset`, `LibraryImage` |
| 사용자 행동 | 내부 원본 | 즉시 저장 | 저장·후기·선호 엔터티 |

---

## 4. 공통 모델 규칙

- 기본 PK: `BigAutoField`
- 모든 서비스 테이블: `created_at`, `updated_at`
- 원천 미러 테이블: `source_updated_at`, `fetched_at`, `last_seen_at` 중 필요한 필드 포함
- 외부 원천에서 사라질 수 있는 기준 엔터티: 물리 삭제 대신 `is_active`, `is_visible`, `deleted_at` 사용
- 시각: DB에는 UTC 저장, 화면에는 `Asia/Seoul`로 변환
- 코드 필드: Django `TextChoices` 또는 별도 기준 테이블 사용
- 원천 응답: 서비스 컬럼으로 정규화한 값과 raw payload를 분리
- 위도·경도: nullable. 현재 위치와의 거리는 요청 시 Haversine으로 계산
- ISBN: 문자열로 저장하고 숫자형으로 저장하지 않음
- 비어 있는 원천값과 실제 0을 구분하기 위해 통계 숫자는 nullable 허용

---

## 5. 최종 엔터티 명세

### 5.1 원천·수집 관리

#### DataSource

외부 원천과 이용조건, 갱신정책을 관리한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 내부 식별자 |
| code | varchar, unique | `library_standard`, `data4library`, `reading_room_api`, `busan_program_dongnae`, `official_homepage`, `kogl`, `manual` 등 |
| name | varchar | 표시명 |
| source_kind | enum | `bulk_file`, `api`, `web`, `manual` |
| base_url | URL, nullable | 원천 기본 URL |
| license_code | varchar, nullable | 이용허락 코드 |
| refresh_policy | text | 운영자용 갱신 설명 |
| default_ttl_seconds | integer, nullable | 기본 fresh TTL |
| priority | integer | 동일 필드 충돌 시 원천 우선순위 |
| is_active | boolean | 사용 여부 |
| created_at / updated_at | datetime | 관리 시각 |

#### SourceSyncRun

배치 또는 수동 수집 한 번의 실행 이력을 저장한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 실행 식별자 |
| source_id | FK | `DataSource` |
| job_name | varchar | 실행 작업명 |
| started_at / finished_at | datetime | 시작·종료 시각 |
| status | enum | `running`, `success`, `partial`, `failed` |
| fetched_count | integer | 원천 조회 건수 |
| inserted_count / updated_count | integer | 반영 건수 |
| skipped_count / failed_count | integer | 제외·실패 건수 |
| source_version | varchar, nullable | 파일 버전·기준일 |
| raw_object_key | varchar, nullable | 원본 파일 또는 응답 저장 위치 |
| error_message | text, nullable | 오류 요약 |
| metadata | JSON | 요청 조건, 커서, 체크섬 등 |

#### LibrarySourceRecord

전국도서관표준데이터 등에서 들어온 원본 행을 staging하고 내부 도서관과의 매칭 결과를 보존한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 원본 행 식별자 |
| source_id | FK | `DataSource` |
| sync_run_id | FK, nullable | 수집 실행 |
| external_record_key | varchar | 원천에 고유 ID가 없으면 이름·주소·기관코드 기반 해시 |
| raw_data | JSON | 원본 행 |
| content_hash | char(64) | 변경 탐지용 SHA-256 |
| source_reference_date | date, nullable | 데이터 기준일자 |
| match_status | enum | `unmatched`, `auto_matched`, `manual_matched`, `rejected` |
| matched_library_id | FK, nullable | 매칭된 `Library` |
| match_confidence | decimal, nullable | 자동 매칭 신뢰도 |
| match_note | text, nullable | 검수 메모 |
| fetched_at | datetime | 수집 시각 |

제약조건: `UNIQUE(source_id, external_record_key, content_hash)` 또는 수집 이력 보존 정책에 따른 조건부 unique.

> 전국도서관표준데이터의 `제공기관코드`는 제공 기관 코드이지 개별 도서관 코드가 아니므로 `LibraryExternalIdentifier.external_code`로 직접 사용하지 않는다.

---

### 5.2 도서관 기준정보

#### Library

도서관의 현재 기본 식별정보를 저장한다. 운영시간과 시점 통계는 별도 테이블로 분리한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 도서관 식별자 |
| name | varchar | 도서관명 |
| normalized_name | varchar | 매칭·검색용 정규화 이름 |
| sido | varchar | 시·도 |
| sigungu | varchar | 시·군·구 |
| library_type | enum/varchar | 공공도서관, 작은도서관, 어린이도서관 등 |
| road_address | varchar | 도로명주소 |
| normalized_address | varchar | 매칭용 정규화 주소 |
| latitude / longitude | decimal, nullable | 좌표 |
| phone | varchar, nullable | 전화번호 |
| homepage_url | URL, nullable | 홈페이지 |
| operating_agency | varchar, nullable | 운영 기관 |
| short_description | varchar, nullable | 카드용 한 줄 설명, 운영자 검수 값 |
| is_active | boolean | 서비스 대상 여부 |
| source_priority_applied | integer, nullable | 현재값 결정에 사용된 우선순위 |
| created_at / updated_at | datetime | 관리 시각 |

권장 인덱스: `(sido, sigungu, library_type, is_active)`, `normalized_name`, 좌표 인덱스.

#### LibraryExternalIdentifier

원천별 개별 도서관 코드를 내부 도서관에 연결한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 식별자 |
| library_id | FK | `Library` |
| source_id | FK | `DataSource` |
| code_type | varchar | `lib_code`, `library_id`, `facility_code` 등 |
| external_code | varchar | 외부 코드 |
| external_name | varchar, nullable | 원천 도서관명 |
| first_seen_at / last_seen_at | datetime | 확인 시각 |
| is_active | boolean | 현재 유효 여부 |

제약조건: `UNIQUE(source_id, code_type, external_code)`.

#### LibraryOpeningHour

요일·공휴일·특정일 운영시간을 정규화한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 식별자 |
| library_id | FK | `Library` |
| source_id | FK | 근거 원천 |
| day_type | enum | `day_of_week`, `holiday`, `specific_date` |
| day_of_week | smallint, nullable | 월=0 ~ 일=6 |
| specific_date | date, nullable | 임시 일정 |
| schedule_status | enum | `open`, `closed`, `unknown` |
| open_time / close_time | time, nullable | 운영시간 |
| valid_from / valid_to | date, nullable | 적용 기간 |
| raw_text | text, nullable | 원문 보조 |
| source_updated_at | datetime, nullable | 원천 수정 시각 |
| fetched_at | datetime | 수집 시각 |
| is_current | boolean | 현재 규칙 여부 |

제약조건: 현재 행 기준 `(library_id, day_type, day_of_week, specific_date, valid_from)` 중복 방지.

#### LibraryClosureRule

휴관 문구와 정규화 규칙을 함께 보존한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 식별자 |
| library_id | FK | `Library` |
| source_id | FK | 원천 |
| rule_type | enum | `regular`, `public_holiday`, `temporary`, `unknown` |
| normalized_rule | JSON | 매주 월요일, 매월 둘째 월요일 등 구조화 값 |
| raw_text | text | 원문 |
| valid_from / valid_to | date, nullable | 적용 기간 |
| is_current | boolean | 현재 적용 여부 |
| fetched_at | datetime | 수집 시각 |

#### LibraryStatisticSnapshot

기준일별 통계와 대출정책을 저장한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 식별자 |
| library_id | FK | `Library` |
| source_id | FK | 원천 |
| reference_date | date | 원천 기준일 |
| reading_seat_count | integer, nullable | 열람좌석 수 |
| book_count | integer, nullable | 도서 자료 수 |
| serial_count | integer, nullable | 연속간행물 수 |
| non_book_count | integer, nullable | 비도서 자료 수 |
| loan_limit_count | integer, nullable | 1인 대출 가능 권수 |
| loan_period_days | integer, nullable | 대출 가능 일수 |
| site_area / building_area | decimal, nullable | 부지·건물 면적 |
| fetched_at | datetime | 수집 시각 |
| is_current | boolean | 화면 검색에 사용할 최신 행 |

제약조건: `UNIQUE(library_id, source_id, reference_date)`.

#### LibraryFacility

검증 가능한 시설·공간 정보를 저장한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 시설 식별자 |
| library_id | FK | `Library` |
| source_id | FK | 원천 |
| facility_type | enum/varchar | `study_room`, `children_room`, `nursing_room`, `parking`, `wifi`, `cafe`, `exhibition`, `auditorium`, `digital_room`, `lounge` 등 |
| facility_name | varchar | 원문 표시명 |
| floor_info | varchar, nullable | 층·위치 |
| description | text, nullable | 설명 |
| evidence_url | URL, nullable | 확인 페이지 |
| confidence | decimal | 0~1 |
| is_verified | boolean | 운영자 검수 여부 |
| is_active | boolean | 현재 유효 여부 |
| last_verified_at | datetime, nullable | 마지막 확인 |
| created_at / updated_at | datetime | 관리 시각 |

제약조건: `UNIQUE(library_id, facility_type, facility_name)`.

---

### 5.3 태그와 추천 목적

#### Tag

비교적 안정적인 범주형 특징만 저장한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 태그 식별자 |
| code | varchar, unique | `rich_books`, `many_seats`, `late_open`, `children_room`, `cafe`, `natural_light`, `quiet_space` 등 |
| label | varchar | 사용자 표시명 |
| tag_group | enum | `collection`, `reading_room`, `facility`, `program`, `space` |
| description | text, nullable | 정의 |
| is_active | boolean | 사용 여부 |
| created_at / updated_at | datetime | 관리 시각 |

`nearby`, `open_now`, `low_occupancy`, `book_available`은 태그에 포함하지 않는다.

#### LibraryTag

도서관과 안정적 태그를 연결한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 식별자 |
| library_id | FK | `Library` |
| tag_id | FK | `Tag` |
| source_id | FK, nullable | 산출 근거 |
| source_method | enum | `official`, `manual`, `rule`, `review_aggregate` |
| score | decimal | 태그 강도 |
| confidence | decimal | 신뢰도 |
| evidence_url | URL, nullable | 근거 URL |
| is_active | boolean | 사용 여부 |
| created_at / updated_at | datetime | 관리 시각 |

제약조건: `UNIQUE(library_id, tag_id, source_method)`.

#### Purpose

홈의 방문 목적 기준정보다.

| code | 화면 문구 |
|---|---|
| `study` | 조용히 공부하고 싶어요 |
| `book` | 책을 빌리러 가요 |
| `kids` | 아이와 함께 가요 |
| `program` | 문화프로그램을 즐기고 싶어요 |
| `mood` | 분위기 좋은 곳에 머물고 싶어요 |
| `nearby` | 가까운 곳이 좋아요 |

필드: `id`, `code`, `label`, `description`, `display_order`, `is_active`.

#### PurposeTagRule

목적과 안정적 태그의 가중치를 정의한다.

| 필드 | 설명 |
|---|---|
| purpose_id | `Purpose` FK |
| tag_id | `Tag` FK |
| weight | 가중치 |
| is_required | 필수 조건 여부 |
| explanation_template | 추천 사유 템플릿 |
| created_at / updated_at | 관리 시각 |

제약조건: `UNIQUE(purpose_id, tag_id)`.

#### PurposeMetricRule

태그가 아닌 계산형 지표의 점수 규칙을 저장한다.

| 필드 | 설명 |
|---|---|
| purpose_id | `Purpose` FK |
| metric_code | `reading_seat_count`, `book_count`, `late_close_minutes`, `active_program_count`, `distance_m`, `review_rating`, `official_image_count`, `has_children_facility` 등 |
| weight | 가중치 |
| is_required | 필수 조건 여부 |
| normalization_rule | min-max, 구간점수, 역거리 등 JSON |
| explanation_template | 추천 사유 템플릿 |
| created_at / updated_at | 관리 시각 |

제약조건: `UNIQUE(purpose_id, metric_code)`.

> `available_seat_ratio`는 상세 화면용 상태 지표로만 유지하며 홈 추천 규칙에 등록하지 않는다.

---

### 5.4 실시간 열람실

#### ReadingRoom

열람실의 준고정 마스터다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 열람실 식별자 |
| library_id | FK | `Library` |
| source_id | FK | 열람실 API |
| external_room_id | varchar | 외부 열람실 ID |
| room_no | varchar, nullable | 원천 번호 |
| name | varchar | 열람실명 |
| room_type | varchar, nullable | 일반·어린이·노트북석 등 |
| floor_info | varchar, nullable | 층·위치 |
| is_active | boolean | 현재 제공 여부 |
| first_seen_at / last_seen_at | datetime | 확인 시각 |

제약조건: `UNIQUE(library_id, source_id, external_room_id)`.

#### LibraryOperationalStatusSnapshot

도서관 전체의 운영상태·방문자 수를 저장한다.

| 필드 | 설명 |
|---|---|
| library_id | `Library` FK |
| source_id | `DataSource` FK |
| operation_status | `open`, `closed`, `unknown`, `unavailable` |
| current_visitor_count | nullable |
| source_updated_at | 원천 기준 시각, nullable |
| fetched_at | 조회 시각 |
| fresh_until | `fetched_at + 1시간` |
| raw_status | 원천 상태 코드, nullable |

권장 인덱스: `(library_id, fetched_at DESC)`.

#### ReadingRoomStatusSnapshot

열람실 좌석의 시점 상태다.

| 필드 | 설명 |
|---|---|
| reading_room_id | `ReadingRoom` FK |
| source_id | `DataSource` FK |
| total_seats | nullable |
| used_seats | nullable |
| reserved_seats | nullable |
| available_seats | nullable |
| occupancy_rate | 계산값, nullable |
| status | `available`, `crowded`, `full`, `unknown`, `unavailable` |
| source_updated_at | 원천 기준 시각, nullable |
| fetched_at | 조회 시각 |
| fresh_until | `fetched_at + 1시간` |
| raw_data | JSON, 선택 | 파싱 검증용 최소 원문 |

권장 인덱스: `(reading_room_id, fetched_at DESC)`.

---

### 5.5 프로그램

#### Program

여러 원천의 프로그램을 통합 검색하기 위한 현재 미러다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 프로그램 식별자 |
| library_id | FK | 개최 도서관 |
| source_id | FK | 제공처 |
| external_program_id | varchar | 원천 ID. 없으면 안정적 해시 키 |
| title | varchar | 프로그램명 |
| category_code | varchar | `lecture`, `reading_writing`, `culture_art`, `experience_education`, `exhibition`, `other` 등 |
| target_text | varchar, nullable | 원문 대상 |
| target_codes | JSON | `infant`, `elementary`, `teen`, `adult`, `senior`, `family`, `all` 배열 |
| summary / description | text, nullable | 설명 |
| start_at / end_at | datetime, nullable | 전체 운영기간 |
| apply_start_at / apply_end_at | datetime, nullable | 신청기간 |
| place | varchar, nullable | 장소 |
| capacity | integer, nullable | 정원 |
| fee_amount | decimal, nullable | 비용 |
| fee_text | varchar, nullable | 원문 비용 |
| source_status | varchar, nullable | 원천 상태 |
| lifecycle_status | enum | `scheduled`, `recruiting`, `closed`, `ongoing`, `ended`, `canceled`, `unknown` |
| source_url / apply_url | URL, nullable | 원문·신청 페이지 |
| thumbnail_url | URL, nullable | 원천 썸네일 |
| source_updated_at | datetime, nullable | 원천 수정 시각 |
| fetched_at / last_seen_at | datetime | 수집·최종 확인 |
| content_hash | char(64) | 변경 탐지 |
| is_visible | boolean | 서비스 노출 여부 |
| deleted_at | datetime, nullable | soft delete |
| created_at / updated_at | datetime | 관리 시각 |

제약조건: `UNIQUE(source_id, external_program_id)`.

#### ProgramSession

반복 회차가 있을 때만 사용한다.

| 필드 | 설명 |
|---|---|
| program_id | `Program` FK |
| sequence | 회차 번호 |
| starts_at / ends_at | 회차 시각 |
| place | 회차별 장소, nullable |
| is_canceled | 취소 여부 |
| source_session_id | 원천 회차 ID, nullable |

제약조건: `UNIQUE(program_id, sequence)`.

> 서비스는 프로그램 신청을 직접 처리하지 않는다. `apply_url`로 공식 신청 화면을 연결한다.

---

### 5.6 도서·소장·목록

#### Book

실제 노출·검색·저장된 도서만 선택적으로 캐시한다.

| 필드 | 타입 개념 | 설명 |
|---|---|---|
| id | PK | 도서 식별자 |
| isbn13 | char(13), nullable | 13자리 ISBN |
| set_isbn13 | char(13), nullable | 세트 ISBN |
| title | varchar | 도서명 |
| authors_text | varchar, nullable | 저자 원문 |
| publisher | varchar, nullable | 출판사 |
| publication_date | date, nullable | 출판일 |
| publication_year | smallint, nullable | 출판년도 |
| volume | varchar, nullable | 권 |
| addition_symbol | varchar, nullable | ISBN 부가기호 |
| kdc_class_no | varchar, nullable | KDC 분류 |
| kdc_class_name | varchar, nullable | KDC 분류명 |
| description | text, nullable | 책소개 |
| cover_image_url | URL, nullable | 표지 URL |
| source_detail_url | URL, nullable | 정보나루 상세 URL |
| metadata_source_id | FK, nullable | 주 메타데이터 원천 |
| metadata_fetched_at | datetime, nullable | 마지막 상세 확인 |
| is_active | boolean | 서비스 사용 여부 |
| created_at / updated_at | datetime | 관리 시각 |

제약조건: ISBN이 비어 있지 않을 때 `UNIQUE(isbn13)`.

#### LibraryHolding

도서관이 ISBN 단위 도서를 소장한다고 확인된 관계다.

| 필드 | 설명 |
|---|---|
| library_id | `Library` FK |
| book_id | `Book` FK |
| source_id | `DataSource` FK |
| first_seen_at | 최초 소장 확인 |
| last_verified_at | 마지막 확인 |
| registered_date | 대표 등록일, nullable |
| is_active | 현재 소장으로 간주하는지 여부 |
| deactivated_at | 비활성화 시각, nullable |

제약조건: `UNIQUE(library_id, book_id)`.

#### LibraryHoldingCopy

정보나루 `itemSrch`의 복본·청구기호 구조를 보존한다.

| 필드 | 설명 |
|---|---|
| holding_id | `LibraryHolding` FK |
| source_id | `DataSource` FK |
| external_copy_key | 원천 복본 식별 키 또는 해시 |
| call_number | 청구기호, nullable |
| separate_shelf_code / name | 별치기호·명, nullable |
| book_code | 도서기호, nullable |
| shelf_location_code / name | 배가기호·명, nullable |
| copy_code | 복본기호, nullable |
| registered_date | 등록일, nullable |
| last_verified_at | 확인 시각 |
| is_active | 현재 유효 여부 |

제약조건: `UNIQUE(holding_id, source_id, external_copy_key)`.

#### BookAvailabilitySnapshot

소장 여부와 대출 가능 여부의 시점값을 저장한다.

| 필드 | 설명 |
|---|---|
| library_id | `Library` FK |
| book_id | `Book` FK |
| holding_id | `LibraryHolding` FK, nullable |
| source_id | `DataSource` FK |
| has_book | 소장 여부 |
| is_loan_available | 대출 가능 여부, nullable |
| source_effective_date | 원천 상태 기준일 |
| fetched_at | API 조회 시각 |
| fresh_until | 기본 24시간 |
| raw_status | 원천 코드, nullable |

인덱스: `(library_id, book_id, fetched_at DESC)`.

#### BookListSnapshot

동일 조건으로 조회된 하나의 목록을 나타낸다.

| 필드 | 설명 |
|---|---|
| source_id | `DataSource` FK |
| list_type | 아래 코드 |
| library_id | 특정 도서관 조건, nullable |
| region_code / detail_region_code | 지역 조건, nullable |
| seed_isbns | 추천 기준 ISBN 배열 JSON |
| period_start / period_end | 집계 기간, nullable |
| effective_date | 원천 기준일, nullable |
| query_params | 성별·연령·KDC·정렬 등 JSON |
| query_hash | 정규화된 조건 해시 |
| result_count | 항목 수 |
| fetched_at | 수집 시각 |
| fresh_until | 노출 fresh 시각 |

`list_type`:

- `popular_national`
- `popular_region`
- `popular_library`
- `mania_recommendation`
- `reader_recommendation`
- `new_arrival`
- `hot_trend`
- `co_loan`

제약조건: 동일 유형의 최신 이력은 허용하되 `UNIQUE(source_id, list_type, query_hash, fetched_at)`.

#### BookListItem

목록 안의 개별 도서다.

| 필드 | 설명 |
|---|---|
| snapshot_id | `BookListSnapshot` FK |
| book_id | `Book` FK |
| rank | 순위 |
| loan_count | 대출 횟수, nullable |
| score | 추천 점수, nullable |
| reason | 원천 추천 사유, nullable |
| rank_difference | 급상승 폭, nullable |
| base_week_rank / past_week_rank | 급상승 관련 순위, nullable |
| registered_date | 신착 등록일, nullable |
| source_payload | JSON, 선택 | 목록별 추가 필드 |

제약조건: `UNIQUE(snapshot_id, rank)`, `UNIQUE(snapshot_id, book_id)`.

---

### 5.7 공식 이미지

#### MediaAsset

| 필드 | 설명 |
|---|---|
| source_id | `DataSource` FK |
| source_asset_id | 원천 저작물 ID, nullable |
| original_url | 원본 URL |
| storage_object_key | 자체 스토리지 객체 키, nullable |
| checksum | 파일 체크섬, nullable |
| mime_type / width / height | 파일 속성, nullable |
| license_code | 공공누리 유형 등 |
| attribution_text | 화면 출처표시 문구 |
| commercial_use_allowed | 상업적 이용 가능 여부 |
| modification_allowed | 크롭·리사이즈 가능 여부 |
| license_verified_at | 이용조건 확인 시각 |
| downloaded_at | 자체 저장 시각, nullable |
| is_active | 사용 여부 |

#### LibraryImage

| 필드 | 설명 |
|---|---|
| library_id | `Library` FK |
| media_asset_id | `MediaAsset` FK |
| image_type | `main`, `exterior`, `interior`, `reading_room`, `children_room`, `program`, `facility` |
| is_main | 대표 여부 |
| display_order | 노출 순서 |
| caption | 설명, nullable |

한 도서관의 활성 대표 이미지는 1개만 허용하도록 조건부 unique를 권장한다.

---

### 5.8 사용자·저장·후기·선호

#### User

Django `AbstractUser`를 상속한다.

추가 필드:

| 필드 | 설명 |
|---|---|
| nickname | 화면 표시명 |
| email | unique 권장 |
| default_sido | 선택형 기본 시·도, nullable |
| default_sigungu | 선택형 기본 시·군·구, nullable |
| created_at / updated_at | 관리 시각 |

현재 위치의 위도·경도는 저장하지 않는다.

#### UserLibrarySave

`user_id`, `library_id`, `memo`, `created_at`, `updated_at`.

제약조건: `UNIQUE(user_id, library_id)`.

#### UserBookSave

`user_id`, `book_id`, `memo`, `created_at`, `updated_at`.

제약조건: `UNIQUE(user_id, book_id)`.

#### UserProgramSave

| 필드 | 설명 |
|---|---|
| user_id | `User` FK |
| program_id | `Program` FK |
| status | `interested`, `planned`, `participated`, `canceled` |
| memo | 사용자 메모, nullable |
| reminder_enabled | 알림 사용 여부 |
| created_at / updated_at | 관리 시각 |

제약조건: `UNIQUE(user_id, program_id)`.

#### UserReview

| 필드 | 설명 |
|---|---|
| user_id | `User` FK |
| library_id | `Library` FK |
| purpose_id | `Purpose` FK, nullable |
| rating | 1~5 |
| title | 제목, nullable |
| content | 후기 본문 |
| visited_at | 방문일, nullable |
| is_visible | 노출 여부 |
| moderation_status | `pending`, `visible`, `hidden` |
| created_at / updated_at | 관리 시각 |

#### UserReviewImage

`review_id`, `image`, `alt_text`, `display_order`, `created_at`.

외부 URL 대신 사용자 업로드 파일을 자체 스토리지에 저장한다.

#### UserPreference

사용자의 현재 1:1 취향 프로필이다.

| 필드 | 설명 |
|---|---|
| user_id | OneToOne `User` |
| primary_purpose_id | `Purpose` FK, nullable |
| preference_title | 규칙 기반 제목 |
| preference_summary | 규칙 기반 요약 |
| ai_summary | 선택적 AI 문장, nullable |
| ai_prompt_context | AI에 전달한 축약 JSON, nullable |
| calculated_at | 집계 시각 |
| created_at / updated_at | 관리 시각 |

추천 순위는 AI가 아니라 정량 규칙으로 계산한다. AI는 사용자용 문장 생성에만 선택적으로 사용한다.

#### UserPreferenceItem

| 필드 | 설명 |
|---|---|
| user_preference_id | `UserPreference` FK |
| item_type | `library_tag`, `book_kdc`, `program_category`, `region`, `purpose`, `facility` |
| item_code | 항목 코드 |
| item_label | 표시명 |
| score | 선호 점수 |
| count | 집계 횟수 |
| rank | 같은 유형 안 순위 |
| source_count_library / book / program / review | 행동별 기여 수 |
| created_at / updated_at | 관리 시각 |

제약조건: `UNIQUE(user_preference_id, item_type, item_code)`.

---

## 6. 최종 관계도

```mermaid
erDiagram
    DATA_SOURCE ||--o{ SOURCE_SYNC_RUN : runs
    DATA_SOURCE ||--o{ LIBRARY_SOURCE_RECORD : stages
    DATA_SOURCE ||--o{ LIBRARY_EXTERNAL_IDENTIFIER : issues
    DATA_SOURCE ||--o{ LIBRARY_OPENING_HOUR : sources
    DATA_SOURCE ||--o{ LIBRARY_STATISTIC_SNAPSHOT : sources
    DATA_SOURCE ||--o{ PROGRAM : provides
    DATA_SOURCE ||--o{ BOOK_LIST_SNAPSHOT : provides
    DATA_SOURCE ||--o{ MEDIA_ASSET : licenses

    LIBRARY ||--o{ LIBRARY_SOURCE_RECORD : matched_from
    LIBRARY ||--o{ LIBRARY_EXTERNAL_IDENTIFIER : has
    LIBRARY ||--o{ LIBRARY_OPENING_HOUR : opens
    LIBRARY ||--o{ LIBRARY_CLOSURE_RULE : closes
    LIBRARY ||--o{ LIBRARY_STATISTIC_SNAPSHOT : measures
    LIBRARY ||--o{ LIBRARY_FACILITY : provides
    LIBRARY ||--o{ LIBRARY_TAG : tagged
    TAG ||--o{ LIBRARY_TAG : assigned

    PURPOSE ||--o{ PURPOSE_TAG_RULE : uses
    TAG ||--o{ PURPOSE_TAG_RULE : weighted
    PURPOSE ||--o{ PURPOSE_METRIC_RULE : scores

    LIBRARY ||--o{ READING_ROOM : contains
    LIBRARY ||--o{ LIBRARY_OPERATIONAL_STATUS_SNAPSHOT : status
    READING_ROOM ||--o{ READING_ROOM_STATUS_SNAPSHOT : status

    LIBRARY ||--o{ PROGRAM : hosts
    PROGRAM ||--o{ PROGRAM_SESSION : schedules

    LIBRARY ||--o{ LIBRARY_HOLDING : holds
    BOOK ||--o{ LIBRARY_HOLDING : held
    LIBRARY_HOLDING ||--o{ LIBRARY_HOLDING_COPY : copies
    LIBRARY ||--o{ BOOK_AVAILABILITY_SNAPSHOT : checked
    BOOK ||--o{ BOOK_AVAILABILITY_SNAPSHOT : checked
    LIBRARY_HOLDING o|--o{ BOOK_AVAILABILITY_SNAPSHOT : relates

    BOOK_LIST_SNAPSHOT ||--|{ BOOK_LIST_ITEM : contains
    BOOK ||--o{ BOOK_LIST_ITEM : appears
    LIBRARY o|--o{ BOOK_LIST_SNAPSHOT : scopes

    MEDIA_ASSET ||--o{ LIBRARY_IMAGE : used
    LIBRARY ||--o{ LIBRARY_IMAGE : pictured

    USER ||--o{ USER_LIBRARY_SAVE : saves
    LIBRARY ||--o{ USER_LIBRARY_SAVE : saved
    USER ||--o{ USER_BOOK_SAVE : saves
    BOOK ||--o{ USER_BOOK_SAVE : saved
    USER ||--o{ USER_PROGRAM_SAVE : saves
    PROGRAM ||--o{ USER_PROGRAM_SAVE : saved

    USER ||--o{ USER_REVIEW : writes
    LIBRARY ||--o{ USER_REVIEW : reviewed
    PURPOSE o|--o{ USER_REVIEW : purpose
    USER_REVIEW ||--o{ USER_REVIEW_IMAGE : attaches

    USER ||--|| USER_PREFERENCE : summarizes
    PURPOSE o|--o{ USER_PREFERENCE : primary
    USER_PREFERENCE ||--o{ USER_PREFERENCE_ITEM : contains
```

---

## 7. 핵심 무결성·인덱스

| 엔터티 | 제약·인덱스 |
|---|---|
| Library | `(sido, sigungu, library_type, is_active)`, `normalized_name`, 좌표 |
| LibraryExternalIdentifier | `UNIQUE(source_id, code_type, external_code)` |
| LibraryStatisticSnapshot | `UNIQUE(library_id, source_id, reference_date)`, `(library_id, is_current)` |
| LibraryFacility | `UNIQUE(library_id, facility_type, facility_name)` |
| LibraryTag | `UNIQUE(library_id, tag_id, source_method)` |
| ReadingRoom | `UNIQUE(library_id, source_id, external_room_id)` |
| 상태 스냅샷 | `(대상_id, fetched_at DESC)` |
| Program | `UNIQUE(source_id, external_program_id)`, `(library_id, start_at)`, `(lifecycle_status, apply_end_at)` |
| Book | ISBN 조건부 unique, 제목·저자 검색 인덱스 |
| LibraryHolding | `UNIQUE(library_id, book_id)` |
| LibraryHoldingCopy | `UNIQUE(holding_id, source_id, external_copy_key)` |
| BookAvailabilitySnapshot | `(library_id, book_id, fetched_at DESC)` |
| BookListSnapshot | `(list_type, query_hash, fetched_at DESC)` |
| BookListItem | `UNIQUE(snapshot_id, rank)`, `UNIQUE(snapshot_id, book_id)` |
| 저장 테이블 | `UNIQUE(user_id, 대상_id)` |
| UserPreference | `UNIQUE(user_id)` |
| UserPreferenceItem | `UNIQUE(user_preference_id, item_type, item_code)` |

---

## 8. 전국도서관표준데이터 필드 매핑

첨부 JSON은 파일명과 달리 전국 행 3,554건을 포함하며, 이 중 `시도명=부산광역시`가 220건이다. 부산 MVP에서는 로딩 단계에서 지역을 명시적으로 필터링해야 한다.

| 원천 필드 | 저장 위치 |
|---|---|
| 도서관명, 시도명, 시군구명, 도서관유형 | `Library` |
| 소재지도로명주소, 운영기관명, 도서관전화번호, 홈페이지주소, 위도, 경도 | `Library` |
| 평일·토요일·공휴일 운영 시작/종료 | `LibraryOpeningHour`로 확장 |
| 휴관일 | `LibraryClosureRule.raw_text` + 가능한 범위의 `normalized_rule` |
| 열람좌석수, 자료수 3종, 대출가능권수·일수, 부지·건물면적 | `LibraryStatisticSnapshot` |
| 데이터기준일자 | `LibraryStatisticSnapshot.reference_date`, `LibrarySourceRecord.source_reference_date` |
| 제공기관코드·제공기관명 | `LibrarySourceRecord.raw_data` 및 매칭 보조정보 |

정제 규칙:

- `00:00~00:00`은 무조건 운영으로 해석하지 않는다. 휴관 문구와 함께 확인해 `closed` 또는 `unknown`으로 변환한다.
- 빈 좌표는 허용하며 거리순 결과에서 제외하거나 후순위로 둔다.
- `휴관중`, `임시 휴관`은 정기 운영시간과 별개인 `LibraryClosureRule`로 보존한다.
- 숫자형 이상치와 전화번호 placeholder를 검증 큐로 보낸다.
- `전라북도` 같은 구명칭은 현재 행정명칭 alias 테이블로 정규화한다.
- 이름·주소만으로 자동 병합한 결과는 신뢰도와 매칭 근거를 남긴다.

---

## 9. 정보나루 API와 엔터티 매핑

| API | 서비스 사용 | 저장 위치 |
|---|---|---|
| `libSrch` | 참여 도서관 코드·기본정보 매칭 | `LibraryExternalIdentifier`, 보조 검증 |
| `srchBooks` | 책 검색 | `Book` upsert, 검색 결과는 Redis 캐시 |
| `srchDtlList` | 책 상세 | `Book` 갱신 |
| `itemSrch` | 특정 도서관 장서·청구기호·복본 | `LibraryHolding`, `LibraryHoldingCopy` |
| `libSrchByBook` | 특정 ISBN 소장 도서관 | `LibraryHolding` 확인 |
| `bookExist` | 도서관×ISBN 소장·대출 가능 | `BookAvailabilitySnapshot` |
| `loanItemSrch` | 전국 인기대출 | `BookListSnapshot/Item` |
| `loanItemSrchByLib` | 지역·도서관 인기대출 | `BookListSnapshot/Item` |
| `recommandList` | 마니아·다독자 추천 | `BookListSnapshot/Item` |
| `hotTrend` | 급상승 도서 | `BookListSnapshot/Item` |
| `newArrivalBook` | 신착도서 | `BookListSnapshot/Item` |
| `usageAnalysisList` | 함께 대출·이용분석 | 필요 목록만 `co_loan` 스냅샷, 나머지는 Phase 2 |
| `keywordList` | 도서 핵심 키워드 | Phase 2 선택 기능 |
| `usageTrend`, `extends/libSrch` | 도서관 대출·반납 추이 | 상세 분석 기능이 필요할 때 별도 스냅샷으로 확장 |

API 의미상 주의사항:

- `bookExist.loanAvailable`은 조회일 전날 상태다.
- `recommandList`는 최대 5개 ISBN을 입력하고 최대 200개 추천 결과를 받을 수 있다.
- 전국 인기대출은 최대 5,000건, 도서관·지역 인기대출은 최대 200건이다.
- 급상승 도서는 기준일 포함 최근 3일 결과, 일자별 최대 5건이다.
- 통합 도서관별 인기목록은 최근 30일 기준 연령 그룹별 상위 20권이다.

---

## 10. 스냅샷 fresh·보존 정책

| 데이터 | fresh 기준 | DB 보존 | 화면 표시 |
|---|---:|---:|---|
| 열람실 운영·좌석 | 1시간 | 1~7일 | `기준 시각`, stale 여부 |
| 도서 소장 관계 | 7~30일 | 현재 관계 + 변경 이력 필요 시 90일 | 마지막 확인일 |
| 대출 가능 여부 | 24시간 | 30~90일 | `전일 기준` + 확인 시각 |
| 전국·지역·도서관 인기 | 1일 | 최근 3~12개월 선택 | 집계 기간 |
| 마니아·다독자 추천 | 7일 | 최근 N개 버전 | 기준 ISBN |
| 급상승·신착 | 1일 | 최근 3~12개월 선택 | 기준일 |
| 프로그램 미러 | 원천별 6~24시간 | 현재 + soft delete | 공식 링크·수집 시각 |
| 도서 상세 | 30~90일 | 선택적 영구 캐시 | 메타데이터 원천 |

fresh가 지났다는 이유로 최신 스냅샷을 즉시 삭제하지 않는다. 외부 API 장애 시 마지막 성공 결과를 `is_stale=true`로 반환할 수 있다.

---

## 11. 기존 ERD 대비 주요 변경 결과

1. `Library`의 운영시간·통계 필드를 별도 테이블로 분리했다.
2. `LibraryExternalCode`를 원천 FK와 이력을 가진 `LibraryExternalIdentifier`로 교체했다.
3. `ReadingRoomStatusSnapshot`에서 열람실 마스터를 `ReadingRoom`으로 분리했다.
4. 열람실 fresh 정책을 1시간으로 확정하고 상세 화면에서만 사용하도록 제한했다.
5. `LibraryBook`을 `LibraryHolding`, `LibraryHoldingCopy`, `BookAvailabilitySnapshot`으로 분리했다.
6. `BookRankingSnapshot`을 `BookListSnapshot`과 `BookListItem`으로 분리했다.
7. 프로그램을 DB 미러·soft delete 구조로 확정했다.
8. 동적 상태 태그를 제거하고 `PurposeMetricRule`로 점수 계산을 분리했다.
9. 목적 코드를 `study`, `book`, `kids`, `program`, `mood`, `nearby`로 통일했다.
10. 이미지에 공공누리 이용조건과 출처표시 메타데이터를 추가했다.
11. 현재 위치 좌표를 사용자 모델에 저장하지 않는 정책을 명시했다.
12. 원본 파일과 자동 매칭 과정을 추적하기 위해 `LibrarySourceRecord`를 추가했다.

---

## 12. MVP 경계

### MVP 포함

- 부산 지역 도서관 기본정보·운영시간·시설·정적 통계 검색
- 6개 방문 목적 기반 규칙 추천
- 도서관 상세 열람실 상태 1시간 캐시
- 정보나루 도서 검색·상세·소장·대출 가능·인기·추천 목록
- 프로그램 통합 검색과 공식 신청 링크
- 도서관·책·프로그램 저장, 후기, 취향 집계
- 공식 대표 이미지와 이용허락 표시

### MVP 제외 또는 후순위

- 전국 전체 장서 사전 적재
- 서비스 내부 프로그램 신청·결제
- 실시간 좌석 기반 홈 추천
- 후기 텍스트의 자동 태깅
- 도서 키워드·대출추이 전체 장기 분석
- AI가 직접 추천 순위를 결정하는 기능

---

## 13. 참고 원천

- 전국도서관표준데이터: https://www.data.go.kr/data/15013109/standard.do
- 공공도서관 열람실 현황 실시간 정보: https://www.data.go.kr/data/15142580/openapi.do
- 도서관 정보나루 Open API: https://www.data4library.kr/apiUtilization
- 공공누리: https://www.kogl.or.kr/info/freeUse.do
- 부산광역시 Big-데이터웨이브: https://data.busan.go.kr/

