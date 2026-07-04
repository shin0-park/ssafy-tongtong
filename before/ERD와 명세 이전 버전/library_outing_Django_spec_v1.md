# 도서관 나들이 Django 개발 명세서

- 문서 버전: 1.0
- 작성 기준일: 2026-06-21
- 기준 ERD: `도서관_나들이_ERD_수정결과본.md`
- 대상: Django REST API 백엔드 및 데이터 수집·동기화 작업
- 1차 서비스 범위: 부산 지역 MVP, 전국 확장 가능한 구조

---

## 1. 목적과 전제

이 문서는 다음 기능을 Django로 구현하기 위한 개발 기준이다.

1. 방문 목적별 도서관 추천
2. 도서관 검색·상세 조회
3. 도서 검색과 소장 도서관 조회
4. 인기·마니아·다독자·급상승·신착 도서 목록
5. 도서관 프로그램 통합 검색
6. 도서관·책·프로그램 저장, 후기, 취향 집계
7. 외부 공공데이터의 수집, 정규화, 캐시, 장애 대응

서비스 목업은 화면 의도를 파악하는 참고자료로만 사용한다. 목업에 있지만 최종 ERD에 없는 내부 예약·결제·알림 센터 등의 기능은 MVP 명세에 포함하지 않는다.

### 고정 정책

- 홈 추천은 실시간 열람실 API를 사용하지 않는다.
- 열람실 API는 도서관 상세 화면에서만 호출한다.
- 열람실 최신 DB 스냅샷의 `fetched_at`이 1시간 이내이면 외부 호출 없이 재사용한다.
- 브라우저가 제공한 현재 좌표는 해당 HTTP 요청에서만 사용하고 DB에 저장하지 않는다.
- 정보나루 대출 가능 여부는 전일 기준이라고 응답에 명시한다.
- 프로그램 검색은 내부 DB만 조회하며 외부 API 호출은 비동기 동기화 작업에서 수행한다.
- 추천 점수는 규칙 기반이다. AI는 선택적으로 취향 요약 문장만 생성한다.

---

## 2. 권장 기술 스택

### 2.1 런타임·프레임워크

| 항목 | 권장안 | 비고 |
|---|---|---|
| Python | 3.13 | 팀 환경이 3.12라면 3.12도 허용 |
| Django | `>=5.2.15,<5.3` | 5.2 LTS, 2028-04까지 확장 지원 |
| Django REST Framework | `>=3.16,<3.17` | API 구현 |
| PostgreSQL | 16 이상 | JSONB, 조건부 인덱스, 전문검색 활용 |
| Redis | 7 이상 | API 응답 캐시, 분산락, Celery broker/result |
| Celery | `>=5.6,<5.7` | 외부 데이터 수집·선호 재계산 |
| Celery Beat | Celery와 동일 | 주기 작업 |

Django 6.0 최신판보다 5.2 LTS를 선택하는 이유는 학기 프로젝트의 안정성과 지원기간을 우선하기 위해서다.

### 2.2 주요 패키지

```text
Django>=5.2.15,<5.3
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

- 객체 스토리지: `django-storages`, `boto3`
- 운영 모니터링: Sentry SDK
- 데이터 정제: `rapidfuzz`, `python-dateutil`
- 주소·형태소 검색 고도화: PostgreSQL `pg_trgm`, 별도 검색엔진은 Phase 2

---

## 3. 프로젝트 구조

```text
library_outing/
├─ manage.py
├─ pyproject.toml
├─ config/
│  ├─ __init__.py
│  ├─ settings/
│  │  ├─ base.py
│  │  ├─ local.py
│  │  ├─ test.py
│  │  └─ production.py
│  ├─ urls.py
│  ├─ celery.py
│  ├─ asgi.py
│  └─ wsgi.py
├─ apps/
│  ├─ common/
│  ├─ accounts/
│  ├─ sources/
│  ├─ libraries/
│  ├─ books/
│  ├─ programs/
│  ├─ recommendations/
│  ├─ interactions/
│  └─ integrations/
├─ tests/
│  ├─ fixtures/
│  │  ├─ data4library/
│  │  ├─ reading_room/
│  │  └─ programs/
│  └─ contract/
└─ scripts/
```

### 앱 책임

| 앱 | 책임 |
|---|---|
| `common` | 공통 추상 모델, 예외, 페이지네이션, 응답 포맷, 유틸리티 |
| `accounts` | 사용자, 인증, 기본 지역 |
| `sources` | 데이터 원천, 수집 실행, raw staging, 관리 명령 |
| `libraries` | 도서관·운영시간·통계·시설·태그·열람실·이미지 |
| `books` | 도서·소장·복본·대출 가능·도서 목록 스냅샷 |
| `programs` | 프로그램·회차·검색 |
| `recommendations` | 방문 목적, 규칙, 추천 점수 계산 |
| `interactions` | 저장, 후기, 사용자 취향 |
| `integrations` | 외부 API 클라이언트·provider adapter·normalizer |

뷰나 serializer에서 외부 API를 직접 호출하지 않는다. 모든 외부 통신은 `integrations`의 client와 도메인 service를 통해 수행한다.

---

## 4. 환경변수

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,api.example.com
DATABASE_URL=postgresql://user:password@db:5432/library_outing
REDIS_URL=redis://redis:6379/0

DATA4LIBRARY_BASE_URL=http://data4library.kr/api
DATA4LIBRARY_AUTH_KEY=
READING_ROOM_API_BASE_URL=
READING_ROOM_API_SERVICE_KEY=

SERVICE_DEFAULT_SIDO=부산광역시
SERVICE_DEFAULT_SIGUNGU=
SERVICE_DEFAULT_REGION_CODE=21

PROGRAM_PROVIDER_DONGNAE_BASE_URL=
PROGRAM_PROVIDER_DONGNAE_KEY=
PROGRAM_PROVIDER_BUSANJIN_BASE_URL=
PROGRAM_PROVIDER_BUSANJIN_KEY=

MEDIA_STORAGE_BACKEND=local
AWS_STORAGE_BUCKET_NAME=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_ENDPOINT_URL=

AI_SUMMARY_ENABLED=false
AI_API_KEY=
```

보안 규칙:

- API 인증키를 프론트엔드에 노출하지 않는다.
- URL 전체를 로그로 남길 때 `authKey`, `serviceKey`를 마스킹한다.
- production에서는 `.env` 파일을 배포 이미지에 포함하지 않는다.
- 외부 응답 원문에 개인정보가 포함될 가능성을 점검한 후 raw 저장 범위를 제한한다.

---

## 5. Django 설정 기준

```python
# config/settings/base.py
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}
```

- 동일 출처의 날짜·시간은 파싱 즉시 aware datetime으로 변환한다.
- 외부 API의 한국 시각 기준일은 `ZoneInfo("Asia/Seoul")`를 명시한다.
- 사용자 업로드 이미지 최대 크기와 MIME allowlist를 설정한다.

---

## 6. 모델 구현 명세

아래는 Django 필드 선택 기준이다. 세부 의미는 ERD 수정결과본을 따른다.

