# 도서관 나들이 Frontend 개발 명세서 v2.1

- 문서 버전: 2.1
- 작성 기준일: 2026-06-24
- 대상 애플리케이션: Vue 3 SPA
- 연동 백엔드: Django REST API `/api/v1`
- 1차 서비스 범위: 부산광역시 MVP
- 문서 상태: 백엔드 실구현 API 계약 동기화 기준안 + 이메일 인증 계약 정정판
- 변경 성격: v1.3 UI/UX·Kakao 지도 원칙 유지 + 실제 API Endpoint·Method·DTO·현재 구현 범위 전면 동기화
- 최상위 구현 기준: `도서관 나들이 프론트 전달용 API 계약 문서 v1.1`
- 도메인 참고: `library_outing_Django_spec_v3.md`, `library_outing_ERD_v3.md`
- 디자인 참고: 대화에서 제공된 홈·도서관·책·프로그램·커뮤니티·나의 나들이·도서관 상세 시안

## 0. 문서 사용 규칙

### 0.1 목적

이 문서는 도서관 나들이 서비스의 Vue 프론트엔드를 실제 Django API에 연결하기 위한 구현 기준이다. 화면, Route, API Service, Pinia Store, DTO, 사용자 상호작용, 반응형·접근성·테스트 범위를 함께 정의한다.

프론트 구현자는 이 문서를 통해 다음을 결정할 수 있어야 한다.

1. 어떤 URL에 어떤 화면을 배치하는가.
2. 회원과 비회원에게 무엇을 보여주고 어떤 행동을 허용하는가.
3. 각 화면이 어떤 실제 API를 어떤 Method로 호출하는가.
4. 백엔드 응답을 어떤 DTO와 화면 상태로 해석하는가.
5. 로딩·빈 상태·오류·권한·위치 권한을 어떻게 처리하는가.
6. 저장·좋아요·후기·선호 변경 후 어떤 Store와 목록을 갱신하는가.
7. 현재 백엔드에 없는 기능을 UI에서 어떻게 보류하는가.

### 0.2 문서 우선순위

문서 간 내용이 충돌할 때 다음 순서로 판단한다.

1. **실제 Endpoint, HTTP Method, Request·Response, 현재 구현 여부**: `도서관 나들이 프론트 전달용 API 계약 문서 v1.1`
2. **도메인 의미, 권한 정책, 장기 설계 방향**: `library_outing_Django_spec_v3.md`
3. **모델 관계와 null 의미**: `library_outing_ERD_v3.md`
4. **화면·상호작용·반응형·접근성**: 본 Frontend 명세서
5. **초기 아이디어와 시각적 참고**: 페이지 구조 문서와 첨부 디자인 시안

API 계약에 없는 Endpoint, 필드, 상태값은 프론트가 임의로 생성하지 않는다. 기존 Django 설계에는 있으나 프론트 전달용 API 계약에서 현재 보류된 기능은 v2.1의 MUST 범위에서 제외한다.

### 0.3 백엔드 계약 보존 원칙

- Frontend v2.0은 백엔드 API에 맞춰 화면을 조정하며 새 백엔드 기능을 전제로 하지 않는다.
- UI 카드에서 일부 응답 필드만 보여주는 것은 프론트 표시 규칙이지 API 변경 요구가 아니다.
- 응답에 없는 `is_saved`, `is_liked`, 운영 상태, 추천 점수, 후기 공개 상태를 추론하지 않는다.
- 지원되지 않는 Query를 URL이나 요청에 보내지 않는다.
- `null`, `false`, 빈 배열, 데이터 행 부재를 같은 의미로 합치지 않는다.
- 내부 프로그램 신청, 실시간 좌석, 후기 이미지 업로드, 통합 성향 대시보드처럼 현재 보류된 기능을 UI에서 활성 기능처럼 노출하지 않는다.
- API 계약 공백은 27장의 `TBD`로 관리하고, 임시 구현은 별도 합의 없이 확정 기능으로 문서화하지 않는다.

### 0.4 요구 수준 표기

| 표기 | 의미 |
|---|---|
| MUST | v2.0 완료를 위해 반드시 구현 |
| SHOULD | 구현 권장. 일정상 제외 시 이슈 기록 |
| MAY | 선택 구현 또는 후속 개선 |
| DEFERRED | 현재 API 계약에서 의도적으로 보류 |
| TBD | 계약 확인이 필요한 항목 |

### 0.5 화면 명세 공통 형식

각 화면은 다음 항목을 기준으로 구현한다.

- 화면 ID와 Route
- 접근 권한과 Router Guard
- 사용 Endpoint·Method·Query
- 요청·응답 DTO
- 레이아웃과 구성 요소
- 사용자 행동과 성공 후 이동
- 회원·비회원 분기
- 로딩·빈 상태·오류 상태
- 반응형·접근성 기준
- 완료 조건

### 0.6 v2.1 핵심 변경 요약

| 영역 | v1.3 | v2.0 |
|---|---|---|
| 인증 식별자 | 이메일 중심 | 이메일 중심으로 확정 |
| Refresh | `/auth/refresh/` 가정 | `/auth/token/refresh/` 확정 |
| 사용자 정보 | `/profile/` 가정 | `/users/me/` 확정 |
| 홈 | 추천 API 분리 가정 | `GET /home/` 단일 응답 |
| 도서관 필터 | 목적·시설·운영·거리 포함 | `q`, `sigungu`, `library_type`만 활성 |
| 운영 상태 | 카드·상세 표시 | 정밀 운영표 보류로 활성 UI에서 제거 |
| 인기 도서 | 주간 인기 섹션 | Endpoint 없음. 제거 |
| 책 저장 ID | 내부 Book ID | ISBN13 |
| 후기 작성 | multipart + 이미지 | JSON, 이미지 업로드 보류 |
| 후기 좋아요 | PUT·DELETE | POST·DELETE |
| 선호 Payload | ID 배열 | code 배열 + 지역 객체 |
| 나의 나들이 | 분석 Dashboard | 다섯 개 목록 Container |
| 프로필 | 이미지·소개 포함 | email·nickname 중심 |
| 숨김 후기 UI | 조건부 설계 | 상태 계약 부재로 보류 |
| 인증 요청 필드 | 일부 초안에서 username 사용 | 실제 백엔드에 맞춰 email 사용 |

## 1. 프로젝트 개요

### 1.1 서비스 정의

도서관 나들이는 부산 지역 도서관, 책, 문화 프로그램과 이용 후기를 한곳에서 탐색하고 관심 항목을 저장할 수 있는 서비스다. 현재 백엔드가 제공하는 규칙 기반 홈 추천과 직접 선호 설정을 활용하며, 행동 기반 통합 분석은 후속 범위로 둔다.

현재 핵심 사용 흐름은 다음과 같다.

```text
홈에서 추천 도서관을 발견한다
→ 도서관·책·프로그램·후기를 탐색한다
→ 상세 정보와 위치를 확인한다
→ 관심 도서관·책·프로그램을 저장한다
→ 후기를 작성하거나 좋아요한다
→ 나의 나들이 목록에서 다시 확인한다
→ 직접 선호 목적·지역·시설을 설정한다
```

### 1.2 v2.0 활성 기능

1. JWT 회원가입·로그인·자동 Access 갱신·로그아웃
2. 규칙 기반 홈 오늘 추천·테마 추천·조건부 개인 추천
3. 도서관 기본 검색·구군·유형 필터·목록·상세
4. 도서관 상세의 통계·확인된 시설·Kakao 지도
5. 정보나루 책 검색·책 상세·부산 소장 도서관 조회
6. 문화 프로그램 목록·상세·원문·도서관 연결
7. 도서관·책·프로그램 저장·저장 해제
8. 후기 목록·상세·JSON 작성·수정·삭제·좋아요
9. 선호 목적·지역·시설 태그 전체 교체 저장
10. 나의 나들이의 저장 도서관·책·프로그램·내 후기·좋아요 후기 목록
11. email·nickname 조회와 nickname 수정
12. 이미지 출처·fallback 표시, 반응형·접근성·상태 UX

### 1.3 v2.0 보류 범위

다음은 화면에서 활성 기능으로 제공하지 않는다.

- 도서관 `open_today`, `open_now` 정밀 판정과 관련 필터
- 목적·시설·좌석·장서·공휴일·거리 기반 도서관 검색 필터
- 주간 인기 도서
- 비슷한 도서관
- 행동 기반 개인화 추천 계산과 사용자 취향 요약 문장
- 나의 나들이 통합 분석 Dashboard와 4축 성향
- 후기 이미지 업로드·수정·삭제
- 프로필 이미지·자기소개
- 프론트 후기 숨김 상태 표시와 관리자 기능
- 서비스 내부 프로그램 신청·예약·결제
- 실시간 열람실 좌석·실시간 대출 가능 여부
- GMS/AI 문구 생성과 AI 결정 추천 순위
- 도서관 찾기 지도 중심 모드
- 무한 스크롤

### 1.4 현재 데이터 상태를 고려한 UX

| 데이터 | 예상 상태 | 프론트 처리 |
|---|---|---|
| 도서관 | 존재 | 정상 목록·상세 |
| 도서관 시설 | 일부 존재 | `true`만 표시, profile 부재 안내 가능 |
| 도서관 이미지 | 일부 존재 | `thumbnail.is_fallback` 처리 |
| 운영표 | 현재 0건 가능 | 정밀 운영 상태 UI 미노출 |
| 프로그램 | import 전 0건 가능 | 오류가 아닌 빈 상태 |
| 책 | 정보나루 검색 중심 | 외부 API 오류·503 분리 |
| 소장 도서관 내부 매칭 | `matched=false` 다수 가능 | 외부 도서관 카드로 표시 |
| 후기 | 초기 0건 가능 | 첫 후기 작성 CTA |
| LibraryTag | 현재 0건 가능 | 태그 기반 도서관 UI 미사용 |

## 2. 사용자와 권한

### 2.1 사용자 유형

| 사용자 | 설명 |
|---|---|
| 비회원 | 공개 콘텐츠를 탐색하는 사용자 |
| 신규 회원 | 가입했으나 선호·저장·후기 데이터가 적은 사용자 |
| 기존 회원 | 저장, 후기, 좋아요 또는 직접 선호가 있는 사용자 |
| 후기 작성자 | 자신이 작성한 후기의 수정·삭제 권한을 가진 회원 |
| 관리자 | Django admin에서 데이터를 관리하는 운영자. 별도 SPA 관리자 UI 없음 |

### 2.2 기능 권한표

| 기능 | 비회원 | 회원 | 추가 조건 |
|---|---:|---:|---|
| 홈·도서관·책·프로그램·후기 조회 | 가능 | 가능 | 공개 API |
| 홈 nearby 요청 | 위치 동의 시 | 위치 동의 시 | 좌표를 `/home/` 요청에만 사용 |
| 도서관·책·프로그램 저장 | 로그인 유도 | 가능 | POST·DELETE 멱등 Endpoint |
| 후기 좋아요 | 로그인 유도 | 가능 | POST·DELETE |
| 후기 작성 | Route 접근 차단 | 가능 | 태그 1~5개 필요 |
| 후기 수정·삭제 | Route 접근 차단 | 본인만 | 서버 403이 최종 기준 |
| 선호 설정 | Route 접근 차단 | 가능 | PUT 전체 교체 |
| 나의 나들이 | Route 접근 차단 | 가능 | 다섯 목록만 제공 |
| 프로필 조회·nickname 수정 | Route 접근 차단 | 가능 | `/users/me/` |
| 후기 숨김 관리 | 불가 | 불가 | Django admin에서만 수행 |

### 2.3 행동 게이트와 Route 게이트

#### 공개 화면의 로그인 필요 행동

비회원이 저장 또는 좋아요를 누르면 현재 맥락을 유지한 채 로그인으로 전환한다.

```text
저장·좋아요 클릭
→ LoginRequiredDialog
→ PendingIntent 저장
→ /auth/login?redirect={현재 내부 경로}
→ 로그인 성공
→ redirect 대상 복귀
→ interaction 상태 확인
→ 목표 상태가 아니면 POST 1회 자동 실행
```

자동 재실행 대상:

- 도서관 저장
- 책 저장
- 프로그램 저장
- 후기 좋아요

#### 인증 전 mount를 차단하는 Route

- `/reviews/new`
- `/reviews/:id/edit`
- `/my-outings/**`
- `/profile/**`
- `/onboarding/preferences`

비회원은 Router Guard 단계에서 로그인으로 이동하며, 해당 페이지 API를 먼저 호출하지 않는다.

### 2.4 후기 작성자 권한

후기 응답에는 별도 `can_edit`, `can_delete`가 없으므로 화면상 작성자 여부는 다음 비교로 계산한다.

```js
review.user.id === authStore.user?.id
```

이 비교는 메뉴 노출을 위한 편의 판단일 뿐 최종 권한 검증은 아니다. 수정·삭제 요청에서 서버가 `403`을 반환하면 권한 없음 화면 또는 안내를 표시한다.

후기 응답에 `moderation_status`가 없으므로 v2.0은 hidden·pending Badge나 읽기 전용 분기를 구현하지 않는다.

### 2.5 저장·좋아요 초기 상태

도서관·책·프로그램·후기 응답에는 `is_saved`, `is_liked`가 없다. 로그인 회원은 `interactionStore`가 나의 나들이 목록을 읽어 다음 Set을 구성한다.

```text
savedLibraryIds
savedBookIsbns
savedProgramIds
likedReviewIds
```

초기 hydration 전 상태는 `false`가 아니라 `unknown`이다. 버튼은 상태 확인 중임을 표시하고, 응답을 받기 전 “저장 안 됨” 또는 “좋아요 안 함”으로 단정하지 않는다.