### 6.1 공통 추상 모델

```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

soft delete가 필요한 모델은 `deleted_at`과 `is_visible` 또는 `is_active`를 명시적으로 사용한다. 전역 soft-delete manager를 남용하지 않는다. 관리자 화면에서는 삭제 행을 확인할 수 있어야 한다.

### 6.2 accounts

#### User

- 상속: `AbstractUser`
- `email`: `EmailField(unique=True)`
- `nickname`: `CharField(max_length=50)`
- `default_sido`: `CharField(max_length=30, blank=True)`
- `default_sigungu`: `CharField(max_length=30, blank=True)`
- 현재 위치 좌표 필드 금지

회원가입 전에 커스텀 User 모델을 생성하고 첫 migration에 포함한다.

### 6.3 sources

#### DataSource

- `code`: `SlugField(max_length=80, unique=True)`
- `source_kind`: `CharField(choices=SourceKind)`
- `base_url`: `URLField(blank=True)`
- `default_ttl_seconds`: `PositiveIntegerField(null=True, blank=True)`
- `priority`: `SmallIntegerField(default=100)`

#### SourceSyncRun

- `source`: FK `PROTECT`
- `status`: choices
- 카운트 필드: `PositiveIntegerField(default=0)`
- `metadata`: `JSONField(default=dict, blank=True)`
- 인덱스: `(source, -started_at)`, `(status, -started_at)`

#### LibrarySourceRecord

- `raw_data`: `JSONField`
- `content_hash`: `CharField(max_length=64, db_index=True)`
- `match_confidence`: `DecimalField(max_digits=5, decimal_places=4, null=True)`
- `matched_library`: FK `SET_NULL`
- 인덱스: `(source, external_record_key)`, `(match_status, -fetched_at)`

### 6.4 libraries

#### Library

- 이름·지역·주소: `CharField`
- 좌표: `DecimalField(max_digits=10, decimal_places=7, null=True)`
- 홈페이지: `URLField(blank=True)`
- `is_active`: `BooleanField(default=True, db_index=True)`
- 검색 인덱스:
  - `Index(fields=["sido", "sigungu", "library_type", "is_active"])`
  - `GinIndex(fields=["normalized_name"], opclasses=["gin_trgm_ops"])`는 `pg_trgm` 활성화 시 적용

초기 MVP는 위도·경도와 Haversine 계산으로 구현한다. 거리 검색량이 커지면 GeoDjango의 `PointField`와 PostGIS로 교체한다.

#### LibraryExternalIdentifier

```python
models.UniqueConstraint(
    fields=["source", "code_type", "external_code"],
    name="uq_external_library_identifier",
)
```

#### LibraryOpeningHour

- `day_type`, `day_of_week`, `specific_date` 조합에 `CheckConstraint` 적용
- `schedule_status="open"`이면 open/close time 필수
- 야간 운영이 자정을 넘는 경우 `closes_next_day=True` 필드 추가 가능
- `is_current` 인덱스

#### LibraryStatisticSnapshot

- 모든 숫자는 원천 결측을 표현하기 위해 `null=True`
- `reference_date`: `DateField`
- 현재 행 전환은 transaction에서 기존 `is_current=False` 후 새 행 true

#### LibraryFacility, Tag, LibraryTag

- `facility_type`, `tag_group`은 `TextChoices`
- 운영자 검수 필드와 근거 URL 보존
- `LibraryTag`에서 만료시간·실시간 태그 사용 금지

#### ReadingRoom, LibraryOperationalStatusSnapshot, ReadingRoomStatusSnapshot

- 스냅샷 모델의 기본 정렬: `-fetched_at`
- 상태 값은 원천 문자열이 아닌 내부 choice로 정규화
- 계산 가능한 `occupancy_rate`는 저장 전에 0~1 범위 검증
- `available_seats`가 음수가 되지 않도록 `CheckConstraint`

#### MediaAsset, LibraryImage

- `storage_object_key`는 파일시스템 절대 경로가 아닌 storage backend key
- 공공누리 라이선스 메타데이터 필수
- `LibraryImage` 대표 이미지 조건부 unique:

```python
models.UniqueConstraint(
    fields=["library"],
    condition=Q(is_main=True),
    name="uq_active_main_image_per_library",
)
```

실제 삭제 대신 `MediaAsset.is_active=False`로 차단한다.

### 6.5 programs

#### Program

- `source`: FK `PROTECT`
- `library`: FK `PROTECT`
- `external_program_id`: `CharField(max_length=255)`
- `target_codes`: `JSONField(default=list)`
- `fee_amount`: `DecimalField(max_digits=10, decimal_places=2, null=True)`
- `content_hash`: `CharField(max_length=64)`
- unique: `(source, external_program_id)`
- 인덱스:
  - `(library, start_at)`
  - `(lifecycle_status, apply_end_at)`
  - `(is_visible, start_at)`
  - `target_codes` JSONB GIN 선택

`lifecycle_status`는 아래 순서로 재계산한다.

1. 원천 취소 값이면 `canceled`
2. `end_at < now`이면 `ended`
3. 운영기간 안이면 `ongoing`
4. 신청기간 안이면 `recruiting`
5. 신청 종료 후 운영 전이면 `closed`
6. 그 외 미래 일정은 `scheduled`
7. 날짜 부족 시 `unknown`

#### ProgramSession

반복 프로그램에서만 생성한다. 단일 회차는 Program의 start/end만 사용해도 된다.

### 6.6 books

#### Book

- `isbn13`: `CharField(max_length=13, null=True, blank=True)`
- 조건부 unique:

```python
models.UniqueConstraint(
    fields=["isbn13"],
    condition=Q(isbn13__isnull=False) & ~Q(isbn13=""),
    name="uq_book_nonempty_isbn13",
)
```

- ISBN 입력 시 숫자 13자리와 체크디지트 검증을 권장
- 제목은 필수, 저자·출판사 등은 nullable/blank 허용

#### LibraryHolding

- unique `(library, book)`
- 단일 `bookExist=N` 응답만으로 기존 소장 관계를 즉시 비활성화하지 않는다.
- 반복된 부정 확인 또는 `itemSrch` 전체 동기화에서 사라진 경우 정책에 따라 비활성화한다.

#### LibraryHoldingCopy

- 원천 copy ID가 없으면 다음 정규화 문자열의 해시를 사용한다.

```text
holding_id|call_number|shelf_location_code|copy_code|registered_date
```

#### BookAvailabilitySnapshot

- `source_effective_date`: 반드시 저장
- 정보나루 응답은 조회일 전날이므로 normalizer가 한국 날짜 기준 `today - 1 day`를 기본값으로 설정
- 인덱스 `(library, book, -fetched_at)`

#### BookListSnapshot, BookListItem

- `query_hash`는 auth key·pageNo를 제외한 정규화 쿼리의 SHA-256
- `query_params`의 key 정렬 및 다중값 정렬 후 해시
- snapshot과 items는 하나의 transaction에서 저장
- items 저장 전에 같은 ISBN의 Book을 bulk upsert

### 6.7 recommendations

#### Purpose, PurposeTagRule, PurposeMetricRule

- 운영자가 admin에서 가중치를 조정 가능
- `normalization_rule` 예시:

```json
{
  "method": "piecewise",
  "points": [
    {"gte": 300, "score": 1.0},
    {"gte": 150, "score": 0.7},
    {"gte": 50, "score": 0.4}
  ],
  "missing": 0.0
}
```

규칙 변경에는 `updated_at`을 기록하고 추천 응답에 `rule_version`을 포함할 수 있다.

### 6.8 interactions

- 저장 모델 unique `(user, target)`
- `UserReview.rating`: 1~5 check constraint
- `UserReviewImage`: 최대 5장, 파일당 크기 제한
- `UserPreference`: `OneToOneField(User)`
- `UserPreferenceItem`: unique `(user_preference, item_type, item_code)`

---

## 7. 외부 API 통합 구조

### 7.1 공통 HTTP client 정책

```python
@dataclass(frozen=True)
class ExternalRequestPolicy:
    connect_timeout: float = 3.0
    read_timeout: float = 7.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5
```

- GET 요청만 네트워크 오류·502·503·504에 한해 재시도
- 4xx는 재시도하지 않음
- JSON 요청 시 `format=json`을 명시할 수 있으면 명시
- 응답 Content-Type과 실제 body를 모두 검증
- 인증키·사용자 검색어를 로그에 원문으로 남기지 않음
- upstream 응답을 그대로 API 사용자에게 노출하지 않음
- 외부 오류는 내부 코드로 변환

### 7.2 Data4LibraryClient

```python
class Data4LibraryClient:
    def search_libraries(...): ...          # libSrch
    def search_books(...): ...              # srchBooks
    def get_book_detail(isbn13: str, ...): ...
    def get_library_items(...): ...          # itemSrch
    def get_holding_libraries(...): ...      # libSrchByBook
    def get_book_availability(...): ...      # bookExist
    def get_popular_books(...): ...          # loanItemSrch
    def get_popular_books_by_scope(...): ... # loanItemSrchByLib
    def get_recommendations(...): ...         # recommandList
    def get_hot_trend(...): ...
    def get_new_arrivals(...): ...
    def get_usage_analysis(...): ...
```

#### 파라미터 검증

- `isbn13`: 문자열 10 또는 13자리, API별 요구에 맞게 검증
- 다중 ISBN: 세미콜론 결합, 최대 5개
- `region`, `dtl_region`: 코드 테이블 검증
- 인기 목록 날짜는 `YYYY-MM-DD`
- 신착 기준월은 `YYYY-MM`
- `kdc`와 `dtl_kdc` 동시 사용 제한을 client에서 검증
- `pageSize`는 서비스 상한을 별도로 두어 과도한 응답 방지

#### normalizer 반환 객체

원천 XML/JSON 구조를 Django 모델과 분리하기 위해 dataclass를 사용한다.

```python
@dataclass(frozen=True)
class NormalizedBook:
    isbn13: str | None
    title: str
    authors_text: str | None
    publisher: str | None
    publication_year: int | None
    kdc_class_no: str | None
    kdc_class_name: str | None
    cover_image_url: str | None
```

원천 필드명이 바뀌면 normalizer와 contract test만 수정하도록 한다.

### 7.3 ReadingRoomClient

공공데이터포털 설명상 세 종류의 정보를 제공한다.

1. 공공도서관 통합정보
2. 공공도서관 운영상태·방문자·좌석사용률
3. 열람실 정의와 실시간 이용가능 좌석

공개 상세 페이지에는 실제 Swagger operation ID와 전체 필드가 노출되지 않으므로 명세서에서 임의 endpoint 이름을 확정하지 않는다. 활용신청 후 Swagger를 기준으로 다음 adapter를 구현한다.

```python
class ReadingRoomProvider(Protocol):
    def fetch_library_catalog(self, **filters) -> list[NormalizedLibraryRef]: ...
    def fetch_library_status(self, external_library_id: str) -> NormalizedLibraryStatus: ...
    def fetch_room_statuses(self, external_library_id: str) -> list[NormalizedRoomStatus]: ...
```

확정해야 할 매핑 체크리스트:

- 외부 도서관 ID의 범위와 안정성
- 열람실 ID가 전국 고유인지 도서관 내부 고유인지
- 원천 갱신 시각 필드
- 전체·사용·예약·이용가능 좌석 필드
- 운영상태 코드와 휴관 의미
- 방문자 수의 단위와 null 의미
- 페이지네이션·트래픽 제한·에러코드
- 좌석 합계가 서로 불일치할 때 우선순위

### 7.4 프로그램 provider adapter

부산 프로그램은 하나의 완전한 통합 API가 아니라 구·도서관별 제공처가 섞여 있으므로 provider pattern을 사용한다.

```python
class ProgramProvider(ABC):
    source_code: str

    @abstractmethod
    def fetch(self, *, modified_since: datetime | None = None) -> Iterable[RawProgram]: ...

    @abstractmethod
    def normalize(self, raw: RawProgram) -> NormalizedProgram: ...