## 3. 정보 구조와 내비게이션

### 3.1 최상위 정보 구조

```text
도서관 나들이
├─ 홈
├─ 도서관 찾기
│  └─ 도서관 상세
├─ 책 둘러보기
│  └─ 책 상세·소장 도서관
├─ 문화 프로그램
│  └─ 프로그램 상세
├─ 커뮤니티
│  ├─ 후기 상세
│  ├─ 후기 작성
│  └─ 후기 수정
├─ 나의 나들이 — 회원
│  ├─ 저장한 도서관
│  ├─ 저장한 책
│  ├─ 저장한 프로그램
│  ├─ 좋아요한 후기
│  └─ 내가 쓴 후기
└─ 프로필 — 회원
   ├─ 내 정보
   ├─ 닉네임 수정
   └─ 선호 설정
```

`/my-outings`는 분석 Dashboard가 아니라 회원 목록 영역의 진입점이며 `/my-outings/libraries`로 redirect한다.

### 3.2 데스크톱 헤더

공통 메뉴:

- 홈
- 도서관 찾기
- 책 둘러보기
- 문화 프로그램
- 커뮤니티

비회원 우측:

- 로그인
- 회원가입

회원 우측 프로필 메뉴:

- 나의 나들이
- 내 프로필
- 선호 설정
- 로그아웃

현재 메뉴는 녹색 underline과 `aria-current="page"`로 표시한다.

### 3.3 모바일 내비게이션

하단 탭은 다섯 개로 고정한다.

1. 홈
2. 도서관
3. 책
4. 프로그램
5. 커뮤니티

나의 나들이와 프로필은 Header의 프로필 메뉴 또는 Drawer에서 제공한다. 후기 작성·수정처럼 집중 Form 화면에서는 하단 탭을 숨길 수 있다.

### 3.4 카드 이동 원칙

| 클릭 영역 | 결과 |
|---|---|
| 카드 주 링크·제목 | 해당 콘텐츠 상세 |
| 저장 버튼 | 저장 상태 변경 또는 로그인 유도 |
| 후기 좋아요 | 좋아요 상태 변경 또는 로그인 유도 |
| 프로그램·후기의 도서관명 | 도서관 상세 |
| 프로그램 원문 | 새 탭 외부 사이트 |
| `matched=false` 소장 도서관 | 내부 상세 이동 없음 |

카드 전체를 `div @click`으로 만들고 내부에 버튼을 중첩하지 않는다. 주 링크와 액션 버튼을 분리하고 `@click.stop`은 보조 방어로만 사용한다.

### 3.5 뒤로 가기와 상태 복원

- 목록의 검색·필터·페이지는 URL Query가 원본이다.
- 상세에서 뒤로 가면 Query, 페이지, Scroll 위치를 복원한다.
- 현재 위치의 정확한 위도·경도는 URL에 기록하지 않는다.
- 외부 책 검색은 `search_type`, `q`, `page`, `page_size`를 URL에 기록한다.

## 4. 기술 스택과 구현 구조

### 4.1 기본 기술 스택

| 영역 | 선택 |
|---|---|
| UI Framework | Vue 3 |
| 작성 방식 | Composition API, `<script setup>` |
| Build Tool | Vite |
| Router | Vue Router 4 |
| State | Pinia |
| HTTP | Axios |
| 인증 | JWT Access Token + HttpOnly Refresh Cookie |
| 지도 | Kakao Map JavaScript SDK |
| CSS | Bootstrap 5.3 + CSS Custom Properties + scoped CSS |
| 언어 | JavaScript ES2022 |
| 타입 문서 | TypeScript 형태 DTO 또는 JSDoc |
| Unit | Vitest |
| Component | Vue Test Utils |
| API Mock | MSW 권장 |
| E2E | Playwright 권장 |

### 4.2 Vue 구현 원칙

- Options API와 Composition API를 혼용하지 않는다.
- View는 Route 단위 데이터 조합을 담당하고 재사용 UI는 Component로 분리한다.
- View에서 Axios를 직접 호출하지 않고 Service 또는 Store Action을 거친다.
- 정보나루·공공데이터·GMS는 Django API를 통해서만 사용한다.
- Vue가 직접 호출하는 외부 서비스는 Kakao Map JavaScript SDK로 제한한다.
- 응답 표시값은 서버 필드 또는 명시된 formatter만 사용하고 새 사실을 생성하지 않는다.
- 원격 HTML을 `v-html`로 렌더링하지 않는다.
- 배열 index를 key로 사용하지 않는다.

### 4.3 권장 디렉터리 구조

```text
src/
├─ app/
│  ├─ App.vue
│  ├─ router.js
│  └─ bootstrap.js
├─ assets/styles/
│  ├─ tokens.css
│  ├─ base.css
│  └─ bootstrap-overrides.css
├─ components/
│  ├─ layout/
│  ├─ cards/
│  ├─ actions/
│  ├─ filters/
│  ├─ feedback/
│  ├─ forms/
│  └─ media/
├─ composables/
│  ├─ useAuthGate.js
│  ├─ useAsyncState.js
│  ├─ useGeolocation.js
│  ├─ useListQuery.js
│  └─ useOptimisticToggle.js
├─ constants/
│  ├─ routes.js
│  ├─ programStatus.js
│  └─ storageKeys.js
├─ layouts/
│  ├─ DefaultLayout.vue
│  ├─ AuthLayout.vue
│  └─ MemberLayout.vue
├─ pages/
│  ├─ auth/
│  ├─ home/
│  ├─ libraries/
│  ├─ books/
│  ├─ programs/
│  ├─ community/
│  ├─ my-outings/
│  ├─ profile/
│  └─ system/
├─ services/
│  ├─ apiClient.js
│  ├─ authService.js
│  ├─ accountService.js
│  ├─ kakaoMapLoader.js
│  ├─ preferenceService.js
│  ├─ homeService.js
│  ├─ libraryService.js
│  ├─ bookService.js
│  ├─ programService.js
│  ├─ reviewService.js
│  └─ myOutingsService.js
├─ stores/
│  ├─ auth.js
│  ├─ reference.js
│  ├─ home.js
│  ├─ libraries.js
│  ├─ books.js
│  ├─ programs.js
│  ├─ community.js
│  ├─ myOutings.js
│  ├─ interactions.js
│  └─ ui.js
└─ utils/
   ├─ apiError.js
   ├─ dateTime.js
   ├─ format.js
   ├─ kakaoMap.js
   ├─ query.js
   ├─ statusLabel.js
   └─ validators.js
```

### 4.4 이름 규칙

| 대상 | 규칙 | 예시 |
|---|---|---|
| Vue Component | PascalCase | `LibraryCard.vue` |
| Composable | `use` + PascalCase | `useGeolocation.js` |
| Store export | `useXxxStore` | `useInteractionStore` |
| Service 함수 | 동사 + 자원 | `fetchLibraryDetail` |
| Route name | kebab-case | `library-detail` |
| CSS class | kebab-case | `.library-card__meta` |
| 상수 | UPPER_SNAKE_CASE | `MAX_REVIEW_TAGS` |

## 5. 환경변수와 API Client

### 5.1 Vue 환경변수

```dotenv
# frontend/.env
VITE_API_BASE_URL=/api/v1
VITE_APP_NAME=도서관 나들이
VITE_REQUEST_TIMEOUT_MS=15000
VITE_USE_MOCK_API=false
VITE_KAKAO_MAP_JAVASCRIPT_KEY=발급받은_JavaScript_Key
```

저장소에는 값이 비어 있는 `.env.example`만 포함한다.

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_APP_NAME=도서관 나들이
VITE_REQUEST_TIMEOUT_MS=15000
VITE_USE_MOCK_API=false
VITE_KAKAO_MAP_JAVASCRIPT_KEY=
```

- `.env`는 Git에서 제외한다.
- `.env` 변경 후 Vite dev server를 재시작한다.
- Kakao 변수에는 JavaScript Key만 넣는다.
- 정보나루·GMS·공공데이터·Django Secret·JWT Refresh Token은 Vue 환경변수에 두지 않는다.

### 5.2 Axios 인스턴스

```js
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS ?? 15000),
  withCredentials: true,
  headers: { Accept: 'application/json' },
})
```

요청 Interceptor:

- `authStore.accessToken`이 있으면 `Authorization: Bearer <token>`을 추가한다.
- Refresh Token은 HttpOnly Cookie이므로 JavaScript에서 읽지 않는다.
- JSON 요청은 기본 Axios 직렬화를 사용한다.
- v2.0 후기 작성·수정에는 `FormData`를 사용하지 않는다.
- 로그인·Refresh·로그아웃에도 `withCredentials=true`를 유지한다.

### 5.3 JWT 갱신과 401 처리

실제 Endpoint:

```text
POST /auth/signup/
POST /auth/login/
POST /auth/token/refresh/
POST /auth/logout/
GET  /users/me/
PATCH /users/me/
```

Access Token은 Pinia 메모리에만 저장하고 Refresh Token은 HttpOnly Cookie로 관리한다.

```text
보호 API 401
→ login·refresh·logout 요청인지 확인
→ 이미 재시도한 요청인지 확인
→ 전역 Refresh Promise 생성 또는 기존 Promise 대기
→ POST /auth/token/refresh/
→ 성공: access 저장, 원 요청 1회 재시도
→ 실패: 사용자 전용 요청 취소
         + 모든 Pinia Store 초기화
         + 개인 sessionStorage 제거
         + 안전한 redirect 보존
         + 로그인 이동
```

필수 규칙:

- Refresh는 single-flight로 한 번만 수행한다.
- 원 요청에 `_retry`를 기록해 무한 반복을 막는다.
- Refresh Endpoint의 401은 다시 Refresh하지 않는다.
- 로그아웃 이후 늦게 도착한 Refresh 응답이 인증을 복원하지 않도록 generation 값을 확인한다.

### 5.4 앱 시작 인증 복원

```text
앱 시작
→ POST /auth/token/refresh/
→ 성공 시 access token 저장
→ GET /users/me/
→ authStore.user 저장
→ initialized=true
```

Refresh가 실패하면 비회원으로 초기화하되 공개 화면을 오류로 막지 않는다. 보호 Route 판단은 초기화가 끝난 뒤 수행한다.

### 5.5 공통 API 오류 정규화

```ts
interface NormalizedApiError {
  status: number | null
  code: string
  detail: string
  fields: Record<string, string[]>
  isNetworkError: boolean
  isCanceled: boolean
}
```

오류 형태:

- `401`, `403`, `404`, `503`: `{ detail: string }`
- `400`: 필드별 문자열 배열 가능
- `204`: body 없음

필드 오류는 Form field 아래에 연결하고, 그 외 오류는 화면 `ErrorState` 또는 Toast로 표시한다.

### 5.6 Kakao Map JavaScript SDK

Kakao 지도는 도서관 상세 페이지에서만 MUST로 사용한다.

사용 필드:

- `library.id`
- `library.name`
- `library.road_address`
- `library.latitude`
- `library.longitude`

동적 SDK URL:

```text
//dapi.kakao.com/v2/maps/sdk.js
  ?appkey=${VITE_KAKAO_MAP_JAVASCRIPT_KEY}
  &autoload=false
```

주요 객체:

- `kakao.maps.Map`
- `kakao.maps.LatLng` — 입력 순서 위도, 경도
- `kakao.maps.Marker`
- `kakao.maps.InfoWindow`

길찾기 URL:

```text
https://map.kakao.com/link/to/[URL 인코딩 도서관명],[위도],[경도]
```

Loader 규칙:

1. `window.kakao?.maps`가 준비되면 즉시 resolve한다.
2. 동시 호출은 같은 Promise를 사용한다.
3. 동일 script를 중복 삽입하지 않는다.
4. Key·좌표가 없으면 SDK를 호출하지 않는다.
5. 실패 시 지도 영역만 fallback으로 전환한다.
6. 주소와 외부 길찾기 링크는 가능한 경우 유지한다.

개발 허용 도메인에 `http://localhost:5173`, 배포 시 실제 origin을 등록한다.

### 5.7 요청 취소와 중복 방지

- 검색·필터 변경 시 이전 GET을 `AbortController`로 취소한다.
- 같은 상세 ID의 동시 요청은 deduplicate한다.
- 취소된 요청은 사용자 오류로 표시하지 않는다.
- 후기 상세는 조회수 증가 가능성이 있으므로 hover prefetch하지 않는다.

## 6. 라우팅 명세

### 6.1 Route 목록

| Name | Path | View | 접근 |
|---|---|---|---|
| `home` | `/` | `HomeView` | 공개 |
| `libraries` | `/libraries` | `LibraryListView` | 공개 |
| `library-detail` | `/libraries/:id` | `LibraryDetailView` | 공개 |
| `books` | `/books` | `BookExploreView` | 공개 |
| `book-detail` | `/books/:isbn13` | `BookDetailView` | 공개 |
| `programs` | `/programs` | `ProgramListView` | 공개 |
| `program-detail` | `/programs/:id` | `ProgramDetailView` | 공개 |
| `community` | `/community` | `ReviewListView` | 공개 |
| `review-detail` | `/reviews/:id` | `ReviewDetailView` | 공개 |
| `review-create` | `/reviews/new` | `ReviewCreateView` | 회원 |
| `review-edit` | `/reviews/:id/edit` | `ReviewEditView` | 회원·작성자 |
| `login` | `/auth/login` | `LoginView` | 비회원 권장 |
| `signup` | `/auth/signup` | `SignupView` | 비회원 권장 |
| `onboarding-preferences` | `/onboarding/preferences` | `PreferenceOnboardingView` | 회원 |
| `my-outings-root` | `/my-outings` | Redirect | 회원 |
| `my-outings-libraries` | `/my-outings/libraries` | `SavedLibrariesView` | 회원 |
| `my-outings-books` | `/my-outings/books` | `SavedBooksView` | 회원 |
| `my-outings-programs` | `/my-outings/programs` | `SavedProgramsView` | 회원 |
| `my-outings-liked-reviews` | `/my-outings/liked-reviews` | `LikedReviewsView` | 회원 |
| `my-outings-reviews` | `/my-outings/reviews` | `MyReviewsView` | 회원 |
| `profile` | `/profile` | `ProfileView` | 회원 |
| `profile-edit` | `/profile/edit` | `ProfileEditView` | 회원 |
| `profile-preferences` | `/profile/preferences` | `PreferenceSettingsView` | 회원 |
| `forbidden` | `/403` | `ForbiddenView` | 공개 |
| `server-error` | `/error` | `ServiceErrorView` | 공개 |
| `not-found` | `/:pathMatch(.*)*` | `NotFoundView` | 공개 |