```

초기 provider 예시:

- 동래구 도서관 강좌 API/파일
- 부산진구 통합 예약 현황 API
- Big-데이터웨이브 도서관별 데이터셋
- 공식 도서관 홈페이지 HTML parser
- 수동 입력 provider

동일 프로그램 병합은 `source + external_program_id`를 1차 키로 사용한다. 서로 다른 원천의 중복 프로그램을 강제 병합하지 말고 운영자 검수용 `canonical_program_id` 확장을 Phase 2로 둔다.

### 7.5 공공누리 이미지

수집 시 다음을 확인한다.

- 원문 페이지 URL
- 저작물 ID
- 공공누리 유형
- 출처표시 문구
- 상업적 이용 가능 여부
- 변경 가능 여부
- 라이선스 확인 시각

변경 불가 유형은 임의 크롭을 금지한다. 썸네일 생성이 변경에 해당할 수 있으므로 라이선스 정책을 검토하고 원본 비율 리사이즈만 허용하는 별도 처리 규칙을 둔다.

---

## 8. REST API 명세

기본 prefix: `/api/v1`

### 8.1 공통 응답

#### 목록

```json
{
  "count": 24,
  "next": "/api/v1/libraries?page=2",
  "previous": null,
  "results": []
}
```

#### 오류

```json
{
  "code": "UPSTREAM_UNAVAILABLE",
  "message": "외부 도서 정보 제공처에 일시적으로 연결할 수 없습니다.",
  "details": {},
  "request_id": "01J..."
}
```

주요 오류 코드:

- `VALIDATION_ERROR`
- `AUTHENTICATION_REQUIRED`
- `PERMISSION_DENIED`
- `NOT_FOUND`
- `UPSTREAM_UNAVAILABLE`
- `UPSTREAM_RATE_LIMITED`
- `EXTERNAL_MAPPING_MISSING`
- `STALE_DATA_ONLY`

### 8.2 인증·사용자

| Method | URL | 인증 | 설명 |
|---|---|---|---|
| POST | `/auth/signup/` | 없음 | 회원가입 |
| POST | `/auth/token/` | 없음 | access/refresh 발급 |
| POST | `/auth/token/refresh/` | 없음 | access 갱신 |
| GET | `/me/` | 필요 | 프로필 |
| PATCH | `/me/` | 필요 | nickname, 기본 지역 수정 |
| GET | `/me/dashboard/` | 필요 | 나의 나들이 요약 |

회원가입 body:

```json
{
  "username": "library_user",
  "email": "user@example.com",
  "password": "...",
  "nickname": "김나들이",
  "default_sido": "부산광역시",
  "default_sigungu": "해운대구"
}
```

### 8.3 기준정보

| Method | URL | 설명 |
|---|---|---|
| GET | `/purposes/` | 6개 방문 목적 |
| GET | `/metadata/regions/` | 지역 선택용 목록 |
| GET | `/metadata/library-types/` | 도서관 유형 |
| GET | `/metadata/facilities/` | 시설 코드 |
| GET | `/metadata/program-categories/` | 프로그램 분류 |

### 8.4 홈 추천

#### GET `/home/recommendations/`

Query:

| 이름 | 필수 | 설명 |
|---|---|---|
| purpose | 예 | `study`, `book`, `kids`, `program`, `mood`, `nearby` |
| sido / sigungu | 조건부 | 지역 기반 후보 |
| lat / lng | 아니오 | 브라우저 현재 좌표, 저장하지 않음 |
| limit | 아니오 | 기본 6, 최대 20 |

지역 결정 우선순위:

1. 요청 `sido`, `sigungu`
2. 인증 사용자의 `default_sido`, `default_sigungu`
3. 설정의 `SERVICE_DEFAULT_SIDO`

현재 좌표가 있으면 거리 지표를 계산하되 서버 로그와 DB에 좌표를 저장하지 않는다.

응답 예시:

```json
{
  "purpose": {
    "code": "study",
    "label": "조용히 공부하고 싶어요"
  },
  "region": {
    "sido": "부산광역시",
    "sigungu": null
  },
  "location_used": true,
  "rule_version": "2026-06-21T10:00:00+09:00",
  "results": [
    {
      "library": {
        "id": 101,
        "name": "수영구도서관",
        "address": "...",
        "library_type": "public",
        "main_image": null
      },
      "score": 86.4,
      "distance_m": 1540,
      "is_open_now": true,
      "reasons": [
        "열람좌석이 많은 편이에요",
        "스터디 공간이 확인되었어요",
        "오늘 늦게까지 운영해요"
      ]
    }
  ]
}
```

이 endpoint에서 열람실 실시간 API를 호출하지 않는다.

### 8.5 도서관

#### GET `/libraries/`

Query filters:

- `q`: 도서관명·주소
- `sido`, `sigungu`
- `library_type`: 다중값 허용
- `facility`: 다중값, AND/OR 정책은 `facility_mode`
- `tag`
- `open_now=true`
- `weekend_open=true`
- `holiday_open=true`
- `late_open_after=21:00`
- `min_book_count`
- `min_seat_count`
- `lat`, `lng`, `radius_m`
- `ordering=distance|name|-book_count|-reading_seat_count|-review_rating`

`open_now`는 `LibraryOpeningHour`와 현재 적용되는 `LibraryClosureRule`로 계산한다. 외부 API를 호출하지 않는다.

카드 응답:

```json
{
  "id": 101,
  "name": "연제도서관",
  "library_type": "public",
  "address": "부산광역시 ...",
  "coordinates": {"latitude": 35.0, "longitude": 129.0},
  "today_hours": {"status": "open", "open": "09:00", "close": "21:00"},
  "is_open_now": true,
  "latest_statistics": {
    "reference_date": "2026-05-01",
    "reading_seat_count": 220,
    "book_count": 115000
  },
  "facilities": ["study_room", "wifi", "parking"],
  "tags": [
    {"code": "many_seats", "label": "열람좌석 많음"}
  ],
  "main_image": null,
  "distance_m": 2310,
  "is_saved": false
}
```

#### GET `/libraries/{id}/`

포함:

- 기본정보
- 오늘·주간 운영시간
- 휴관 원문
- 최신 통계와 기준일
- 시설·안정적 태그
- 공식 이미지·출처
- 예정 프로그램 일부
- 후기 요약
- 정보나루 연계 가능 여부
- 열람실 API 연계 가능 여부

열람실 현재 상태는 이 응답에 강제로 포함하지 않고 별도 endpoint를 사용한다.

#### GET `/libraries/{id}/reading-rooms/status/`

처리:

1. 해당 도서관의 열람실 API external ID 확인
2. 최근 성공 snapshot 조회
3. `fetched_at >= now - 1시간`이면 즉시 반환
4. fresh가 아니면 Redis lock 획득 후 외부 API 호출
5. 정상 응답을 transaction으로 저장
6. 실패 시 과거 snapshot이 있으면 `is_stale=true`로 반환
7. 과거 데이터도 없으면 503

응답:

```json
{
  "library_id": 101,
  "supported": true,
  "operation_status": "open",
  "source_updated_at": "2026-06-21T13:35:00+09:00",
  "fetched_at": "2026-06-21T13:36:10+09:00",
  "fresh_until": "2026-06-21T14:36:10+09:00",
  "is_stale": false,
  "rooms": [
    {
      "id": 12,
      "name": "제1열람실",
      "floor_info": "3층",
      "total_seats": 120,
      "used_seats": 72,
      "available_seats": 48,
      "occupancy_rate": 0.6,
      "status": "available"
    }
  ]
}
```

외부 코드가 없으면 404 대신 다음처럼 기능 미지원 응답을 권장한다.

```json
{
  "library_id": 101,
  "supported": false,
  "reason": "EXTERNAL_MAPPING_MISSING",
  "rooms": []
}
```

#### GET/POST `/libraries/{id}/reviews/`

- GET: 공개 후기 목록
- POST: 인증 필요
- rating 1~5, content 필수
- `multipart/form-data` 이미지 최대 5장

### 8.6 책

#### GET `/books/search/`

Query:

| 이름 | 설명 |
|---|---|
| search_type | `title`, `author`, `isbn`, `keyword`, `publisher` |
| q | 검색어 |
| exact | 정확 일치 여부 |
| sort | `loan`, `title`, `author`, `pub`, `pubYear`, `isbn` |
| order | `asc`, `desc` |
| page / page_size | 페이지 |

처리:

- 동일 쿼리 Redis 캐시 6시간
- 캐시 miss 시 `srchBooks` 호출
- 결과 도서 bulk upsert
- API 키는 query hash에서 제외
- 검색결과에 대출건수는 원천 기준 값임을 표시

#### GET `/books/{isbn13}/`

- Book 메타데이터가 30일 이내면 DB 반환
- 오래되었거나 description이 없으면 `srchDtlList` 호출 후 갱신
- 상세 API 실패 시 기존 DB 값이 있으면 stale 메타데이터 반환
- 선택적 `include=analysis`는 Phase 2

#### GET `/books/{isbn13}/libraries/`

Query:

- `region`: 정보나루 광역 코드. 기본 부산 `21`
- `detail_region`: 선택
- `lat`, `lng`: 거리 계산용, 저장하지 않음
- `include_availability=true|false`

처리:

1. 동일 ISBN·지역의 소장 도서관 조회 캐시가 7일 이내면 사용
2. 아니면 `libSrchByBook` 호출
3. 내부 `LibraryExternalIdentifier`로 매칭
4. `LibraryHolding` upsert
5. `include_availability=true`일 때만 각 도서관에 대해 `bookExist`를 호출
6. 동시 호출은 semaphore와 서비스 상한을 적용
7. 각 availability는 24시간 캐시

응답:

```json
{
  "isbn13": "9780000000000",
  "region_code": "21",
  "results": [
    {
      "library": {"id": 101, "name": "연제도서관", "address": "..."},
      "has_book": true,
      "loan_available": true,
      "availability_basis": "previous_day",
      "source_effective_date": "2026-06-20",
      "checked_at": "2026-06-21T10:30:00+09:00",
      "distance_m": 2010
    }
  ]
}
```

`loan_available`이 null이면 미지원·조회실패·미제공을 구분하는 `availability_status`를 함께 반환한다.

#### GET `/book-lists/`

Query:

- `type`: list type
- `region`, `detail_region`, `library_id`
- `seed_isbn`: 복수 가능, 최대 5
- `start_date`, `end_date`
- `age`, `gender`, `kdc`, `detail_kdc`
- `limit`

목록 refresh 정책:

| type | fresh |
|---|---:|
| popular_national/region/library | 24시간 |
| mania/reader | 7일 |
| hot_trend | 24시간 |
| new_arrival | 24시간 |
| co_loan | 7일 |

일반 사용자 요청은 가능하면 DB 최신 snapshot을 반환한다. snapshot이 없거나 만료되었을 때 동기 refresh를 허용할지 여부는 유형별로 결정한다. 홈·메인 노출 목록은 Celery가 미리 생성한다.

### 8.7 프로그램

#### GET `/programs/`

Filters:

- `q`: 프로그램명·도서관명
- `sido`, `sigungu`
- `library_id`
- `category`
- `target`
- `start_from`, `start_to`
- `application_status`: `recruiting`, `closed`, `scheduled`, `ongoing`
- `ordering=start_at|-start_at|apply_end_at|title`

외부 API를 호출하지 않는다.

응답:

```json
{
  "id": 501,
  "title": "나만의 문장 수집 노트",
  "category": "reading_writing",
  "library": {"id": 101, "name": "마포중앙도서관"},
  "target_text": "성인",
  "target_codes": ["adult"],
  "start_at": "2026-06-14T10:00:00+09:00",
  "end_at": "2026-07-05T12:00:00+09:00",
  "apply_start_at": null,
  "apply_end_at": null,
  "lifecycle_status": "recruiting",
  "place": "배움실 2",
  "fee_text": "무료",
  "source_url": "...",
  "apply_url": "...",
  "is_saved": false
}
```

#### GET `/programs/{id}/`

프로그램 상세, 회차, 공식 신청 URL, 원천 표시, 마지막 동기화 시각을 반환한다.

### 8.8 나의 나들이

| Method | URL | 설명 |
|---|---|---|
| GET | `/me/saved-libraries/` | 저장 도서관 |
| PUT | `/me/saved-libraries/{library_id}/` | 저장·메모 upsert |
| DELETE | `/me/saved-libraries/{library_id}/` | 저장 해제 |
| GET | `/me/saved-books/` | 찜한 책 |
| PUT/DELETE | `/me/saved-books/{book_id}/` | 저장/해제 |
| GET | `/me/saved-programs/` | 관심·예정 프로그램 |
| PUT/PATCH/DELETE | `/me/saved-programs/{program_id}/` | 상태·메모 관리 |
| GET | `/me/reviews/` | 작성 후기 |
| PATCH/DELETE | `/me/reviews/{review_id}/` | 본인 후기 수정/삭제 |
| GET | `/me/preference/` | 취향 프로필 |
| POST | `/me/preference/recalculate/` | 수동 재계산 요청 |

저장·후기 변경 후 preference 계산 task를 즉시 실행하지 않고 30~60초 debounce할 수 있다.

---

## 9. 추천 로직 명세

### 9.1 후보군

```text
활성 도서관
∩ 선택 지역
∩ 목적별 필수 조건
∩ 좌표가 필요한 경우 좌표 보유 도서관
```

사용 데이터:

- `Library`
- 현재 `LibraryOpeningHour`, `LibraryClosureRule`
- 최신 `LibraryStatisticSnapshot`
- 활성 `LibraryFacility`, `LibraryTag`
- 향후 30일 활성 프로그램 수
- 후기 평균·개수
- 공식 이미지 유무
- 요청 좌표와 계산한 거리
- 사용자 `UserPreferenceItem`의 약한 보너스

사용하지 않는 데이터:

- `ReadingRoomStatusSnapshot`
- `LibraryOperationalStatusSnapshot`의 방문자·좌석사용률
- 대출 가능 여부

### 9.2 점수식

```text
base_score = Σ(rule.weight × normalized_feature)
required_pass = 모든 is_required 규칙 충족
preference_bonus = 사용자 상위 취향과 일치한 제한적 가산점
final_score = normalize(base_score + preference_bonus, 0..100)
```

- 거리 점수: 가까울수록 높은 역거리 또는 구간점수
- 결측값: 규칙의 `missing` 정책 적용
- 매우 큰 통계값의 독주를 막기 위해 log 또는 percentile normalization 사용
- 추천 사유는 점수 기여도가 큰 상위 3개 규칙에서 생성
- 동점: 거리, 검증 데이터 충실도, 후기 수, 도서관명 순

### 9.3 목적별 기본 feature

| 목적 | 핵심 feature |
|---|---|
| study | 정적 열람좌석 수, 스터디룸, 조용한 공간 태그, 늦은 폐관, Wi-Fi |
| book | 도서 자료 수, 자료실·디지털실, 정보나루 연계 여부, 사용자 KDC 선호 |
| kids | 어린이자료실, 수유실, 어린이 대상 프로그램, 가족 편의시설 |
| program | 향후 프로그램 수, 신청 가능 프로그램 수, 선호 분류 일치 |
| mood | 내부 공식 이미지, 자연채광·카페·라운지·전시공간, 후기 평점 |
| nearby | 거리, 현재 운영 여부, 주차·접근성 태그 |

`study`는 열람실 실시간 잔여좌석을 사용하지 않는다.

### 9.4 Haversine

```python
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))
```

- 요청 lat: -90~90, lng: -180~180 검증
- 현재 좌표를 모델·캐시 key·분석 로그에 원문으로 저장하지 않음
- 거리 캐시가 필요하면 좌표를 낮은 정밀도 geohash로 일시 캐시하되 개인정보 검토 후 적용

---

## 10. 캐시·스냅샷 처리

### 10.1 열람실 1시간 캐시

```python
@transaction.atomic
def persist_room_payload(library, payload, fetched_at):
    # ReadingRoom upsert
    # LibraryOperationalStatusSnapshot insert
    # ReadingRoomStatusSnapshot bulk_create
    ...