`/my-outings`는 `/my-outings/libraries`로 redirect한다.

### 6.2 Route Meta

```js
meta: {
  requiresAuth: true,
  guestOnly: false,
  requiresAuthor: false,
  layout: 'member',
  preserveRedirect: true,
  title: '저장한 도서관',
}
```

### 6.3 Router Guard

```text
인증 초기화 대기
→ requiresAuth && 비로그인
   → /auth/login?redirect={to.fullPath}
→ guestOnly && 로그인
   → 안전한 redirect 또는 /
→ requiresAuthor Route는 상세 조회 후 user.id 비교
   → 다르면 /403
```

- Redirect는 내부 경로만 허용한다.
- 후기 수정과 선호 설정은 로그인 후 화면에 복귀하지만 자동 제출하지 않는다.
- 보호 Route는 비회원 상태에서 API를 먼저 호출하지 않는다.

### 6.4 Query 규칙

- 기본값은 URL에서 생략한다.
- 빈 문자열, `undefined`, `null`은 제거한다.
- 필터·검색·정렬 변경 시 `page=1`로 초기화한다.
- 실제 API가 다중 값을 명시하지 않은 `sigungu`, `library_type`, 프로그램 필터는 v2.0에서 단일 값으로 보낸다.
- 현재 위치 좌표는 URL에 기록하지 않는다.
- 검색 입력 중 자동 반영은 `router.replace`, 명시적 이동은 `router.push`를 사용한다.

예시:

```text
/libraries?q=시민&sigungu=부산진구&library_type=public&page=2
/books?search_type=title&q=밝은밤&page=1
/programs?sigungu=해운대구&category=lecture&page=1
/community?ordering=-like_count&page=1
```

### 6.5 Scroll 동작

- 새 상세 Route는 상단으로 이동한다.
- 브라우저 뒤로 가기는 저장된 Scroll 위치를 복원한다.
- 같은 목록에서 Query가 바뀌면 결과 제목으로 Focus와 Scroll을 이동한다.

## 7. 상태 관리 명세

### 7.1 상태 관리 원칙

- 목록 검색 상태는 Router Query가 원본이다.
- 서버 응답이 데이터 원본이며 Store는 캐시와 화면 조합을 담당한다.
- Access Token은 메모리에만 유지한다.
- 정확한 위치 좌표는 메모리에만 유지한다.
- 저장·좋아요 상태는 `interactionStore`가 나의 나들이 목록에서 hydrate한다.
- 모달·Toast·Drawer는 `uiStore`가 관리한다.
- 후기 초안은 텍스트·코드·ID만 `sessionStorage`에 보관할 수 있다.

### 7.2 Store 목록

#### `authStore`

```text
state
- user: UserDto|null
- accessToken: string|null
- initialized: boolean
- status: idle|loading|refreshing|authenticated|anonymous|error
- pendingIntent: PendingIntent|null
- authGeneration: number

actions
- initialize()
- signup(payload)
- login(payload)
- logout()
- refreshSession()
- fetchMe()
- updateMe(payload)
- setPendingIntent(intent)
- consumePendingIntent()
- clearAuthState()
```

#### `referenceStore`

```text
state
- preferenceOptions
- reviewTagOptions: null|array
- preferenceFetchedAt

actions
- ensurePreferenceOptions()
- setReviewTagOptions(options)
- clear()
```

`reviewTagOptions`는 현재 전용 공급 Endpoint가 없어 `TBD`다. 프로필 시설 태그를 후기 경험 태그로 재사용하지 않는다.

#### `homeStore`

```text
state
- response: HomeResponse|null
- status
- error
- fetchedAt

actions
- fetchHome({ coordinates? })
- invalidate()
```

#### `libraryStore`

```text
state
- listResponse
- currentLibrary
- listStatus
- detailStatus

actions
- fetchList(query)
- fetchDetail(id)
- save(id)
- unsave(id)
- clearDetail()
```

#### `bookStore`

```text
state
- localListResponse
- externalSearchResponse
- currentBook
- holdingLibrariesResponse

actions
- fetchLocalList(query)
- searchExternal(query)
- fetchDetail(isbn13)
- fetchHoldingLibraries(isbn13, query)
- save(isbn13)
- unsave(isbn13)
```

#### `programStore`

```text
state
- listResponse
- currentProgram

actions
- fetchList(query)
- fetchDetail(id)
- save(id)
- unsave(id)
```

#### `communityStore`

```text
state
- listResponse
- currentReview
- draft

actions
- fetchList(query)
- fetchDetail(id)
- createReview(jsonPayload)
- updateReview(id, jsonPayload)
- deleteReview(id)
- like(id)
- unlike(id)
- saveDraft(draft)
- clearDraft()
```

#### `myOutingsStore`

```text
state
- listsByType
- fetchedAtByType

actions
- fetchList(type, query)
- invalidate(type?)
- removeLocal(type, targetKey)
```

지원 type:

```text
libraries|books|programs|reviews|liked-reviews
```

#### `interactionStore`

```text
state
- savedLibraryIds: Set<number>
- savedBookIsbns: Set<string>
- savedProgramIds: Set<number>
- likedReviewIds: Set<number>
- hydrationStatusByType

actions
- hydrateLibraries()
- hydrateBooks()
- hydratePrograms()
- hydrateLikedReviews()
- ensureHydrated(type)
- markSaved(type, id)
- markUnsaved(type, id)
- markLiked(reviewId)
- markUnliked(reviewId)
- clear()
```

Hydration은 각 나의 나들이 Endpoint를 `page_size=100`으로 순회하며 `next`가 있으면 다음 페이지를 가져온다. 무한 요청을 방지하기 위해 이미 방문한 `next` URL과 최대 페이지 수를 추적한다.

#### `uiStore`

```text
state
- toasts
- activeDialog
- profileMenuOpen
- filterDrawerOpen
- globalBusyCount

actions
- showToast()
- openDialog()
- closeDialog()
- openFilterDrawer()
- closeFilterDrawer()
- resetUi()
```

### 7.3 전체 Store 초기화

로그아웃과 Refresh 실패는 같은 reset 경로를 사용한다.

```text
사용자 전용 요청 취소
→ 모든 Store $reset()
→ access token 제거
→ PendingIntent·개인 초안 제거
→ Dialog·Drawer 닫기
→ 공개 Route 또는 로그인 이동
```

공개 목록의 URL Query는 제거하지 않는다.

### 7.4 캐시와 무효화

| 데이터 | 재사용 | 무효화 |
|---|---|---|
| 선호 옵션 | 세션 | 로그아웃·새 배포 |
| 홈 | 5분 | 선호 저장, 로그인 상태 변경 |
| 도서관 목록 | 동일 Query | Query 변경 |
| 도서관 상세 | 5분 | 수동 재조회 |
| 외부 책 검색 | 동일 Query 단기 | Query 변경 |
| 책·프로그램 상세 | 10분 | 해당 저장 상태는 interaction만 갱신 |
| 후기 목록 | 1분 | 후기 생성·수정·삭제·좋아요 |
| 나의 나들이 목록 | 1분 | 대응 저장·좋아요·후기 Mutation |
| 사용자 정보 | 세션 | nickname 수정 |

### 7.5 낙관적 업데이트

저장·좋아요는 목표 상태를 즉시 반영할 수 있다.

```text
현재 Set·count 보관
→ UI 즉시 변경
→ POST 또는 DELETE
→ 성공: 서버 응답으로 확정
→ 실패: 이전 상태로 rollback + Toast
```

- 중복 클릭을 막는다.
- POST 응답은 `200` 또는 `201` 모두 성공으로 처리한다.
- DELETE 후기 자체는 `204` body 없음으로 처리한다.
- 후기 생성·수정·삭제는 낙관적으로 처리하지 않는다.

## 8. 공통 데이터 계약

### 8.1 공통 목록·사용자·오류

```ts
interface ApiListResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

interface UserDto {
  id: number
  email: string
  nickname: string
}

interface AuthResponse {
  access: string
  user: UserDto
}

interface DetailErrorResponse {
  detail: string
}

type FieldErrorResponse = Record<string, string[]>
```

### 8.2 이미지

```ts
interface ThumbnailDto {
  url: string | null
  is_fallback: boolean
  fallback_key: string | null
  license_code: string | null
  attribution_text: string | null
}
```

- `is_fallback=true`이면 실제 도서관 사진으로 설명하지 않는다.
- `attribution_text`가 있을 때만 출처 Overlay를 제공한다.
- 상대 URL이면 API origin 기준 절대 URL로 정규화한다.

### 8.3 도서관

```ts
interface LibrarySummaryDto {
  id: number
  name: string
  library_type: string
  sido: string
  sigungu: string
  road_address: string | null
  latitude: string | null
  longitude: string | null
  book_count: number | null
  reading_seat_count: number | null
  thumbnail: ThumbnailDto | null
}

interface LibraryStatisticsDto {
  book_count: number | null
  non_book_count: number | null
  serial_count: number | null
  reading_seat_count: number | null
  building_area: number | string | null
  site_area: number | string | null
}

interface FacilityProfileDto {
  has_reading_room: boolean | null
  has_children_room: boolean | null
  has_digital_room: boolean | null
  has_parking: boolean | null
  has_cafe: boolean | null
  has_wifi: boolean | null
  has_nursing_room: boolean | null
  has_accessible_facility: boolean | null
  has_elevator: boolean | null
  has_lounge: boolean | null
  has_outdoor_space: boolean | null
}

interface LibraryDetailDto extends LibrarySummaryDto {
  phone: string | null
  homepage_url: string | null
  operating_agency: string | null
  short_description: string | null
  statistics: LibraryStatisticsDto | null
  facility_profile: FacilityProfileDto | null
  opening_hours: unknown[]
  closure_rules: unknown[]
}
```

`opening_hours`, `closure_rules`의 내부 객체 구조가 프론트 계약에 추가되기 전에는 raw object를 화면에 출력하지 않는다.

### 8.4 홈

```ts
interface RecommendationThemeDto {
  code: string
  title: string
  subtitle: string
}

interface RecommendedLibraryDto extends LibrarySummaryDto {
  recommendation_reason: string | null
}

interface HomeResponse {
  today_recommendations: {
    theme: RecommendationThemeDto
    items: RecommendedLibraryDto[]
  }
  theme_recommendations: Array<{
    purpose: { code: 'study'|'book'|'kids'|'mood'|'nearby'; label: string }
    items: RecommendedLibraryDto[]
  }>
  personal_recommendations: {
    available: boolean
    reason: string | null
    items: RecommendedLibraryDto[]
  }
}
```

### 8.5 책

```ts
interface BookSummaryDto {
  isbn13: string
  title: string
  authors_text: string | null
  publisher: string | null
  publication_year: string | null
  cover_image_url: string | null
}

interface BookDetailDto extends BookSummaryDto {
  kdc_class_no: string | null
  kdc_class_name: string | null
  source_detail_url: string | null
  loan_count: number | null
}

interface ExternalBookSearchItemDto extends BookDetailDto {
  local_book_id: number | null
}

interface ExternalBookSearchResponse {
  source: 'data4library'
  num_found: number
  page: number
  page_size: number
  results: ExternalBookSearchItemDto[]
}

interface HoldingLibraryResultDto {
  matched: boolean
  library: LibrarySummaryDto | null
  external_library: {
    provider_code: string
    external_library_key: string
    name: string
    address: string | null
    homepage_url: string | null
    phone: string | null
    latitude: string | null
    longitude: string | null
  }
  holding: {
    call_number: string | null
    loan_available: boolean | null
    loan_status: string | null
  }
}

interface HoldingLibrariesResponse {
  isbn13: string
  source: 'data4library'
  count: number
  page: number
  page_size: number
  results: HoldingLibraryResultDto[]
}
```

`loan_available=null`은 대출 불가가 아니라 상태 미제공이다.

### 8.6 프로그램

```ts
interface ProgramLibraryDto {
  id: number
  name: string
  sigungu: string
}

interface ProgramSummaryDto {
  id: number
  title: string
  library: ProgramLibraryDto
  category: string
  category_display: string
  target: string[]
  target_display: string[]
  application_start_date: string | null
  application_end_date: string | null
  application_status: string | null
  operation_start_date: string | null
  operation_end_date: string | null
  operation_status: string | null
  source_board: string | null
  source_url: string | null
}

interface ProgramDetailDto extends ProgramSummaryDto {
  source_sido: string | null
  source_sigungu: string | null
  source_library_name: string | null
  provider_code: string | null
  external_program_key: string | null
  post_date: string | null
  collected_at: string | null
  tags: unknown[]
}
```

프로그램 카드에 이미지 필드는 요구하지 않는다.

### 8.7 후기

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
  tags: unknown[]
  images: unknown[]
  related_books: unknown[]
  related_programs: unknown[]
}

interface CreateReviewPayload {
  library_id: number
  content: string
  tag_codes: string[]
  book_ids: string[]
  program_ids: number[]
}