```

서비스 의사코드:

```python
def get_room_status(library_id: int):
    latest = repository.get_latest_success(library_id)
    if latest and latest.fetched_at >= now() - timedelta(hours=1):
        return build_response(latest, is_stale=False)

    with redis_lock(f"reading-room:{library_id}", timeout=30):
        latest = repository.get_latest_success(library_id)
        if latest and latest.fetched_at >= now() - timedelta(hours=1):
            return build_response(latest, is_stale=False)

        try:
            payload = provider.fetch(...)
            snapshot = persist(payload)
            return build_response(snapshot, is_stale=False)
        except ExternalServiceError:
            if latest:
                return build_response(latest, is_stale=True)
            raise UpstreamUnavailable()
```

- lock 대기시간은 짧게 설정
- 여러 방 snapshot이 부분 저장되지 않도록 transaction 사용
- 실패 응답은 snapshot으로 저장하지 않고 sync log에 기록

### 10.2 도서 검색

Redis key:

```text
book-search:v1:{sha256(normalized_query)}
```

TTL 6시간. 검색 결과 Book 자체는 DB에 upsert한다. Redis가 삭제되어도 저장한 책과 사용자 저장 FK는 유지된다.

### 10.3 대출 가능 여부

Redis를 별도로 사용하지 않아도 최신 DB snapshot 조회로 충분하다.

```text
fresh = latest.fetched_at >= now - 24h
```

- negative result도 캐시
- API 실패 시 과거 snapshot을 반환할 수 있으나 `is_stale=true`
- 응답에 `source_effective_date`와 `availability_basis="previous_day"` 포함

### 10.4 목록 snapshot

1. query params 정규화
2. `query_hash` 계산
3. 최신 fresh snapshot 확인
4. 필요 시 API 호출
5. Book bulk upsert
6. snapshot + items transaction 저장
7. 이전 snapshot은 보존정책에 따라 정리

동일 snapshot 생성 race는 Redis lock `book-list:{type}:{query_hash}`로 제어한다.

---

## 11. 데이터 수집·Celery 작업

### 11.1 작업 목록

| Task | 주기 | 설명 |
|---|---|---|
| `sources.sync_library_standard` | 월 1회 또는 파일 갱신 시 | 표준데이터 raw 적재·정규화·매칭 |
| `sources.sync_data4library_libraries` | 주 1회 | 정보나루 참여 도서관 코드 갱신 |
| `programs.sync_all_providers` | 6시간마다 | 모든 프로그램 provider 동기화 |
| `programs.recompute_lifecycle_statuses` | 매시간 | 신청·운영 상태 재계산 |
| `books.refresh_featured_book_lists` | 매일 새벽 | 홈·책 둘러보기 인기·급상승·신착 |
| `books.cleanup_old_snapshots` | 매일 | 정책 초과 snapshot 정리 |
| `libraries.cleanup_room_snapshots` | 매일 | 1~7일 초과 원본 상태 정리 |
| `interactions.rebuild_user_preference` | 이벤트 debounce + 매일 보정 | 사용자 취향 재계산 |
| `libraries.verify_media_assets` | 월 1회 | 링크·라이선스 점검 |
| `sources.audit_unmatched_records` | 매일/수동 | 미매칭 원천 행 보고서 |

### 11.2 Celery 설정

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
app = Celery("library_outing")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

권장 큐:

- `default`
- `sync_library`
- `sync_program`
- `sync_book`
- `preference`
- `media`

외부 제공처별 rate limit을 큐 또는 task annotation으로 분리한다.

---

## 12. 전국도서관표준데이터 import

### 12.1 첨부 파일 분석 결과

- JSON root: `fields`, `records`
- 필드 수: 28
- 전체 행: 3,554
- 부산광역시 행: 220
- 위도·경도 결측: 전국 기준 149행
- 파일명에 “부산”이 있으나 내용은 전국 데이터이므로 시·도 필터를 명시해야 한다.

### 12.2 import 단계

```text
파일 체크섬 확인
→ SourceSyncRun 생성
→ 각 raw 행 LibrarySourceRecord 저장
→ 형식 검증·정규화
→ 내부 Library 후보 매칭
→ 자동 매칭 또는 검수 큐
→ Library 현재값 upsert
→ OpeningHour·ClosureRule·StatisticSnapshot 반영
→ current 행 전환
→ sync 결과 집계
```

### 12.3 매칭 우선순위

1. 수동으로 확정된 source record 매칭
2. 실제 외부 도서관 코드
3. 정규화 주소 완전일치 + 정규화 이름 유사도
4. 좌표 100m 이내 + 이름 유사도
5. 홈페이지 도메인·전화번호 보조 일치
6. 그 외 `unmatched`

자동 매칭 threshold 예시:

- 이름 유사도 0.92 이상 + 주소 완전일치: auto match
- 이름 0.85 이상 + 좌표 100m 이내: auto match 후보
- 그 미만: 운영자 검수

### 12.4 필드 변환

```python
STANDARD_FIELD_MAP = {
    "도서관명": "name",
    "시도명": "sido",
    "시군구명": "sigungu",
    "도서관유형": "library_type",
    "소재지도로명주소": "road_address",
    "운영기관명": "operating_agency",
    "도서관전화번호": "phone",
    "홈페이지주소": "homepage_url",
    "위도": "latitude",
    "경도": "longitude",
}
```

- 빈 문자열은 `None`
- `0`과 결측을 구분
- URL scheme이 없으면 검증 후 보정
- 전화번호 `000-0000-0000`, `054-000-0000` 등은 품질 플래그
- `대출가능권수`가 자료 수보다 큰 이상치 등은 원문을 남기고 검수 대상

### 12.5 운영시간 변환

- 평일 시간은 월~금 행으로 확장
- 토요일은 토요일 행
- 일요일은 원천에 명시가 없으므로 휴관 원문과 홈페이지 보강 없이 임의 open 처리하지 않음
- 공휴일 `00:00~00:00`은 `closed` 후보지만 휴관 원문과 함께 판정
- 복잡한 휴관 문구는 raw text를 보존하고 파싱 실패 시 `unknown`

---

## 13. 정보나루 세부 활용 기준

### 13.1 서비스에 직접 사용하는 API

| 기능 | 정보나루 API | 주요 제한·의미 |
|---|---|---|
| 참여 도서관 | `libSrch` | 주소·연락처·운영시간·단행본 수 |
| 도서 검색 | `srchBooks` | 여러 검색필드 사용 시 AND, 기본 대출건수 내림차순 |
| 도서 상세 | `srchDtlList` | ISBN, 선택적 최근 90일 대출정보 |
| 도서관별 장서 | `itemSrch` | callNumbers 복수 가능, ISBN 최대 5개 |
| 소장 도서관 | `libSrchByBook` | 광역 지역 코드 필수 |
| 소장·대출가능 | `bookExist` | 대출 가능은 조회 전날 상태 |
| 전국 인기 | `loanItemSrch` | 최대 5,000건 |
| 지역·도서관 인기 | `loanItemSrchByLib` | 최대 200건 |
| 마니아·다독자 | `recommandList` | 입력 ISBN 최대 5개, 결과 최대 200건, 최근 36개월 기반 |
| 급상승 | `hotTrend` | 최근 7일 변화, 기준일 포함 3일, 일별 최대 5건 |
| 신착 | `newArrivalBook` | 도서관 코드 필수, 기준월 |

### 13.2 Phase 2 API

- `keywordList`: 도서별 최대 50개 키워드
- `usageAnalysisList`: 최근 12개월 대출추이, 최근 30일 이용자 그룹, 최근 36개월 함께 대출·추천
- `usageTrend`: 최근 30일 요일·시간대별 상대 비율
- `extends/libSrch`: 도서관 통합 정보와 최신 신착 10권
- `extends/loanItemSrchByLib`: 최근 30일 연령 그룹별 상위 20권
- `monthlyKeywords`, `readQt`: 콘텐츠 확장 시 검토

### 13.3 코드 관리

정보나루의 지역·세부지역·연령·성별·KDC 코드는 코드 파일 또는 DB seed로 관리한다.

```text
region 21 = 부산광역시
age 0 = 영유아
age 6 = 유아
age 8 = 초등
age 14 = 청소년
age 20/30/40/50/60 = 연령대
kdc 0..9 = 대주제
```

프론트에서 원천 코드를 직접 하드코딩하지 않고 metadata API가 내부 표시명과 함께 제공한다.

---

## 14. 쿼리·성능 설계

### 14.1 도서관 목록

- `select_related`로 current statistic을 직접 참조할 수 없다면 `Subquery` 또는 current flag 사용
- 시설·태그는 `Prefetch`
- 후기 평균은 `LibraryReviewAggregate` 물리 테이블 또는 annotation을 선택
- 카드마다 최신 프로그램 count를 개별 쿼리하지 않음

MVP 권장: 야간 배치 또는 signal/task로 다음 denormalized aggregate를 별도 테이블에 유지할 수 있다.

```text
LibrarySearchAggregate
- current_book_count
- current_reading_seat_count
- review_rating
- review_count
- active_program_count_30d
- main_image_id
- refreshed_at
```

이 엔터티는 검색 최적화용 파생 데이터이므로 ERD 핵심 원본으로 간주하지 않는다.

### 14.2 전문검색

1단계:

- `icontains` + trigram index
- 도서관명, 주소, 프로그램명

2단계:

- PostgreSQL `SearchVector`
- 한국어 형태소 품질이 부족하면 OpenSearch 검토

### 14.3 N+1 방지

- `is_saved`는 인증 사용자에 대해 `Exists` annotation
- 리스트 serializer에서 DB 접근 금지
- 도서 소장 도서관 availability는 요청 옵션이 false면 호출·조회하지 않음

### 14.4 페이지 크기

- 일반 목록 기본 20, 최대 100
- 외부 API pageSize는 내부 요청 제한과 다르게 관리
- 인기 목록 화면 노출은 최대 50 권장

---

## 15. 권한·보안·개인정보

### 15.1 권한

- 공개: 도서관·책·프로그램 조회, 공개 후기 조회
- 인증: 저장, 후기 작성, 내 취향
- 본인만: 저장 메모, 후기 수정·삭제
- 운영자: 원천 매칭, 프로그램 노출, 태그·추천 가중치, 이미지 라이선스

### 15.2 현재 위치

- 요청 query/body에서만 사용
- DB 모델에 저장하지 않음
- access log에서 query string 제거 또는 lat/lng 마스킹
- 분석 이벤트에는 exact 좌표 대신 시군구 또는 동의 받은 저정밀 지역만 사용

### 15.3 외부 URL

- 프로그램 신청·홈페이지 링크는 scheme allowlist `http/https`
- SSRF 방지를 위해 서버가 사용자 입력 URL을 임의 fetch하지 않음
- 홈페이지 parser 대상 도메인은 `DataSource` allowlist에 등록

### 15.4 이미지

- MIME magic byte 확인
- EXIF GPS 제거
- 파일당 최대 10MB, 이미지당 장축 최대 정책 적용
- SVG 사용자 업로드 금지
- 악성 파일 검사 hook 준비

### 15.5 후기

- HTML 허용하지 않고 plain text 또는 안전한 Markdown subset
- rate throttle
- 신고·숨김을 위한 moderation status
- 삭제 시 이미지도 storage lifecycle에 따라 처리

---

## 16. Django Admin 요구사항

### Sources

- 수집 실행 성공·실패·건수·오류 확인
- unmatched `LibrarySourceRecord` 검색 및 수동 매칭
- 원천 활성화·우선순위·TTL 관리

### Libraries

- 도서관 기본정보·외부 코드 inline
- 운영시간·휴관·시설·태그 inline
- 대표 이미지 지정
- 최신 스냅샷과 마지막 성공 시각 read-only 표시

### Programs

- 원천별 필터
- lifecycle status, visible, deleted 필터
- 공식 URL 확인
- 중복 후보 검색

### Recommendations

- 목적·태그·metric 가중치 편집
- 샘플 도서관에 대한 점수 preview admin action

### Reviews

- pending/hidden 관리
- 이미지 확인

---

## 17. 테스트 명세

### 17.1 모델·제약

- ISBN 조건부 unique
- 사용자 저장 중복 방지
- rating 범위
- snapshot 음수 좌석 방지
- Program source+external ID unique
- 대표 이미지 1개 제한

### 17.2 normalizer contract test

첨부 매뉴얼과 실제 샘플 응답을 fixture로 저장한다.

- `bookExist`: Y/N, 누락, XML/JSON 변형
- `itemSrch`: callNumbers 0·1·복수
- `srchBooks`: ISBN 없음, 출판년도 비정상
- `recommandList`: 최대 ISBN 수 검증
- `hotTrend`: 날짜별 다중 결과
- 열람실: null 좌석, 방 ID 중복, source timestamp 누락
- 프로그램: 신청기간 누락, 반복 일정, 취소 상태

CI에서는 live API를 호출하지 않는다.

### 17.3 서비스 테스트

- 열람실 snapshot 59분이면 API 미호출
- 61분이면 API 호출
- API 실패 + 과거 snapshot이면 stale 반환
- API 실패 + snapshot 없음이면 503
- 동시 요청에서 외부 호출 1회
- `bookExist` 응답의 effective date가 전날로 저장
- negative holding 결과가 기존 holding을 즉시 삭제하지 않음
- 목록 snapshot과 item transaction rollback

### 17.4 추천 테스트

- 동일 입력은 동일 순위
- 실시간 좌석 snapshot 변경이 홈 추천 결과에 영향 없음
- 좌표가 없을 때 nearby 목적의 fallback 처리
- 결측 통계가 높은 점수로 오인되지 않음
- 필수 시설 미충족 후보 제외
- 추천 이유가 실제 기여 rule과 일치

### 17.5 API 테스트

- 필터 조합
- pagination 상한
- 인증·소유권
- lat/lng validation
- 외부 오류 코드 변환
- API key 미노출
- OpenAPI schema snapshot

### 17.6 데이터 품질 테스트

- 첨부 JSON 3,554건 파싱
- 부산 필터 220건 확인
- 빈 좌표 허용
- `휴관중` 파싱
- 구 행정명칭 alias
- 00:00 처리
- 제공기관코드를 도서관 external ID로 사용하지 않음

---

## 18. 로깅·모니터링

구조화 로그 필드:

```json
{
  "event": "external_api_call",
  "provider": "data4library",
  "operation": "bookExist",
  "status_code": 200,
  "duration_ms": 324,
  "cache_hit": false,
  "request_id": "..."
}
```

로그 금지:

- 인증키
- 사용자 비밀번호·token
- 정확한 현재 위치
- 후기 이미지 원본 binary

지표:

- 외부 API 성공률·p95 latency
- cache hit rate
- stale fallback 수
- provider별 마지막 성공 동기화 시각
- unmatched library 수
- 프로그램 visible/soft-deleted 수
- 추천 endpoint p95

알림:

- 프로그램 provider 2회 연속 실패
- 표준데이터 import partial/failed
- 열람실 API 오류율 20% 초과
- 정보나루 rate limit 증가
- 최근 24시간 featured book snapshot 없음

---

## 19. 배포 구성

최소 구성:

```text
Nginx/Load Balancer
  → Django ASGI/WSGI app
  → PostgreSQL
  → Redis
  → Celery worker
  → Celery beat
  → Object Storage