interface UpdateReviewPayload {
  content?: string
  tag_codes?: string[]
}

// book_ids·program_ids 수정 지원은 API 계약 확인 후 별도 확장한다.
```

- `images`는 조회 전용으로 렌더링할 수 있으나 v2.0은 업로드 UI를 제공하지 않는다.
- `is_liked`, `moderation_status`, `can_edit`는 응답에 없으므로 별도 DTO에 추가하지 않는다.

### 8.8 선호

```ts
interface PreferenceOptionDto {
  purposes: Array<{
    code: string
    label: string
    description: string | null
    display_order: number
  }>
  regions: Array<{
    region_key: string
    sido: string
    sigungu: string
    label: string
  }>
  tags: Array<{
    code: string
    label: string
    tag_group: string
    description: string | null
    display_order: number
  }>
}

interface UserPreferencesDto {
  purposes: Array<{ code: string; label: string; weight: string; display_order: number }>
  regions: Array<{ region_key: string; sido: string; sigungu: string; weight: string; display_order: number }>
  tags: Array<{ code: string; label: string; weight: string; display_order: number }>
}

interface ReplacePreferencesPayload {
  purpose_codes: string[]
  regions: Array<{ sido: string; sigungu: string }>
  tag_codes: string[]
}
```

### 8.9 저장 관계

```ts
interface SavedLibraryItemDto {
  id: number
  memo: string
  created_at: string
  updated_at: string
  library: LibrarySummaryDto
}

interface SavedBookItemDto {
  id: number
  memo: string
  created_at: string
  updated_at: string
  book: BookSummaryDto
}

interface SavedProgramItemDto {
  id: number
  memo: string
  created_at: string
  updated_at: string
  program: ProgramSummaryDto
}

interface LikedReviewItemDto {
  id: number
  liked_at: string
  review: ReviewDto
}
```

`memo` 수정 Endpoint가 없으므로 v2.0에서 편집 UI를 제공하지 않는다.

### 8.10 null·빈 배열·0 표시

| 값 | 의미 | 표시 원칙 |
|---|---|---|
| `null` | 미제공·미확인 가능 | 0·없음으로 변환하지 않음 |
| `false` | 명시적 false | 시설은 기본 미표시 |
| `[]` | 현재 관계·데이터 없음 | 빈 상태 또는 섹션 숨김 |
| `0` | 실제 0일 수 있음 | 계약상 숫자면 `0` 표시 가능 |
| `is_fallback=true` | 시스템 대체 이미지 | 실제 촬영 이미지로 설명하지 않음 |

## 9. 디자인 시스템과 공통 UI

### 9.1 디자인 참고 원칙

첨부 시안은 시각적 방향과 컴포넌트 패턴의 참고 자료다. 시안에 임의로 포함된 기능과 전국 예시 데이터는 구현 요구사항이 아니다. 기능·데이터가 충돌하면 API 계약과 본 명세를 우선한다.

디자인 방향:

- 밝은 아이보리 배경과 흰색 Surface
- 녹색 브랜드 포인트
- 둥근 카드와 얇은 Border
- 과하지 않은 부드러운 그림자
- 충분한 여백을 둔 따뜻한 공공서비스형 UI
- 도서관 정보를 딱딱한 행정표가 아니라 방문 후보로 이해할 수 있는 구성

유지할 요소:

- 로고와 서비스명
- 현재 메뉴 녹색 underline
- 아이보리·연녹색 Hero
- 녹색 Primary Button, 밝은 Secondary Button
- 태그 Chip, 상태 Badge, Bookmark·Heart Icon
- 검색·필터와 결과 목록의 구획
- 도서관 상세 정보 Card Grid
- 나의 나들이의 탭형 저장 목록

제외할 요소:

- 홈 검색창
- 알림 Bell과 임의 도움말
- 내부 프로그램 신청처럼 보이는 CTA
- 실시간 좌석
- 후기 별점·제목·이미지 업로드
- 현재 API에 없는 성향 분석 Card

### 9.2 UX 설계 원칙

1. **점진적 공개**: 목록에는 선택에 필요한 요약, 상세에는 전체 정보를 보여준다.
2. **응답 가능한 사실만 표시**: 서버가 제공하지 않은 운영 상태·태그·추천 점수는 만들지 않는다.
3. **탐색 우선**: 비회원도 공개 정보를 탐색하고 사용자 데이터 생성 시에만 로그인한다.
4. **불확실성 보존**: 미제공·미확인·false·없음을 구분한다.
5. **행동 결과 예측 가능성**: 카드 링크와 저장·좋아요·외부 링크를 분리한다.
6. **지도 보조성**: Kakao 지도는 상세 위치 확인과 길찾기 링크로 한정한다.
7. **부분 실패 격리**: 정보나루·지도·관련 목록 실패가 전체 화면을 무너뜨리지 않게 한다.

### 9.3 디자인 토큰

```css
:root {
  --color-brand-700: #1f6b3a;
  --color-brand-600: #2f7d45;
  --color-brand-100: #eef6ee;
  --color-ivory: #fbfaf5;
  --color-surface: #ffffff;
  --color-surface-subtle: #f5f7f3;
  --color-text: #1f2521;
  --color-text-muted: #68716a;
  --color-border: #e2e7e0;
  --radius-sm: 0.5rem;
  --radius-md: 0.75rem;
  --radius-lg: 1rem;
  --radius-xl: 1.25rem;
  --shadow-card: 0 0.25rem 1rem rgb(31 55 37 / 8%);
}
```

선택·오류·성공을 색상 하나로만 구분하지 않고 Icon, Border, Text를 함께 사용한다.

### 9.4 공통 컴포넌트

Layout:

- `AppHeader`
- `AppFooter`
- `MobileBottomNavigation`
- `ProfileMenuDrawer`
- `PageContainer`
- `PageHeader`
- `PageHeroBanner`
- `MemberSubNavigation`

Card:

- `LibraryCard`
- `BookCard`
- `ExternalLibraryCard`
- `ProgramCard`
- `ReviewCard`
- `RelatedBookMiniCard`
- `RelatedProgramMiniCard`

Action:

- `SaveButton`
- `LikeButton`
- `AuthGate`
- `ExternalLinkButton`

Filter·Feedback:

- `SearchBar`
- `FilterPanel`
- `FilterDrawer`
- `ActiveFilterChips`
- `SortSelect`
- `PaginationBar`
- `ResultCount`
- `LoadingSkeleton`
- `EmptyState`
- `ErrorState`
- `InlineError`
- `ConfirmDialog`
- `LoginRequiredDialog`
- `ToastRegion`

Media:

- `ResponsiveImage`
- `AttributionOverlay`
- `KakaoMapPanel`

### 9.5 핵심 컴포넌트 계약

#### `SaveButton`

```text
props
- resourceType: library|book|program
- resourceId: number|string
- state: unknown|saved|unsaved
- disabled

emits
- success
- error
```

- Guest면 Auth Gate를 실행한다.
- 로그인 회원의 `unknown`은 interaction hydration 중 상태다.
- 저장은 POST, 해제는 DELETE다.
- Icon만 보일 때도 `aria-label`을 제공한다.

#### `LikeButton`

- `state: unknown|liked|unliked`, `likeCount`를 받는다.
- 좋아요는 POST, 해제는 DELETE다.
- Count는 0 미만으로 내려가지 않는다.

#### `AttributionOverlay`

- `attribution_text`가 있을 때만 ⓘ 버튼을 표시한다.
- hover, focus, tap에서 전체 문구를 표시한다.
- `aria-expanded`, `aria-controls`, `role=note`를 사용한다.

#### `KakaoMapPanel`

```text
props
- libraryId
- name
- roadAddress
- latitude
- longitude
```

- 좌표 검증, SDK 로드, 지도·단일 Marker·InfoWindow, 길찾기 URL, fallback을 담당한다.
- 현재 위치 수집·거리 계산·Geocoding·Kakao REST API 호출은 담당하지 않는다.

### 9.6 카드 정보 우선순위

#### `LibraryCard`

필수:

- 대표 이미지 또는 fallback
- 도서관명
- 구·군·유형
- 주소 한 줄
- 장서 수·좌석 수 — 값이 있을 때
- 저장 버튼

추천 카드 조건부:

- `recommendation_reason`

제외:

- 오늘 운영 상태·운영시간
- 태그·시설 Chip
- 거리 — 응답에 거리 필드 없음
- 전화번호·운영기관·전체 통계

#### `BookCard`

- 세로형 표지
- 도서명·저자
- 출판사·출판연도
- KDC 이름 — 값이 있을 때
- 외부 검색에서는 `loan_count` 조건부
- 저장 식별자는 ISBN13

#### `ExternalLibraryCard`

- 외부 도서관명·주소·전화·홈페이지
- `matched=false` 안내
- 내부 도서관 상세 링크와 저장 버튼 없음
- `loan_available=null`이면 “대출 상태 미제공”

#### `ProgramCard`

- 프로그램명
- 도서관 링크
- `category_display`
- `target_display`
- 신청·운영 기간과 상태
- 저장 버튼
- 원문 링크

응답에 이미지가 없으므로 이미지 영역을 필수로 만들지 않는다. “신청하기” CTA를 사용하지 않는다.

#### `ReviewCard`

- 작성자 nickname·작성일
- 도서관 링크
- 후기 본문
- 서버가 제공한 태그
- 조회수·좋아요 수와 버튼
- 서버 응답에 이미지·관련 관계가 있을 때 읽기 전용 미리보기

목록 카드에 수정·삭제 메뉴를 넣지 않는다.

## 10. 공통 상호작용과 화면 상태

### 10.1 로딩

- 첫 진입은 실제 레이아웃과 유사한 Skeleton을 사용한다.
- 목록 재조회는 검색·필터를 유지하고 결과만 갱신한다.
- 저장·좋아요는 버튼만 Busy 상태로 바꾼다.
- 인증 초기화처럼 화면 구성이 불가능할 때만 전면 Loading을 사용한다.

### 10.2 빈 상태

| 화면 | 문구 | CTA |
|---|---|---|
| 도서관 | 조건에 맞는 도서관이 없습니다 | 검색·구군·유형 초기화 |
| 책 검색 전 | 도서명, 저자, ISBN으로 책을 찾아보세요 | 검색 입력 Focus |
| 책 결과 없음 | 검색 결과가 없습니다 | 검색어 지우기 |
| 프로그램 | 현재 표시할 프로그램이 없습니다 | 필터 초기화 |
| 커뮤니티 | 아직 등록된 후기가 없습니다 | 로그인 회원은 첫 후기 작성 |
| 저장 목록 | 아직 저장한 항목이 없습니다 | 해당 탐색 페이지 이동 |

프로그램 0건과 후기 0건은 서버 오류가 아니다.

### 10.3 오류 상태

| 상태 | 문구 | 처리 |
|---|---|---|
| 네트워크 | 연결이 불안정해 정보를 불러오지 못했어요 | 다시 시도 |
| 400 | 입력하거나 선택한 값을 확인해 주세요 | Field Error 연결 |
| 401 Refresh 성공 | 문구 없음 | 원 요청 재시도 |
| 401 Refresh 실패 | 다시 로그인해 주세요 | Reset 후 로그인 |
| 403 | 이 페이지에 접근할 수 없어요 | 403 화면 |
| 404 | 요청한 정보를 찾을 수 없어요 | 자원별 NotFound |
| 503 책 검색 | 책 검색 서비스를 사용할 수 없어요 | 로컬 화면 유지·재시도 |
| 지도 실패 | 지도를 불러오지 못했어요 | 주소·외부 링크 유지 |

### 10.4 위치 권한

- 홈 진입 즉시 요청하지 않는다.
- `nearby` 테마 사용자가 선택할 때 이유를 먼저 설명한다.
- 좌표는 `GET /home/?lat=&lng=` 요청에만 사용한다.
- 거절하면 오류 페이지가 아니라 다른 테마·지역 탐색을 유지한다.

### 10.5 외부 링크

- 도서관 홈페이지·프로그램 원문·카카오 길찾기는 새 탭으로 연다.
- `target="_blank" rel="noopener noreferrer"`를 사용한다.
- URL이 없으면 CTA를 숨긴다.
- 내부 프로그램 신청을 암시하지 않는다.

### 10.6 날짜·숫자

- Timezone: `Asia/Seoul`
- 날짜: `2026. 6. 24.`
- 기간: `2026. 6. 15. ~ 6. 30.`
- 숫자: `61,405권`, `134석`, `890.58㎡`
- null 숫자를 0으로 표시하지 않는다.

### 10.7 Toast

성공 예시:

- 도서관을 저장했어요.
- 저장을 해제했어요.
- 후기에 좋아요를 표시했어요.
- 후기를 등록했어요.
- 선호 설정을 저장했어요.

### 10.8 작성 중 이탈 보호

후기 작성·수정과 선호 설정에서 변경사항이 있으면 SPA 이동과 새로고침 전에 확인한다. 후기 초안에는 이미지가 포함되지 않는다.

### 10.9 페이지네이션

- 페이지 번호 방식을 사용한다.
- URL에 `page`를 기록한다.
- 필터·검색 변경 시 `page=1`.
- 한 페이지 이하면 Pagination을 숨긴다.
- 외부 책 검색과 소장 도서관 응답은 자체 `page`, `page_size` 구조를 사용한다.

### 10.10 로그인 필요 안내

| 행동 | 제목 | 로그인 후 |
|---|---|---|
| 도서관 저장 | 도서관을 저장하려면 로그인이 필요해요 | POST 자동 실행 가능 |
| 책 저장 | 관심 책을 저장하려면 로그인이 필요해요 | POST 자동 실행 가능 |
| 프로그램 저장 | 프로그램을 저장하려면 로그인이 필요해요 | POST 자동 실행 가능 |
| 후기 좋아요 | 후기에 공감하려면 로그인이 필요해요 | POST 자동 실행 가능 |
| 후기 작성 | 후기를 작성하려면 로그인이 필요해요 | 작성 Route 복귀, 자동 제출 금지 |
| 나의 나들이 | 로그인 후 저장한 항목을 볼 수 있어요 | 보호 Route 복귀 |

버튼은 `[로그인하기] [나중에]`로 통일한다.

### 10.11 검색·필터 공통 UX

- Enter 또는 검색 버튼으로 실행한다.
- 모바일 Filter Drawer는 “결과 보기”에서 한 번에 적용한다.
- 활성 Query를 Chip으로 표시하고 개별 제거·전체 초기화를 제공한다.
- API가 지원하지 않는 필터는 비활성 상태로도 노출하지 않는다.

도서관 활성 예시:

```text
[검색: 시민 ×] [부산진구 ×] [공공도서관 ×]  전체 초기화
```

### 10.12 마이크로카피

권장:

- 오늘은 이런 도서관도 좋아요
- 검색 조건을 조금 바꿔볼까요?
- 아직 저장한 항목이 없어요
- 원문에서 신청 정보를 확인해 주세요
- 대출 상태가 제공되지 않았어요

피할 표현:

- AI가 엄선한 추천
- 실시간 좌석이 여유로워요
- 이 프로그램 신청하기
- 데이터 없음
- 저장 안 됨 — 상태 hydration 전

### 10.13 부분 실패

- 정보나루 검색 실패 시 도서관·프로그램·커뮤니티 Navigation은 유지한다.
- Kakao 지도 실패는 도서관 상세 전체 실패가 아니다.
- 관련 프로그램·후기 별도 요청 실패 시 기본 도서관 상세를 유지한다.

## 11. 인증·온보딩 페이지 명세

인증 식별자는 이메일이다. 로그인 요청과 회원가입 요청에는 `username`을 전송하지 않는다. `/users/me/` 응답도 `id`, `email`, `nickname`을 기준으로 처리한다.

### 11.1 로그인 — `FR-AUTH-LOGIN`

| 항목 | 명세 |
|---|---|
| Route | `/auth/login` |
| API | `POST /auth/login/` |
| Request | `{ email, password }` |
| 성공 | Access 저장 + User 저장 + redirect |

화면:

1. 이메일
2. 비밀번호와 표시 전환
3. 로그인 버튼
4. 회원가입 링크
5. Form Error

검증:

- email trim 후 필수
- password 필수
- 제출 중 중복 클릭 금지

오류 문구:

```text
이메일 또는 비밀번호를 확인해 주세요.
```

성공 흐름:

```text
POST /auth/login/
→ access·user 저장
→ refresh cookie는 서버가 설정
→ 안전한 redirect 또는 홈
→ PendingIntent가 있으면 대상 화면에서 한 번 소비
```

### 11.2 회원가입 — `FR-AUTH-SIGNUP`

| 항목 | 명세 |
|---|---|
| Route | `/auth/signup` |
| API | `POST /auth/signup/` |
| Request | `{ email, password, nickname }` |
| Response | `201 { access, user }` |
| 성공 | `/onboarding/preferences` |

입력:

1. 이메일
2. 닉네임
3. 비밀번호
4. 비밀번호 확인 — API 전송 제외

서버 필드 오류는 해당 입력 아래에 표시한다. 회원가입 성공 시 이미 인증된 상태이므로 별도 로그인 없이 온보딩으로 이동한다.

### 11.3 초기 선호 설정 — `FR-AUTH-ONBOARDING`

| 항목 | 명세 |
|---|---|
| Route | `/onboarding/preferences` |
| API | `GET /preferences/options/`, `GET /users/me/preferences/`, `PUT /users/me/preferences/` |
| 필수 | 선택형, 건너뛰기 가능 |

단계:

1. 방문 목적 선택
2. 선호 지역 선택
3. 선호 시설 태그 선택
4. 저장

Payload:

```json
{
  "purpose_codes": ["study", "book", "program"],
  "regions": [{ "sido": "부산광역시", "sigungu": "해운대구" }],
  "tag_codes": ["facility_parking", "facility_wifi"]
}
```

건너뛰기는 PUT 없이 홈으로 이동한다. 현재 위치 좌표는 저장하지 않는다.

## 12. 홈 페이지 명세

### 12.1 홈 — `FR-HOME-001`

| 항목 | 명세 |
|---|---|
| Route | `/` |
| 접근 | 공개 |
| API | `GET /home/` |
| Query | `lat`, `lng` 선택 |

### 12.2 화면 순서

```text
Hero
→ 오늘의 추천
→ 여기는 어때요? — available일 때
→ 테마별 추천 5개
→ 주요 탐색 Route 안내
```

홈에는 검색창을 두지 않는다.

### 12.3 데이터 조회

```text
Home mount
→ GET /home/
→ 세 영역을 한 응답으로 렌더링
```

nearby 선택:

```text
사용자 선택
→ 위치 사용 설명
→ Geolocation
→ 허용: GET /home/?lat={lat}&lng={lng}
→ 거절: 기존 홈 유지 + 지역 탐색 안내
```

별도 테마 Endpoint를 호출하지 않는다.

### 12.4 오늘의 추천

- `today_recommendations.theme.title`, `subtitle` 표시
- `items` 최대 3개
- 결과가 1~2개면 빈 카드를 채우지 않는다.
- `recommendation_reason`이 있으면 카드에 한 줄 표시한다.
- 운영 상태·태그·거리·저장 상태를 응답 없이 추가하지 않는다.

### 12.5 개인 추천

노출 조건:

```js
personal_recommendations.available &&
personal_recommendations.items.length > 0
```

`available=false`이면 카드 섹션을 숨긴다. `reason`은 개인 추천 미노출 안내나 선호 설정 CTA에 사용할 수 있다. 행동 기반 개인화는 현재 보류이므로 문구가 실제 서버 동작보다 과장되지 않게 한다.

### 12.6 테마별 추천

고정 코드:

- `study`
- `book`
- `kids`
- `mood`
- `nearby`

각 그룹은 최대 6개를 표시한다. `program`은 홈 테마에 포함하지 않는다.

현재 도서관 목록 API는 `purpose` Query를 지원하지 않으므로 “더보기”를 `/libraries?purpose=...`로 연결하지 않는다. v2.0에서는 다음 중 하나를 사용한다.

- 해당 테마의 홈 응답 카드만 표시
- “도서관 전체 보기”는 `/libraries`로 이동

### 12.7 완료 조건

- Home 요청은 기본 1회다.
- nearby 선택 전 위치 권한을 요청하지 않는다.
- 테마 5개만 노출한다.
- 응답에 없는 운영·태그·거리 정보를 만들지 않는다.
- 개인 추천 `available=false`에서 빈 카드 영역을 표시하지 않는다.

## 13. 도서관 찾기·상세 명세

### 13.1 도서관 목록 — `FR-LIB-LIST`

| 항목 | 명세 |
|---|---|
| Route | `/libraries` |
| API | `GET /libraries/` |
| Query | `page`, `page_size`, `q`, `sigungu`, `library_type` |

### 13.2 목록 UI

데스크톱:

```text
PageHeader
검색 입력
구·군 Select
도서관 유형 Select
결과 Count
LibraryCard Grid
Pagination
```

모바일에서는 구·군과 유형을 Filter Drawer에서 편집한다.

### 13.3 검색·필터

- `q`: 서버 검색 대상에 맡기며 프론트가 검색 범위를 과장해 설명하지 않는다.
- `sigungu`: v2.0에서 단일 값
- `library_type`: v2.0에서 단일 값
- 값이 바뀌면 `page=1`

현재 활성 UI에서 제외:

- `purpose`
- `facility`
- `open_today`, `open_now`
- `weekend_open`, `holiday_status`, `late_open_after`
- 장서·좌석 범위
- 거리·반경·정렬

### 13.4 LibraryCard

표시:

- thumbnail
- 도서관명
- 구·군·유형
- 주소 한 줄
- 장서 수
- 좌석 수
- 저장 버튼

저장 상태는 로그인 회원의 interaction hydration 후 확정한다.

### 13.5 결과 없음

```text
선택한 조건에 맞는 도서관이 없습니다.
검색어, 구·군 또는 도서관 유형을 바꿔보세요.
```

CTA:

- 검색어 지우기
- 구·군 해제
- 유형 해제
- 전체 초기화

### 13.6 도서관 상세 — `FR-LIB-DETAIL`

| 항목 | 명세 |
|---|---|
| Route | `/libraries/:id` |
| API | `GET /libraries/{id}/` |
| 관련 프로그램 | `GET /programs/?library_id={id}` |
| 관련 후기 | `GET /reviews/?library_id={id}` |

화면 순서:

```text
대표 이미지·요약·저장
→ 기본 정보
→ 통계
→ 확인된 시설
→ 위치 지도
→ 관련 프로그램
→ 관련 후기
```

제거·보류:

- 오늘 운영·지금 운영 Badge
- 주요 태그
- 비슷한 도서관
- 정밀 운영 상태

### 13.7 기본 정보와 통계

기본 정보:

- 주소
- 전화 — `tel:`
- 홈페이지 — 외부 링크
- 운영기관
- 짧은 설명

통계:

- 도서 수
- 비도서 수
- 연속간행물 수
- 열람좌석 수
- 건물면적
- 부지면적

null은 0으로 표시하지 않는다.

### 13.8 시설

- `facility_profile`이 null이면 “확인된 시설 정보가 아직 없습니다.”
- profile이 있으면 `true`인 시설만 Chip으로 표시한다.
- `false`를 “시설 없음” Badge로 만들지 않는다.
- field가 null이면 미확인으로 남긴다.

### 13.9 운영시간 데이터

`opening_hours`, `closure_rules`는 배열로 오지만 내부 구조가 현재 프론트 계약에 정의되지 않았다.

- 배열이 비어 있으면 운영정보 섹션을 숨기거나 “등록된 운영 정보가 없습니다.”를 표시한다.
- 객체 구조가 확정되기 전 raw JSON을 렌더링하지 않는다.
- 운영 여부를 프론트가 계산하지 않는다.

### 13.10 Kakao 지도

- 좌표가 모두 유효할 때만 SDK를 로드한다.
- 단일 Marker와 도서관명 InfoWindow를 표시한다.
- 주소와 길찾기 외부 링크를 인접 텍스트로 제공한다.
- 좌표 없음·Key 누락·SDK 오류는 지도 영역 fallback으로 처리한다.

### 13.11 저장

```text
POST   /libraries/{id}/save/   → saved=true
DELETE /libraries/{id}/save/   → saved=false
```

`200`, `201`을 성공으로 처리하며 이미 목표 상태여도 정상 응답으로 본다.

### 13.12 완료 조건

- 미지원 필터를 요청하지 않는다.
- 운영 상태를 추론하지 않는다.
- 시설 true만 표시한다.
- 지도 오류가 상세 전체를 막지 않는다.
- 관련 프로그램·후기 실패가 기본 상세를 막지 않는다.

## 14. 책 둘러보기·상세 명세

### 14.1 책 둘러보기 — `FR-BOOK-LIST`

| 항목 | 명세 |
|---|---|
| Route | `/books` |
| 로컬 목록 | `GET /books/` |
| 외부 검색 | `GET /books/search/` |

### 14.2 초기 화면

v2.0에는 인기 도서 Endpoint가 없다. 초기 화면은 검색 중심으로 구성한다.

```text
Hero·검색 안내
→ 검색 유형 Select
→ 검색어
→ 검색 버튼
→ 검색 전 안내 또는 등록된 책 목록
```

`GET /books/`를 사용하는 경우 제목은 “서비스에 등록된 책”으로 표현하고 인기 도서로 표현하지 않는다. count가 0이면 섹션을 숨길 수 있다.

### 14.3 외부 검색

지원 `search_type`:

- `title`
- `author`
- `isbn`
- `keyword`
- `publisher`

기본 요청:

```text
GET /books/search/?search_type={type}&q={query}&page={page}&page_size={size}
```

검색어가 비어 있으면 외부 전체 검색을 보내지 않는다.

응답은 공통 DRF Pagination이 아니라 `num_found`, `page`, `page_size`, `results` 구조다.

`503`이면 다음을 표시한다.

```text
책 검색 서비스를 사용할 수 없어요.
잠시 후 다시 시도해 주세요.
```

### 14.4 BookCard

- 표지 2:3
- 도서명·저자
- 출판사·연도
- KDC 분류명
- `loan_count` 조건부
- ISBN13 기반 저장 버튼

`local_book_id`가 null이어도 ISBN13은 식별자로 유지한다.

### 14.5 책 상세 — `FR-BOOK-DETAIL`

| 항목 | 명세 |
|---|---|
| Route | `/books/:isbn13` |
| API | `GET /books/{isbn13}/` |
| 소장 | `GET /books/{isbn13}/libraries/` |
| 저장 | POST·DELETE `/books/{isbn13}/save/` |

표시:

- 표지
- 도서명·저자·출판사·연도
- KDC 분류
- 대출 집계 수 — 값이 있을 때
- 원천 상세 링크 — 값이 있을 때
- 저장 버튼
- 부산 소장 도서관

외부 검색 결과 ISBN이 상세 Endpoint에서 조회 가능한지는 Contract Test로 확인한다. 404이면 검색 결과로 돌아가는 CTA와 “상세 정보가 아직 등록되지 않았습니다.” 안내를 제공하고, 프론트가 데이터를 임의로 저장하지 않는다.

### 14.6 소장 도서관

#### `matched=true`

- 내부 LibraryCard 축약형
- `/libraries/{id}` 이동 가능
- 내부 도서관 데이터와 외부 원천 정보를 함께 받은 경우 내부 도서관을 주 표시로 사용

#### `matched=false`

- `ExternalLibraryCard`
- 내부 상세 링크 없음
- 저장 버튼 없음
- 외부 명칭·주소·전화·홈페이지 표시
- “서비스 도서관 정보와 아직 연결되지 않았습니다.” 안내 가능

대출 상태:

| 값 | 표시 |
|---|---|
| `loan_available=true` | 대출 가능 — 서버가 명시한 경우만 |
| `loan_available=false` | 대출 불가 — 서버가 명시한 경우만 |
| `loan_available=null` | 대출 상태 미제공 |

### 14.7 저장

```text
POST   /books/{isbn13}/save/
DELETE /books/{isbn13}/save/
```

내부 숫자 Book ID를 사용하지 않는다.

### 14.8 완료 조건

- 인기 도서라고 잘못 표시하지 않는다.
- ISBN13을 저장 식별자로 사용한다.
- matched false를 내부 상세로 연결하지 않는다.
- `loan_available=null`을 대출 불가로 표시하지 않는다.
- 정보나루 503을 전체 앱 오류로 승격하지 않는다.

## 15. 문화 프로그램 목록·상세 명세

### 15.1 프로그램 목록 — `FR-PROGRAM-LIST`

| 항목 | 명세 |
|---|---|
| Route | `/programs` |
| API | `GET /programs/` |
| Query | `page`, `page_size`, `q`, `library_id`, `sigungu`, `category`, `target`, `application_status`, `operation_status` |

### 15.2 검색·필터

- 검색어
- 도서관 — `library_id`
- 구·군
- 프로그램 분류
- 대상
- 신청 상태
- 운영 상태

API 계약이 다중 Query 직렬화를 명시하지 않았으므로 각 필터는 v2.0에서 단일 선택으로 요청한다.

### 15.3 ProgramCard

- 프로그램명
- 운영 도서관 링크
- `category_display`
- `target_display`
- 신청 기간·상태
- 운영 기간·상태
- 저장 버튼
- 원문 링크

응답에 이미지가 없으므로 이미지 Placeholder를 억지로 만들지 않고 텍스트 중심 Card를 사용한다. 분류 Icon은 장식적 표현으로 MAY 사용한다.

### 15.4 상태 표시

사용자용 분류·대상은 서버의 `category_display`, `target_display`를 사용한다.

신청·운영 상태는 raw code를 Badge style에 사용하고, 알려지지 않은 code는 “상태 확인 필요”로 표시한다. 전체 enum이 확정되기 전 프론트에서 임의 전체 목록을 단정하지 않는다.

예시 계약에서 확인된 값:

- `application_status=available`
- `operation_status=upcoming`

### 15.5 프로그램 상세 — `FR-PROGRAM-DETAIL`

표시:

- 프로그램명
- 운영 도서관
- 분류와 대상
- 신청 기간·상태
- 운영 기간·상태
- 원천 게시판
- 게시일·수집일 — 값이 있을 때
- 저장 버튼
- “원문에서 확인” 외부 링크

내부 신청 CTA는 제공하지 않는다.

### 15.6 저장

```text
POST   /programs/{id}/save/
DELETE /programs/{id}/save/
```

### 15.7 빈 상태

프로그램 count가 0이어도 Import 전 정상 상태일 수 있다.

```text
현재 표시할 문화 프로그램이 없습니다.
프로그램 데이터가 추가되면 이곳에서 확인할 수 있어요.
```

## 16. 커뮤니티·후기 명세

### 16.1 후기 목록 — `FR-REVIEW-LIST`

| 항목 | 명세 |
|---|---|
| Route | `/community` |
| API | `GET /reviews/` |
| Query | `page`, `page_size`, `q`, `library_id`, `tag`, `user_id`, `ordering` |

정렬:

- 최신순 `-created_at`
- 조회수순 `-view_count`
- 좋아요순 `-like_count`

### 16.2 후기 태그 필터 계약 공백

목록은 `tag` Query를 지원하고 작성은 `tag_codes` 1~5개를 요구한다. 그러나 현재 API 계약에는 후기 선택 가능 태그 옵션 Endpoint가 없다.

- `/preferences/options/`의 시설 태그를 후기 태그로 재사용하지 않는다.
- 후기 Form 완료 전 백엔드가 후기 선택 가능 태그 목록 또는 버전 관리된 seed 목록을 제공해야 한다.
- 전용 목록이 없으면 후기 작성 기능은 P0 계약 공백으로 표시한다.

### 16.3 ReviewCard

표시:

- 작성자 nickname
- 작성일
- 도서관 링크
- 본문
- 서버가 제공한 태그
- 조회수·좋아요 수
- 좋아요 버튼
- 이미지·관련 책·프로그램은 응답에 있으면 읽기 전용 미리보기

응답에 프로필 이미지가 없으므로 이니셜 Avatar 또는 일반 Icon을 프론트 표현으로 사용할 수 있다.

### 16.4 좋아요

```text
POST   /reviews/{id}/like/
DELETE /reviews/{id}/like/
```

- POST `200|201` 성공
- DELETE `200` 성공
- 응답 `like_count`를 현재 Card·상세에 반영한다.
- 초기 liked 상태는 `interactionStore.likedReviewIds`에서 확인한다.

### 16.5 후기 상세 — `FR-REVIEW-DETAIL`

| 항목 | 명세 |
|---|---|
| Route | `/reviews/:id` |
| API | `GET /reviews/{id}/` |

표시:

- 작성자·작성일·수정일
- 도서관 링크
- 본문
- 태그
- 조회수·좋아요
- 응답에 존재하는 이미지·관련 책·프로그램
- 작성자일 때 수정·삭제 메뉴

상세 GET이 조회수에 영향을 줄 수 있으므로 중복 요청을 방지하고 hover prefetch하지 않는다.

### 16.6 후기 작성 — `FR-REVIEW-CREATE`

| 항목 | 명세 |
|---|---|
| Route | `/reviews/new` |
| API | `POST /reviews/` |
| Content-Type | `application/json` |

Form:

1. 도서관 — 필수
2. 본문 — 1~200자
3. 후기 경험 태그 — 1~5개
4. 관련 책 ISBN — 선택
5. 관련 프로그램 ID — 선택, 같은 도서관만
6. 제출

제공하지 않는 입력:

- 제목
- 별점
- 방문 목적
- 이미지 업로드

Payload:

```json
{
  "library_id": 1,
  "content": "조용하고 좋았어요.",
  "tag_codes": ["quiet", "study"],
  "book_ids": ["9788936434120"],
  "program_ids": [1]
}
```

도서관 상세에서 진입하면 `library_id` Query로 선선택한다. 도서관이 바뀌면 다른 도서관의 프로그램 선택을 제거한다.

### 16.7 후기 수정 — `FR-REVIEW-EDIT`

| 항목 | 명세 |
|---|---|
| Route | `/reviews/:id/edit` |
| API | `GET /reviews/{id}/`, `PATCH /reviews/{id}/` |
| 접근 | 작성자 |
| 전송 | JSON |

- user ID 비교 후 메뉴를 노출한다.
- 서버 403이 최종 권한 기준이다.
- 이미지 편집 UI는 제공하지 않는다.
- 도서관 변경 허용 여부가 명시되지 않았으므로 v2.0에서는 도서관을 read-only로 유지한다.
- v2.0 활성 계약에서는 본문·태그를 전송한다.
- 관련 책·프로그램 수정은 PATCH 지원 계약이 확정될 때까지 읽기 전용으로 둔다.

### 16.8 후기 삭제

```text
DELETE /reviews/{id}/
→ 204 No Content
→ body 파싱 금지
```

삭제 확인 후 성공하면 이전 나의 후기 목록 또는 커뮤니티로 이동한다.

### 16.9 초안

```ts
interface ReviewDraft {
  mode: 'create'|'edit'
  reviewId?: number
  libraryId?: number
  content: string
  tagCodes: string[]
  bookIsbns: string[]
  programIds: number[]
  savedAt: string
}
```

- `sessionStorage`
- 이미지 File 없음
- 24시간 후 폐기
- 제출 성공 시 삭제

### 16.10 완료 조건

- JSON으로 작성·수정한다.
- 이미지 Uploader가 없다.
- 본문 1~200자, 태그 1~5개를 검증한다.
- 같은 도서관 프로그램 규칙을 지킨다.
- 좋아요 Method가 POST·DELETE다.
- `moderation_status` UI를 생성하지 않는다.
- 후기 태그 공급 계약이 해결되지 않으면 완료로 표시하지 않는다.

## 17. 나의 나들이 명세

### 17.1 영역 정의

v2.0의 나의 나들이는 통합 성향 Dashboard가 아니라 다섯 개 목록을 모은 회원 전용 Container다.

```text
/my-outings
→ /my-outings/libraries
```

`MemberSubNavigation`:

- 저장한 도서관
- 저장한 책
- 저장한 프로그램
- 좋아요한 후기
- 내가 쓴 후기

### 17.2 저장한 도서관

| Route | API |
|---|---|
| `/my-outings/libraries` | `GET /my-outings/libraries/` |

최상위 item은 저장 관계이고 실제 카드 데이터는 `item.library`다. `memo`는 읽기 전용이며 비어 있으면 표시하지 않는다.

### 17.3 저장한 책

| Route | API |
|---|---|
| `/my-outings/books` | `GET /my-outings/books/` |

`item.book.isbn13`을 상세·저장 해제 식별자로 사용한다.

### 17.4 저장한 프로그램

| Route | API |
|---|---|
| `/my-outings/programs` | `GET /my-outings/programs/` |

`item.program.id`를 상세·저장 해제 식별자로 사용한다.

### 17.5 좋아요한 후기

| Route | API |
|---|---|
| `/my-outings/liked-reviews` | `GET /my-outings/liked-reviews/` |

최상위 item의 `liked_at`과 `item.review`를 구분한다.

### 17.6 내가 쓴 후기

| Route | API |
|---|---|
| `/my-outings/reviews` | `GET /my-outings/reviews/` |

응답에는 공개 상태가 없으므로 별도 hidden Badge나 관리자 상태 변경 UI를 만들지 않는다. 작성자 메뉴는 각 Review의 user ID로 판단한다.

### 17.7 목록 공통 UX

```text
MemberSubNavigation
→ PageHeader + Count
→ 카드 목록
→ Pagination
```

빈 상태는 해당 탐색 Route로 이동하는 CTA를 제공한다.

### 17.8 저장 해제와 Undo

도서관·책·프로그램:

```text
DELETE 성공
→ 목록에서 제거
→ “저장을 해제했어요. 되돌리기” Toast
→ 되돌리기 클릭
→ 대응 POST 저장 Endpoint
```

좋아요 후기:

```text
DELETE like
→ 목록에서 제거
→ 되돌리기
→ POST like
```

Undo 실패 시 목록을 재조회한다.

### 17.9 제외 기능

- 프로필 인사말
- 대표 선호 문장
- 4축 성향
- 상위 태그
- 관심 분야·자주 찾는 지역
- 활동 Count Dashboard
- memo 편집

## 18. 프로필·선호 설정 명세

### 18.1 내 정보 — `FR-PROFILE-VIEW`

| 항목 | 명세 |
|---|---|
| Route | `/profile` |
| API | `GET /users/me/` |

표시:

- email
- nickname
- 닉네임 수정
- 선호 설정 이동
- 나의 나들이 이동

프로필 이미지와 자기소개는 표시·업로드하지 않는다. 시각적 Avatar가 필요하면 nickname 또는 email 앞부분을 로컬 표현으로 사용한다.

### 18.2 내 정보 수정 — `FR-PROFILE-EDIT`

| 항목 | 명세 |
|---|---|
| Route | `/profile/edit` |
| API | `PATCH /users/me/` |

v2.0 편집 field:

- nickname

성공 시 `authStore.user`를 응답으로 교체한다. email 수정은 현재 계약에 명시되지 않았으므로 read-only다.

### 18.3 선호 설정 — `FR-PREFERENCE-SETTINGS`

| 항목 | 명세 |
|---|---|
| Route | `/profile/preferences` |
| 옵션 | `GET /preferences/options/` |
| 현재 값 | `GET /users/me/preferences/` |
| 저장 | `PUT /users/me/preferences/` |

섹션:

1. 방문 목적
2. 선호 지역
3. 선호 시설 태그

옵션을 프론트에 하드코딩하지 않고 서버 응답의 code·label·display_order를 사용한다.

### 18.4 전체 교체 저장

```json
{
  "purpose_codes": ["study", "book", "program"],
  "regions": [
    { "sido": "부산광역시", "sigungu": "해운대구" }
  ],
  "tag_codes": ["facility_parking", "facility_wifi"]
}
```

- 중복 선택은 UI에서 방지한다.
- 빈 배열은 해당 영역 전체 비활성화 의사로 전송할 수 있다.
- 없는 code·region에 대한 400을 각 그룹에 연결한다.
- 현재 위치 좌표는 Payload에 넣지 않는다.

### 18.5 저장 후 처리

- 응답으로 현재 선호 상태를 교체한다.
- 홈 캐시를 무효화한다.
- “선호 설정을 저장했어요.” Toast를 표시한다.
- 자동으로 다른 페이지의 Form을 제출하지 않는다.

### 18.6 변경사항 보호

선택이 바뀐 상태에서 Route를 이탈하면 확인한다. 저장 실패 시 사용자의 선택을 유지한다.

## 19. 시스템 페이지 명세

### 19.1 404

- 존재하지 않는 Route 또는 Resource
- “요청한 정보를 찾을 수 없습니다.”
- 홈·목록·이전 페이지 CTA

### 19.2 403

- 로그인했지만 작성자 권한 등이 없음
- “이 페이지에 접근할 수 없어요.”
- 재로그인으로 해결되지 않는 권한 문제임을 안내

### 19.3 서비스 오류

- 반복되는 5xx 또는 앱 초기화 실패
- 다시 시도·홈 이동
- Stack Trace 노출 금지

### 19.4 오프라인

- 진행 중 입력을 유지한다.
- Mutation을 자동 Queue하지 않는다.
- 캐시된 정보는 이전 정보임을 안내한다.

## 20. 반응형 웹 명세

### 20.1 Breakpoint

Bootstrap 5.3 기본값을 사용한다.

| 구간 | 폭 |
|---|---|
| xs | `<576px` |
| sm | `≥576px` |
| md | `≥768px` |
| lg | `≥992px` |
| xl | `≥1200px` |
| xxl | `≥1400px` |

### 20.2 Layout

- 기본 `container`
- 상세 최대 폭 약 1200px
- Form 640~720px
- 모바일 좌우 여백 16px 이상

### 20.3 Card Grid

| 카드 | xs | md | lg 이상 |
|---|---:|---:|---:|
| 도서관 | 1 | 2 | 3~4 |
| 책 | 1~2 | 3 | 4~6 |
| 프로그램 | 1 | 2 | 3 |
| 후기 | 1 | 1~2 | 2~3 |

프로그램은 이미지가 없으므로 텍스트 높이를 균일하게 제한하고 제목은 2~3줄까지 허용한다.

### 20.4 모바일 필터

- 필터를 기본 노출하지 않는다.
- Drawer 또는 Bottom Sheet에서 draft 상태로 편집한다.
- “결과 보기”에서 URL Query에 반영한다.
- 적용된 Filter 수를 버튼에 표시한다.

### 20.5 상세 Hero·지도

- 데스크톱: 이미지·요약 2열
- 모바일: 이미지 위, 정보 아래
- 지도 높이 240~320px
- 주소·길찾기 링크를 항상 지도 밖에도 제공

### 20.6 터치

- 주요 터치 영역 최소 44×44px
- 인접 Icon Button 8px 이상
- 저장·좋아요가 카드 Link와 겹치지 않음
- 하단 Navigation Safe Area 확보

### 20.7 모바일 하단 Navigation

홈, 도서관, 책, 프로그램, 커뮤니티 다섯 탭을 사용한다. 아이콘과 Label을 함께 표시하고 현재 탭에 `aria-current="page"`를 적용한다.

## 21. 웹 접근성 명세

### 21.1 기본 기준

WCAG 2.1 AA 수준을 목표로 한다.

- Semantic HTML
- Keyboard 전체 사용
- 명확한 Focus
- 색상 대비
- 상태 변화 Live Region

### 21.2 페이지·Form

- `header`, `nav`, `main`, `footer` Landmark
- Route 변경 후 H1 Focus
- 모든 입력에 시각적 Label
- Field Error를 `aria-describedby`로 연결
- Dialog·Drawer Focus Trap과 Trigger 복귀

### 21.3 카드·액션

- 카드 Link와 저장·좋아요 Button에 각각 Focus 가능
- Button 상태 Label: “저장하기”, “저장됨”, “상태 확인 중”
- 결과 수 변경을 polite Live Region으로 안내

### 21.4 이미지·지도

- 책 표지: “{도서명} 표지”
- fallback 도서관 이미지는 장식 또는 “기본 이미지”로 처리
- 출처 Overlay는 Keyboard로 열고 닫을 수 있음
- Kakao 지도만으로 위치 정보를 전달하지 않고 주소·외부 링크를 함께 제공
- 지도 조작 영역이 Focus를 가두지 않음

### 21.5 모션

`prefers-reduced-motion`에서 Drawer, Skeleton Shimmer, Scroll Animation을 축소한다.

## 22. 보안·개인정보 명세

### 22.1 인증 정보

- Access Token은 Pinia 메모리에만 저장한다.
- Refresh Token은 HttpOnly Cookie이며 JavaScript로 읽지 않는다.
- 모든 Axios 요청은 `withCredentials=true`.
- Refresh 실패·로그아웃 시 모든 사용자 Store와 초안을 제거한다.
- Redirect는 내부 경로만 허용한다.

### 22.2 API Key

- Vue에는 Kakao JavaScript Key만 둔다.
- Kakao 허용 도메인을 제한한다.
- 정보나루·GMS·공공데이터 Key는 Django에서만 사용한다.
- `.env`는 Git 제외, `.env.example`에는 빈 이름만 둔다.

### 22.3 XSS·외부 URL

- 후기·책·프로그램 문자열은 Plain Text로 출력한다.
- `v-html` 금지.
- 외부 URL은 `http`, `https`만 허용한다.
- 새 탭 Link에 `noopener noreferrer`.

### 22.4 위치

- 사용자 동의 후 nearby 요청에만 사용한다.
- Web Storage·로그·Route Query에 정확한 좌표를 저장하지 않는다.
- Kakao 길찾기 출발지는 서비스가 수집하지 않는다.

### 22.5 후기 데이터

- 미제출 후기 본문을 외부 오류 로그에 남기지 않는다.
- v2.0은 후기 이미지 File을 선택·저장·전송하지 않는다.

### 22.6 프론트 로그 제외 값

- 비밀번호
- Access·Refresh Token
- 정확한 위치
- 미제출 후기 본문
- API Key

## 23. 성능·사용자 경험 명세

### 23.1 Lazy Loading

모든 Page Component는 동적 import를 사용한다. Kakao SDK는 유효 좌표가 있는 상세에서만 동적 로드한다.

### 23.2 이미지

- 목록 이미지 `loading="lazy"`, `decoding="async"`
- 책 표지 2:3, 도서관 16:9 Aspect Ratio
- `thumbnail.url` 우선
- 이미지 오류의 무한 fallback loop 방지

### 23.3 요청 최적화

- 검색 Query 변경 시 이전 요청 취소
- 동일 상세 GET deduplicate
- Home은 `/home/` 한 번 호출
- interaction hydration은 Resource별 최초 필요 시 수행
- 페이지 순회 시 `next` URL 중복을 방지
- 후기 상세 hover prefetch 금지

### 23.4 느린 Network

- 300ms 이하는 Spinner 지연 가능
- 1초 이상 Skeleton
- 10초 이상 지연 안내
- Timeout 후 명시적 재시도

### 23.5 목표

- LCP 2.5초 이내 목표
- CLS 0.1 이하 목표
- 저장·좋아요는 100ms 이내 시각적 Feedback
- 20개 수준 목록에서 Virtual Scroll 사용하지 않음

## 24. 테스트 명세

### 24.1 테스트 계층

| 계층 | 대상 | 도구 |
|---|---|---|
| Unit | Query, Formatter, Validator, Kakao Utility | Vitest |
| Store | API Action, Rollback, Hydration | Vitest |
| Component | Card, Dialog, Form, Filter | Vue Test Utils |
| Contract Mock | 실제 DTO와 Status Code | MSW |
| E2E | 핵심 사용자 흐름 | Playwright |
| Accessibility | Keyboard·axe | axe-core·수동 |

### 24.2 필수 Unit Test

- `/auth/token/refresh/` single-flight와 1회 재시도
- Refresh 실패 시 전체 Store 초기화
- 안전한 Redirect 검증
- DRF Pagination과 외부 책 Pagination 분리
- 도서관 Query가 지원 field만 직렬화하는지
- ISBN13 저장 식별자 유지
- `loan_available=null` 표시
- `matched=false` 내부 Link 금지
- 후기 JSON Payload와 1~200자·태그 1~5개 검증
- POST·DELETE Save/Like Method
- 204 body 미파싱
- 선호 code·지역 객체 Payload
- interaction 목록 Pagination 순회와 Set 생성
- Kakao 좌표·길찾기 URL·Loader 중복 방지

### 24.3 필수 Component Test

- `SaveButton`: guest, unknown, saved, unsaved, rollback
- `LikeButton`: unknown, liked, unliked, count 하한
- `LibraryCard`: 운영·태그 field 미생성
- `ExternalLibraryCard`: matched false에서 상세 Link 없음
- `ProgramCard`: 이미지 없이 정상 Layout
- `ReviewForm`: JSON, 이미지 Input 없음, 글자·태그 제한
- `PreferenceForm`: Option 응답 기반, 전체 교체 Payload
- `KakaoMapPanel`: 성공·좌표 없음·Key 없음·SDK 실패
- `FilterDrawer`, `PaginationBar`, `EmptyState`, `ErrorState`

### 24.4 E2E 시나리오

#### E2E-01 인증

```text
회원가입 email·nickname·password
→ Access와 User 저장
→ 선호 온보딩
→ 새로고침
→ Refresh Cookie로 세션 복원
```

#### E2E-02 로그인 후 저장 복구

```text
비회원 도서관 저장
→ 로그인
→ Redirect 복귀
→ POST 저장
→ 나의 나들이 목록 확인
```

#### E2E-03 홈

```text
GET /home/
→ 오늘 추천
→ 개인 추천 available 분기
→ 5개 테마
→ nearby에서만 위치 요청
```

#### E2E-04 도서관

```text
q·sigungu·library_type 적용
→ Query 복원
→ 상세
→ 시설 true만 표시
→ Kakao 지도
```

#### E2E-05 책

```text
외부 검색
→ 상세
→ 소장 도서관
→ matched true 내부 상세
→ matched false 외부 카드
→ ISBN 저장
```

#### E2E-06 정보나루 503

```text
책 검색 503
→ 책 화면 유지
→ 오류 안내와 재시도
→ 다른 Navigation 사용 가능
```

#### E2E-07 프로그램

```text
필터
→ 프로그램 상세
→ 도서관 상세
→ 원문 새 탭
→ 내부 신청 CTA 없음
```

#### E2E-08 후기 작성

```text
로그인
→ 후기 작성
→ 본문·태그·관련 책·프로그램
→ JSON POST
→ 상세 이동
→ 이미지 Upload UI 없음
```

#### E2E-09 후기 권한

```text
타인 후기 수정 Route
→ 서버 403
→ 권한 화면
```

#### E2E-10 나의 나들이

```text
/my-outings
→ 저장 도서관 Redirect
→ 다섯 Tab 탐색
→ 저장 해제
→ POST Undo
```

#### E2E-11 선호

```text
Options 조회
→ purpose code·region object·tag code 선택
→ PUT 전체 교체
→ Home 재조회
```

#### E2E-12 Interaction Hydration

```text
로그인 후 도서관 목록
→ 저장 목록 Pagination 순회
→ SaveButton unknown에서 saved·unsaved로 확정
```

### 24.5 Mock Fixture

- Home personal available true·false
- fallback·실제 이미지 도서관
- facility profile null·부분 null·true·false
- opening_hours 빈 배열
- 책 검색 정상·0건·503
- holdings matched true·false·loan null
- 프로그램 0건·정상·알 수 없는 status code
- 후기 0건·관련 관계 존재
- My Outings 중첩 relation
- 401 Refresh 성공·실패
- Kakao Key 누락·좌표 오류·SDK 실패

## 25. 구현 우선순위와 단계

### 25.1 우선순위

| 우선순위 | 범위 |
|---|---|
| P0 | API Client·JWT·Router·공통 상태 |
| P0 | Home·도서관 목록·상세·Kakao 지도 |
| P0 | 책 검색·상세·소장 도서관 |
| P0 | 프로그램 목록·상세 |
| P0 | 저장·나의 나들이 목록·interaction hydration |
| P0 | 후기 목록·상세·좋아요 |
| P0 계약 필요 | 후기 작성용 태그 옵션 |
| P1 | 후기 작성·수정·삭제, 선호 설정, 프로필 nickname |
| P1 | 접근성·반응형·E2E |
| P2 | Undo 고도화, 공유, 추가 Animation |

### 25.2 권장 구현 순서

#### Phase 1. 기반

1. Vite·Router·Pinia·Axios
2. 공통 Layout·System Page
3. 실제 DTO·Error Normalizer
4. JWT Refresh Interceptor·Guard
5. Skeleton·Empty·Error·Dialog·Toast

#### Phase 2. 공개 탐색

1. Home `/home/`
2. 도서관 목록·상세
3. Kakao Map
4. 책 외부 검색·상세·Holdings
5. 프로그램 목록·상세

#### Phase 3. 회원 상태

1. SaveButton·LikeButton·AuthGate
2. My Outings 다섯 목록
3. interaction hydration
4. 로그인 후 PendingIntent 복구

#### Phase 4. 커뮤니티·선호

1. 후기 목록·상세·좋아요
2. 후기 태그 계약 해결
3. 후기 JSON 작성·수정·삭제
4. 선호 옵션·전체 교체
5. 프로필 nickname

#### Phase 5. 품질

1. 반응형
2. 접근성
3. Unit·Contract·E2E
4. Production Build·배포 점검

## 26. 완료 기준

### 26.1 기능 완료

- 모든 Route가 직접 URL·새로고침에서 동작한다.
- 실제 Endpoint·Method와 일치한다.
- 이메일 로그인·회원가입이 동작한다.
- Access 만료 시 `/auth/token/refresh/` 후 원 요청을 재시도한다.
- Refresh 실패·로그아웃 시 전체 Store가 초기화된다.
- Home은 `/home/` 단일 응답을 사용한다.
- 도서관 목록은 지원 Query만 전송한다.
- ISBN13으로 책을 저장한다.
- Holdings matched true·false를 분리한다.
- 후기 JSON 작성·POST 좋아요가 동작한다.
- 나의 나들이는 다섯 목록으로 동작한다.
- 선호는 code·지역 객체 전체 교체 PUT을 사용한다.
- Kakao 지도와 fallback이 동작한다.

### 26.2 데이터 정확성

- 응답에 없는 운영 상태·태그·저장 상태를 생성하지 않는다.
- Facility null·false·profile 부재를 구분한다.
- `loan_available=null`을 대출 불가로 표시하지 않는다.
- matched false를 내부 도서관으로 연결하지 않는다.
- 프로그램 원문을 내부 신청으로 표현하지 않는다.
- 로컬 책 목록을 인기 도서로 표현하지 않는다.
- 프로필에 이미지·자기소개를 임의 추가하지 않는다.

### 26.3 품질 완료

- 360px에서 가로 Scroll 없이 핵심 흐름 사용 가능
- Keyboard로 핵심 흐름 완료
- Console Error 없음
- Kakao 외 비밀 API Key가 Bundle·Network·Log에 없음
- Production Build 성공
- 핵심 Unit·Contract·E2E 통과

## 27. 확정 정책과 계약 공백

### 27.1 v2.0 확정 정책

- 프론트 전달용 API 계약 문서가 Endpoint·Method·DTO의 최상위 기준이다.
- Base URL은 `/api/v1`이다.
- Access Token은 Memory, Refresh Token은 HttpOnly Cookie다.
- 인증 식별자는 이메일이며 username 필드는 사용하지 않는다.
- Refresh Endpoint는 `/auth/token/refresh/`다.
- 로그인은 email과 password를 사용한다.
- Home은 `/home/` 단일 호출이다.
- 도서관 목록 활성 Query는 `q`, `sigungu`, `library_type`, Pagination이다.
- 도서관 운영 상태와 고급 필터는 보류한다.
- 책 저장 식별자는 ISBN13이다.
- 후기 작성·수정은 JSON이고 이미지 업로드는 보류한다.
- 후기 좋아요는 POST·DELETE다.
- 선호는 code와 지역 객체로 전체 교체한다.
- 나의 나들이는 분석 Dashboard가 아니라 다섯 목록이다.
- 프로필은 users/me의 email·nickname을 사용하고 nickname만 수정한다.
- 저장·좋아요 초기 상태는 interaction hydration으로 보완한다.
- Kakao 지도 변수는 `VITE_KAKAO_MAP_JAVASCRIPT_KEY`다.
- Git 협업 규칙은 본 문서 범위가 아니다.

### 27.2 P0 계약 공백

#### 후기 선택 가능 태그

후기 작성은 `tag_codes` 1~5개를 요구하지만 옵션 공급 API가 없다.

필요한 해결 중 하나:

1. 후기 선택 가능 태그 Endpoint 추가
2. `/preferences/options/`와 분리된 `review_tags` 응답 추가
3. 백엔드가 관리하는 버전 고정 seed 파일을 프론트와 공유

시설 선호 태그를 후기 태그로 재사용하면 안 된다.

#### 저장·좋아요 상태

현재 목록·상세 응답에 `is_saved`, `is_liked`가 없다. v2.0은 interaction hydration을 사용한다. 장기적으로 serializer 필드 추가가 가능하지만 v2.0의 Backend 변경 전제는 아니다.

### 27.3 P1 계약 공백

1. `opening_hours`, `closure_rules` 내부 객체 구조
2. 프로그램 `application_status`, `operation_status` 전체 code 목록
3. 외부 검색 ISBN이 책 상세 Endpoint에서 항상 조회 가능한지
4. 후기 `tags`, `images`, `related_books`, `related_programs` 상세 객체 구조
5. `sigungu`, `library_type`, 프로그램 필터의 다중 Query 지원 여부
6. 후기 수정에서 `book_ids`, `program_ids` 전체 교체 지원 여부
7. 나의 나들이 목록 `page_size` 최대값

### 27.4 명시적 보류

- 후기 hidden UI
- 프로필 이미지·bio
- 후기 이미지 업로드
- 통합 나의 나들이 Dashboard
- 행동 기반 개인화 분석
- 인기 도서
- 정밀 운영 상태
- 고급 도서관 필터

## 28. API–화면 매핑

| 화면·기능 | Method | Endpoint |
|---|---|---|
| 회원가입 | POST | `/auth/signup/` |
| 로그인 | POST | `/auth/login/` |
| Access 갱신 | POST | `/auth/token/refresh/` |
| 로그아웃 | POST | `/auth/logout/` |
| 내 정보 | GET·PATCH | `/users/me/` |
| Home | GET | `/home/` |
| 도서관 목록 | GET | `/libraries/` |
| 도서관 상세 | GET | `/libraries/{library_id}/` |
| 도서관 저장 | POST·DELETE | `/libraries/{library_id}/save/` |
| 로컬 책 목록 | GET | `/books/` |
| 책 검색 | GET | `/books/search/` |
| 책 상세 | GET | `/books/{isbn13}/` |
| 소장 도서관 | GET | `/books/{isbn13}/libraries/` |
| 책 저장 | POST·DELETE | `/books/{isbn13}/save/` |
| 프로그램 목록 | GET | `/programs/` |
| 프로그램 상세 | GET | `/programs/{program_id}/` |
| 프로그램 저장 | POST·DELETE | `/programs/{program_id}/save/` |
| 후기 목록·작성 | GET·POST | `/reviews/` |
| 후기 상세·수정·삭제 | GET·PATCH·DELETE | `/reviews/{review_id}/` |
| 후기 좋아요 | POST·DELETE | `/reviews/{review_id}/like/` |
| 선호 옵션 | GET | `/preferences/options/` |
| 내 선호 | GET·PUT | `/users/me/preferences/` |
| 저장 도서관 | GET | `/my-outings/libraries/` |
| 저장 책 | GET | `/my-outings/books/` |
| 저장 프로그램 | GET | `/my-outings/programs/` |
| 내 후기 | GET | `/my-outings/reviews/` |
| 좋아요 후기 | GET | `/my-outings/liked-reviews/` |

# 부록 A. Query 사전

## A.1 도서관

| Query | 형식 | UI |
|---|---|---|
| `q` | string | 검색어 |
| `sigungu` | string | 구·군 단일 선택 |
| `library_type` | string | 유형 단일 선택 |
| `page` | integer | 페이지 |
| `page_size` | integer | 페이지 크기 |

## A.2 로컬 책 목록

| Query | 형식 |
|---|---|
| `q` | string |
| `page` | integer |
| `page_size` | integer |

## A.3 외부 책 검색

| Query | 형식 |
|---|---|
| `search_type` | `title|author|isbn|keyword|publisher` |
| `q` | string |
| `title`, `author`, `isbn13`, `keyword`, `publisher` | 선택 직접 field |
| `page` | integer |
| `page_size` | integer |

## A.4 프로그램

| Query | 형식 |
|---|---|
| `q` | string |
| `library_id` | integer |
| `sigungu` | string |
| `category` | string |
| `target` | string |
| `application_status` | string |
| `operation_status` | string |
| `page`, `page_size` | integer |

## A.5 후기

| Query | 형식 |
|---|---|
| `q` | string |
| `library_id` | integer |
| `tag` | string code |
| `user_id` | integer |
| `ordering` | `-created_at|-view_count|-like_count` |
| `page`, `page_size` | integer |

# 부록 B. 표시 상태 사전

## B.1 저장·좋아요

| 상태 | 표시 |
|---|---|
| `unknown` | 상태 확인 중, false로 단정 금지 |
| `saved`·`liked` | 저장됨·좋아요함 |
| `unsaved`·`unliked` | 저장하기·좋아요 |

## B.2 시설

| 데이터 | 표시 |
|---|---|
| field `true` | 시설 Chip |
| field `false` | 기본 미표시 |
| field `null` | 미확인, 기본 미표시 |
| profile `null` | 확인된 시설 정보 없음 안내 |

## B.3 소장 도서관

| 상태 | 표시 |
|---|---|
| `matched=true` | 내부 도서관 링크 |
| `matched=false` | 외부 도서관 카드 |
| `loan_available=true` | 대출 가능 |
| `loan_available=false` | 대출 불가 |
| `loan_available=null` | 대출 상태 미제공 |

## B.4 프로그램

전체 code 목록이 확정되기 전 raw code에 대응하지 못하면 “상태 확인 필요”로 표시한다. `category_display`, `target_display`는 서버 문구를 그대로 사용한다.

# 부록 C. Mutation 후 갱신

| Mutation | 즉시 수정 | 무효화·재조회 |
|---|---|---|
| 도서관 저장·해제 | `savedLibraryIds` | 나의 나들이 도서관 |
| 책 저장·해제 | `savedBookIsbns` | 나의 나들이 책 |
| 프로그램 저장·해제 | `savedProgramIds` | 나의 나들이 프로그램 |
| 후기 좋아요·해제 | `likedReviewIds`, `like_count` | 후기 목록·상세, 좋아요 후기 |
| 후기 생성 | 생성 상세로 이동 | 커뮤니티, 도서관 관련 후기, 내 후기 |
| 후기 수정 | 현재 상세 교체 | 커뮤니티, 내 후기 |
| 후기 삭제 | 목록 제거 | 커뮤니티, 내 후기, 좋아요 후기 |
| 선호 PUT | 현재 선호 교체 | Home |
| nickname PATCH | `authStore.user` 교체 | Header·프로필 |

# 부록 D. PendingIntent

```ts
type PendingIntent = {
  type: 'save-library'|'save-book'|'save-program'|'like-review'
  resourceId: number|string
  redirect: string
  createdAt: string
}
```

- 하나만 `sessionStorage`에 저장한다.
- 30분 후 폐기한다.
- 저장·좋아요만 사용한다.
- 후기 작성·수정·선호 설정은 Redirect만 사용한다.
- 로그인 후 interaction 상태가 이미 목표 상태이면 POST를 보내지 않는다.

# 부록 E. 공통 문구

| 상황 | 문구 |
|---|---|
| 저장 | 저장했어요. |
| 저장 해제 | 저장을 해제했어요. |
| 로그인 필요 | 로그인하면 원래 화면으로 돌아올 수 있어요. |
| 위치 설명 | 가까운 도서관을 찾기 위해 현재 위치를 사용합니다. 위치는 계정에 저장하지 않아요. |
| 지도 실패 | 지도를 불러오지 못했어요. 주소와 카카오맵 링크를 이용해 주세요. |
| 시설 미수집 | 확인된 시설 정보가 아직 없습니다. |
| 대출 상태 null | 대출 상태 미제공 |
| 프로그램 원문 | 원문에서 신청 정보 확인 |
| 후기 삭제 | 이 후기를 삭제할까요? 삭제한 후기는 되돌릴 수 없습니다. |
| 작성 이탈 | 작성 중인 내용이 사라질 수 있습니다. 나갈까요? |
| 정보나루 503 | 책 검색 서비스를 사용할 수 없어요. 잠시 후 다시 시도해 주세요. |

# 부록 F. 화면별 완료 체크리스트

## 인증

- [ ] 이메일 로그인
- [ ] signup 응답으로 자동 로그인 상태 구성
- [ ] `/auth/token/refresh/` single-flight
- [ ] Refresh 실패·로그아웃 전체 Store Reset

## 홈

- [ ] `/home/` 한 번 호출
- [ ] 개인 추천 available 분기
- [ ] 테마 5개
- [ ] nearby에서만 위치 요청

## 도서관

- [ ] q·sigungu·library_type만 요청
- [ ] 운영 상태 UI 없음
- [ ] 시설 true만 표시
- [ ] Kakao Map fallback

## 책

- [ ] 인기 도서 표현 없음
- [ ] ISBN13 저장
- [ ] matched true·false 분리
- [ ] loan null 분리
- [ ] 503 부분 실패

## 프로그램

- [ ] 이미지 없는 Card
- [ ] category_display·target_display 사용
- [ ] 내부 신청 CTA 없음

## 커뮤니티

- [ ] 후기 JSON 작성·수정
- [ ] 이미지 Uploader 없음
- [ ] POST·DELETE 좋아요
- [ ] 작성자 권한·204 삭제
- [ ] 후기 태그 옵션 계약 확인

## 나의 나들이

- [ ] `/my-outings`가 저장 도서관으로 Redirect
- [ ] 다섯 목록
- [ ] 중첩 relation DTO 사용
- [ ] Undo는 POST 재생성
- [ ] 분석 Dashboard 없음

## 프로필·선호

- [ ] users/me 조회
- [ ] nickname PATCH
- [ ] code·지역 객체 PUT
- [ ] 프로필 이미지·bio 없음

# 부록 G. 참고 문서

1. `도서관 나들이 프론트 전달용 API 계약 문서 v1.1`
2. `library_outing_Django_spec_v3.md`
3. `library_outing_ERD_v3.md`
4. `도서관 나들이 주요 페이지 구조.txt`
5. `LibraryBigdata_API_Manual.pdf`
6. `데이터셋 정보.pdf`
7. `GMS 사용법.pdf`
8. 디자인 참고 시안 7종
9. Kakao Map JavaScript SDK 사용 계약

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| 1.0 | 2026-06-23 | Vue SPA 전체 Route·상태·페이지 명세 최초 작성 |
| 1.1 | 2026-06-24 | JWT·HttpOnly Refresh, Kakao 지도, 모바일 Navigation, 디자인 정책 확정 |
| 1.2 | 2026-06-24 | 백엔드 계약 보존형 UI/UX 보강 |
| 1.3 | 2026-06-24 | Kakao SDK Loader·환경변수·Fallback·보안·테스트 구체화 |
| 2.0 | 2026-06-24 | 프론트 전달용 API 계약 v1과 실제 Endpoint·Method·DTO 동기화, 미지원 기능 분리, 후기 JSON·ISBN 저장·목록형 나의 나들이·interaction hydration 구조 확정 |


---

**문서 끝 — 도서관 나들이 Frontend 개발 명세서 v2.0**