```

개발환경은 Docker Compose를 권장한다.

서비스 분리 우선순위:

1. 단일 Django deployment + 별도 Celery worker
2. 수집량 증가 시 provider별 worker queue 분리
3. 전국 확장 후 검색·추천 read replica 또는 검색엔진 검토

`python manage.py check --deploy`, migration dry-run, static/media 접근정책을 배포 체크리스트에 포함한다.

---

## 20. 구현 단계

### Phase 0: 기반

- Django 프로젝트, User 모델, PostgreSQL, Redis, Celery
- 공통 응답·예외·OpenAPI
- DataSource seed

### Phase 1: 도서관

- 표준데이터 importer
- Library·운영시간·통계·시설
- 도서관 목록·상세
- 관리자 매칭 화면

### Phase 2: 추천

- Purpose·rule seed
- Haversine
- 홈 추천·추천 사유
- 사용자 기본 지역

### Phase 3: 책

- Data4LibraryClient
- 도서 검색·상세·Book upsert
- 소장 도서관·대출 가능 cache
- 인기·추천 목록 snapshot

### Phase 4: 프로그램

- provider interface
- 동래구·부산진구 등 1~2개 provider 우선
- Program DB 검색·soft delete
- 공식 신청 링크

### Phase 5: 상세 열람실

- 공공데이터포털 활용신청·Swagger 확정
- external ID 매칭
- 1시간 cache·stale fallback
- 상세 endpoint

### Phase 6: 나의 나들이

- 저장·후기·이미지
- UserPreference 집계
- 선택적 AI 요약

### Phase 7: 운영 보강

- 모니터링·rate limit·데이터 품질 리포트
- 공식 이미지·공공누리
- 전국 확장 준비

---

## 21. MVP 완료 조건

### 홈

- 6개 목적 중 하나를 선택하면 DB 기반 추천을 반환한다.
- 좌표가 있으면 거리와 추천 사유를 제공한다.
- 열람실 실시간 API가 중단되어도 홈이 정상 동작한다.

### 도서관 찾기

- 부산 지역·유형·운영·시설·통계 필터가 DB에서 동작한다.
- 거리순은 좌표 보유 행에 대해 계산된다.
- 상세에서 운영시간·통계 기준일·시설·이미지 출처가 표시된다.

### 열람실

- 상세 최초 조회 시 외부 호출 후 snapshot을 저장한다.
- 1시간 안 재조회는 외부 호출 없이 반환한다.
- 장애 시 과거 성공 결과를 stale로 표시한다.

### 책

- 제목·저자·ISBN 검색이 가능하다.
- 검색된 책은 Book에 upsert된다.
- 소장 도서관과 대출 가능 여부가 분리되어 표시된다.
- 대출 가능 여부에 전일 기준일이 노출된다.
- 인기·마니아·다독자·급상승·신착 목록이 snapshot에서 조회된다.

### 프로그램

- 내부 DB에서 지역·도서관·분류·대상·기간·신청상태 필터가 가능하다.
- 원천에서 사라진 프로그램은 FK를 깨지 않고 soft delete된다.
- 신청은 공식 링크로 이동한다.

### 나의 나들이

- 도서관·책·프로그램 저장과 해제가 가능하다.
- 후기와 이미지 작성·수정·삭제가 가능하다.
- 사용자 취향 집계가 재계산되고 추천 보너스에 제한적으로 반영된다.

### 데이터 운영

- 모든 외부 코드에 원천이 연결된다.
- 수집 실행 성공·실패와 반영 건수를 확인할 수 있다.
- API 키와 현재 좌표가 로그·응답에 노출되지 않는다.

---

## 22. 구현 시 확인이 필요한 항목

1. 열람실 API 활용신청 후 Swagger operation ID와 실제 필드명
2. 부산 각 프로그램 제공처의 인증 방식·호출 한도·수정일 필드
3. 정보나루 운영키의 실제 트래픽 한도
4. 표준데이터의 부산 대상 범위를 공공·작은·어린이 중 어디까지 노출할지
5. 도서관 홈페이지 크롤링 허용 여부와 robots/이용약관
6. 공공누리 이미지의 자체 저장·리사이즈 가능 범위
7. 사용자 후기 1인 1도서관 1건 제한 여부
8. JWT 방식과 same-origin session 방식 중 최종 프론트 구조

위 항목은 임의 값으로 구현하지 않고 발급 문서·운영정책 확인 후 환경설정 또는 admin 기준정보로 확정한다.

---

## 23. 참고 문서

- Django 다운로드·지원 버전: https://www.djangoproject.com/download/
- Django 5.2 문서: https://docs.djangoproject.com/en/5.2/
- Django REST Framework: https://www.django-rest-framework.org/
- Celery Django 연동: https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
- 전국도서관표준데이터: https://www.data.go.kr/data/15013109/standard.do
- 공공도서관 열람실 현황 실시간 정보: https://www.data.go.kr/data/15142580/openapi.do
- 정보나루 Open API: https://www.data4library.kr/apiUtilization
- 공공누리 이용조건: https://www.kogl.or.kr/info/freeUse.do
- 부산광역시 Big-데이터웨이브: https://data.busan.go.kr/

