# 도서관 나들이 Frontend 개발 명세서 v1.1

- 문서 버전: 1.1
- 작성 기준일: 2026-06-24
- 대상 애플리케이션: Vue 3 SPA
- 연동 백엔드: Django REST API `/api/v1`
- 1차 서비스 범위: 부산광역시 MVP
- 문서 상태: 구현 기준 확정안
- 기준 문서: `library_outing_Django_spec_v3.md`, `library_outing_ERD_v3.md`, `도서관 나들이 주요 페이지 구조.txt`
- 디자인 참고: 대화에서 제공된 홈·도서관·책·프로그램·커뮤니티·나의 나들이·도서관 상세 시안

---

## 0. 문서 사용 규칙

### 0.1 목적

이 문서는 도서관 나들이 서비스의 Vue 프론트엔드를 구현하기 위한 화면, 라우팅, 상태 관리, API 연동, 사용자 상호작용, 반응형·접근성·테스트 기준을 정의한다.

프론트엔드 구현자는 이 문서를 기준으로 다음을 결정할 수 있어야 한다.

1. 어떤 URL에 어떤 화면을 배치하는가.
2. 회원과 비회원에게 무엇을 보여주고 어떤 행동을 허용하는가.
3. 각 화면이 어떤 API를 언제 호출하는가.
4. 로딩·빈 상태·오류·권한·위치 권한을 어떻게 처리하는가.
5. 공통 컴포넌트와 Pinia Store를 어떻게 분리하는가.
6. 저장·좋아요·후기 작성 후 어떤 데이터를 무효화하고 다시 조회하는가.
7. 데스크톱·태블릿·모바일에서 화면이 어떻게 변하는가.

### 0.2 문서 우선순위

문서 간 내용이 충돌할 때 다음 순서로 판단한다.

1. API, 데이터 의미, 권한, 상태값: `library_outing_Django_spec_v3.md`
2. 모델 관계와 null 의미: `library_outing_ERD_v3.md`
3. 화면 구성과 사용자 경험: 본 Frontend 명세서
4. 초기 페이지 아이디어: `도서관 나들이 주요 페이지 구조.txt`, 메인페이지 서술 문서
5. 외부 API 원천 필드: 정보나루·데이터셋 문서

프론트에서 필요한 필드가 API 명세에 없으면 임의로 추론해 구현하지 않고 **계약 미확정 항목**으로 등록한다.

### 0.3 요구 수준 표기

| 표기 | 의미 |
|---|---|
| MUST | v1.1 완료를 위해 반드시 구현 |
| SHOULD | 구현을 권장하며 일정상 어려우면 이슈로 기록 |
| MAY | 선택 기능 또는 후속 개선 |
| TBD | 백엔드·디자인·팀 합의가 필요한 미결정 사항 |

### 0.4 화면 명세 공통 형식

각 화면은 다음 항목을 기준으로 구현한다.

- 화면 ID와 Route
- 접근 권한
- 진입·이탈 경로
- 사용 API
- 레이아웃과 구성 요소
- 사용자 행동
- 회원·비회원 분기
- 로딩·빈 상태·오류 상태
- 반응형 동작
- 접근성 기준
- 완료 조건

---

## 1. 프로젝트 개요

### 1.1 서비스 정의

도서관 나들이는 부산 지역의 도서관, 책, 문화 프로그램, 이용 후기를 한곳에서 탐색하고 사용자의 저장·후기·선호 데이터를 바탕으로 다음 방문 후보를 추천하는 서비스다.

핵심 사용 경험은 다음과 같다.

```text
도서관을 발견한다
→ 운영·시설·위치·후기를 확인한다
→ 책 또는 프로그램과 연결해 방문 목적을 만든다
→ 관심 항목을 저장하거나 후기를 남긴다
→ 활동을 바탕으로 더 적합한 도서관을 추천받는다
```

### 1.2 v1.1 핵심 기능

1. 모든 사용자에게 제공하는 오늘의 추천 도서관
2. 회원의 직접 선호와 행동 데이터를 반영한 개인화 추천
3. 도서관 검색·필터·상세·위치 정보
4. 도서 검색·상세·부산 소장 도서관 조회
5. 문화 프로그램 검색·상세·원문 연결
6. 도서관 후기 작성·조회·수정·삭제·좋아요
7. 도서관·책·프로그램 저장
8. 나의 나들이 활동 요약과 4축 성향 분석
9. 프로필과 선호 목적·지역·시설 태그 설정
10. 공식 이미지 출처·라이선스 오버레이

### 1.3 v1.1 제외 범위

다음 기능은 프론트 UI를 제공하지 않는다.

- 서비스 내부 프로그램 신청·예약·결제
- 실시간 열람실 잔여 좌석
- 방문 체크인과 참여 이력
- 회원 간 팔로우·쪽지
- 후기 별점과 별도 제목
- 후기 저장 기능
- AI가 직접 운영 여부·시설 사실·추천 순위를 결정하는 기능
- 전국 지역 전환 UI
- 별도 SPA 관리자 화면 — 후기 숨김 처리는 Django admin에서 수행

### 1.4 프로젝트 요구사항 대응

| 요구사항 | 프론트 대응 |
|---|---|
| F1301 사용자 추천 | 홈 오늘의 추천, 개인화 추천, 테마 추천, 비슷한 도서관 |
| F1302 API 활용 | 책 검색·상세·인기·소장 도서관은 Django 경유, 위치 지도는 Kakao Map JavaScript SDK 사용 |
| F1303 커뮤니티 | 후기 목록·상세·작성·수정·삭제·좋아요 |
| F1304 RESTful 원칙 | 자원별 GET·POST·PATCH·PUT·DELETE 계약 준수 |
| NF1302 API Key 관리 | 정보나루·공공데이터·GMS 비밀키는 Django에서만 사용하고, Kakao JavaScript Key는 허용 도메인을 제한한 공개키로 사용 |
| NF1304 페이지 다양성 | 공개·회원 전용을 포함한 다수의 Route 제공 |

---

## 2. 사용자와 권한

### 2.1 사용자 유형

| 사용자 유형 | 설명 |
|---|---|
| 비회원 | 공개 콘텐츠를 탐색하지만 개인 데이터를 생성할 수 없는 사용자 |
| 신규 회원 | 가입 직후 선호와 행동 데이터가 부족한 사용자 |
| 기존 회원 | 선호 또는 저장·후기·좋아요 데이터가 있는 사용자 |
| 후기 작성자 | 특정 공개 후기의 수정·삭제 권한을 가진 회원 |
| 관리자 | Django admin에서 후기 공개 상태 등을 관리하는 운영자. 별도 SPA 관리자 UI는 제공하지 않음 |

### 2.2 기능 권한표

| 기능 | 비회원 | 회원 | 추가 조건 |
|---|---:|---:|---|
| 홈·도서관·책·프로그램·공개 후기 조회 | 가능 | 가능 | 해당 없음 |
| 위치 기반 가까운 도서관 | 위치 동의 시 가능 | 위치 동의 시 가능 | 좌표는 요청 중에만 사용 |
| 도서관·책·프로그램 저장 | 로그인 유도 | 가능 | 해당 없음 |
| 후기 좋아요 | 로그인 유도 | 가능 | `visible` 후기만 |
| 후기 작성 | 로그인 전 화면 접근 차단 | 가능 | 자동 제출 금지 |
| 후기 수정 | 로그인 전 화면 접근 차단 | 본인 공개 후기만 | 작성자 확인 필요, `hidden` 후기 불가 |
| 후기 삭제 | 로그인 전 화면 접근 차단 | 본인 공개 후기만 | 서버 권한이 최종 기준 |
| 숨김 후기 조회 | 불가 | 본인 작성 후기만 읽기 전용 | “공개되지 않음” 배지 표시 |
| 나의 나들이 | 로그인 전 화면 접근 차단 | 가능 | 해당 없음 |
| 프로필·선호 설정 | 로그인 전 화면 접근 차단 | 가능 | 자동 저장 금지 |
| 개인화 추천 | 미노출 | 유효 신호가 있을 때 노출 | 해당 없음 |

### 2.3 인증이 필요한 행동과 페이지

인증 요구는 **행동 게이트**와 **Route 게이트**로 구분한다.

#### 공개 화면의 로그인 필요 행동

비회원이 공개 화면에서 저장 또는 좋아요를 누르면 현재 맥락을 유지한 채 로그인으로 전환한다.

```text
저장·좋아요 클릭
→ LoginRequiredDialog
→ pending intent 저장
→ /auth/login?redirect={현재 내부 경로}
→ 로그인 성공
→ redirect 대상 복귀
→ 목표 상태가 아직 아니면 멱등 요청 1회 자동 실행
```

자동 재실행 대상은 다음 네 가지로 제한한다.

- 도서관 저장
- 책 저장
- 프로그램 저장
- 후기 좋아요

#### 인증 전 접근을 차단하는 페이지

다음 페이지는 비회원 상태에서 컴포넌트를 mount하거나 API를 호출하지 않는다.

- 후기 작성 `/reviews/new`
- 후기 수정 `/reviews/:id/edit`
- 나의 나들이 `/my-outings/**`
- 프로필 `/profile/**`
- 선호 설정 `/profile/preferences`
- 초기 선호 설정 `/onboarding/preferences`

```text
보호 Route 직접 접근
→ Router Guard가 로그인 화면으로 이동
→ /auth/login?redirect={보호 Route}
→ 로그인 성공 후 해당 Route로 복귀
→ 필요한 추가 권한을 서버 응답으로 검증
```

후기 작성·수정과 선호 설정은 Route 복귀만 수행하며 제출·수정·저장을 자동 실행하지 않는다. 후기 수정은 로그인 후 작성자 여부를 확인하고, 작성자가 아니면 `403`으로 처리한다.

### 2.4 비회원 개인 상태값

API의 `is_saved`, `is_liked`는 비회원에게 `null` 또는 미포함일 수 있다.

프론트 규칙:

- `true`: 활성 상태
- `false`: 로그인 회원이 저장·좋아요하지 않은 상태
- `null` 또는 미포함: 비회원 또는 상태 계산 미제공
- `null`을 `false`로 변환해 “저장하지 않음”으로 해석하지 않는다.
- 버튼은 표시하되 누르면 인증 흐름을 실행한다.

### 2.5 작성자 권한

- 공개 후기의 수정·삭제 메뉴는 `review.author.id === authStore.user.id`일 때만 표시한다.
- 후기 수정 Route는 인증 이후 상세 응답으로 작성자 여부를 다시 검증한다.
- UI에서 버튼을 숨겼더라도 서버의 `403` 응답을 최종 권한 판단으로 처리한다.
- `moderation_status=hidden`인 후기는 작성자에게 읽기 전용으로만 노출하고 수정 메뉴를 표시하지 않는다.

### 2.6 숨김 후기와 운영 관리

- 후기 공개 상태 변경은 Django admin에서 수행한다.
- 공개 목록, 공개 상세, 도서관 상세 관련 후기, 추천·태그 rollup에는 `visible` 후기만 포함한다.
- 작성자 본인의 “내가 쓴 후기” 목록에는 `hidden` 후기도 포함한다.
- `hidden` 후기는 “공개되지 않음” 배지를 표시하고 수정·좋아요·공유를 비활성화한다.
- 비작성자의 hidden 후기 직접 접근은 `404` 또는 `403`으로 처리한다.
- 작성자는 hidden 후기 상세를 읽기 전용으로 볼 수 있다.

---

## 3. 정보 구조와 내비게이션

### 3.1 최상위 정보 구조

```text
도서관 나들이
├─ 홈
├─ 도서관 찾기
│  └─ 도서관 상세
├─ 책 둘러보기
│  └─ 책 상세
├─ 문화 프로그램
│  └─ 프로그램 상세
├─ 커뮤니티
│  ├─ 후기 상세
│  ├─ 후기 작성
│  └─ 후기 수정
├─ 나의 나들이
│  ├─ 저장한 도서관
│  ├─ 저장한 책
│  ├─ 저장한 프로그램
│  ├─ 좋아요한 후기
│  └─ 내가 쓴 후기
├─ 프로필
│  ├─ 프로필 수정
│  └─ 선호 설정
└─ 인증
   ├─ 로그인
   ├─ 회원가입
   └─ 초기 선호 설정
```

### 3.2 데스크톱 헤더

헤더는 첨부 시안의 정보 구조를 참고하여 로고, 최상위 메뉴, 프로필 진입점을 한 줄에 배치한다. 현재 Route는 녹색 글자 또는 녹색 underline과 `aria-current="page"`로 표시한다.

비회원:

```text
로고 | 홈 | 도서관 찾기 | 책 둘러보기 | 문화 프로그램 | 커뮤니티 | 나의 나들이 | 로그인 | 회원가입
```

회원:

```text
로고 | 홈 | 도서관 찾기 | 책 둘러보기 | 문화 프로그램 | 커뮤니티 | 나의 나들이 | 프로필 메뉴
```

프로필 메뉴:

- 내 프로필
- 나의 나들이
- 선호 설정
- 내가 쓴 후기
- 로그아웃

`나의 나들이`를 비회원이 선택하면 로그인 Route로 이동하고 안전한 `redirect`를 유지한다.

### 3.3 모바일 내비게이션

모바일은 상단의 간결한 브랜드 헤더와 하단 고정 탭 내비게이션을 사용한다.

하단 탭은 다섯 개로 고정한다.

```text
홈 | 도서관 | 책 | 프로그램 | 커뮤니티
```

- 각 탭은 아이콘과 텍스트 label을 함께 제공한다.
- 현재 탭은 녹색 강조와 `aria-current="page"`로 표시한다.
- 하단 탭은 모바일 safe area를 고려해 `padding-bottom: env(safe-area-inset-bottom)`을 적용한다.
- `나의 나들이`, 프로필, 선호 설정, 내가 쓴 후기, 로그아웃은 상단 프로필 버튼의 메뉴 또는 Drawer에 배치한다.
- 비회원의 프로필 버튼은 로그인·회원가입 메뉴를 연다.
- Filter Drawer와 프로필 메뉴는 서로 독립된 overlay로 관리하며 동시에 열지 않는다.
- 메뉴가 열리면 배경 스크롤을 잠그고 Focus trap과 닫힘 후 Focus 복귀를 제공한다.

햄버거 안에 모든 최상위 메뉴를 중복 배치하지 않는다. 하단 탭이 주요 탐색의 기준이다.

### 3.4 카드 이동 원칙

- 카드 본문 클릭: 해당 상세 Route로 이동
- 저장·좋아요 버튼: 카드 이동을 발생시키지 않음
- 도서관명 링크: 도서관 상세로 이동
- 태그 클릭: 해당 목록 화면의 필터로 이동하거나 현재 목록을 필터링
- 외부 원문: 새 탭으로 열며 외부 링크 아이콘과 접근 가능한 설명을 표시

### 3.5 뒤로 가기와 상태 복원

목록 화면의 검색·필터·정렬·페이지는 URL Query를 기준 상태로 사용한다. 상세에서 브라우저 뒤로 가기를 실행하면 이전 목록 조건과 스크롤 위치를 복원한다.

정밀 위치 좌표는 개인정보 보호를 위해 URL에 기록하지 않는다. `nearby` 목적만 URL에 남기고 좌표는 메모리 상태에서 API 요청에만 사용한다.

---

## 4. 기술 스택과 구현 원칙

### 4.1 기본 기술 스택

| 영역 | 선택 |
|---|---|
| UI Framework | Vue 3 |
| 작성 방식 | Composition API, `<script setup>` |
| Build Tool | Vite |
| Router | Vue Router 4 |
| State | Pinia |
| HTTP | Axios |
| 인증 | JWT access token + HttpOnly refresh cookie |
| 지도 | Kakao Map JavaScript SDK |
| CSS | Bootstrap 5.3 + CSS Custom Properties + scoped CSS |
| 언어 | JavaScript ES2022 |
| 타입 문서 | TypeScript 형태의 DTO 표기 또는 JSDoc |
| Unit Test | Vitest |
| Component Test | Vue Test Utils |
| API Mock | MSW 또는 Axios Mock Adapter |
| E2E | Playwright 권장 |

TypeScript를 채택해도 Route, Store, API 계약과 파일 구조는 동일하게 유지한다.

### 4.2 Vue 작성 규칙

- Options API와 Composition API를 혼용하지 않는다.
- 페이지 컴포넌트는 데이터 조합과 Route 단위 책임을 가진다.
- 재사용 UI는 `components`로 분리한다.
- API 호출은 View에서 Axios를 직접 호출하지 않고 `services` 또는 Store Action을 거친다.
- 브라우저에서 직접 호출하는 외부 서비스는 Kakao Map JavaScript SDK로 제한한다. 정보나루·공공데이터포털·GMS는 Django API를 거친다.
- 포맷·상태 계산은 `utils` 또는 `composables`로 분리한다.
- 원격 HTML을 `v-html`로 렌더링하지 않는다.
- Props는 단방향이며 자식이 부모 객체를 직접 변경하지 않는다.
- 목록 item의 `key`는 배열 index가 아니라 서버 식별자를 사용한다.

### 4.3 권장 디렉터리 구조

```text
src/
├─ app/
│  ├─ App.vue
│  ├─ router.js
│  └─ bootstrap.js
├─ assets/
│  ├─ styles/
│  │  ├─ tokens.css
│  │  ├─ base.css
│  │  ├─ utilities.css
│  │  └─ bootstrap-overrides.css
│  └─ images/
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
│  ├─ useKakaoMapScript.js
│  ├─ useOptimisticToggle.js
│  └─ useReviewDraft.js
├─ constants/
│  ├─ routes.js
│  ├─ status.js
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
│  ├─ kakaoMapLoader.js
│  ├─ referenceService.js
│  ├─ homeService.js
│  ├─ libraryService.js
│  ├─ bookService.js
│  ├─ programService.js
│  ├─ reviewService.js
│  ├─ myOutingsService.js
│  └─ profileService.js
├─ stores/
│  ├─ auth.js
│  ├─ reference.js
│  ├─ home.js
│  ├─ libraries.js
│  ├─ books.js
│  ├─ programs.js
│  ├─ community.js
│  ├─ myOutings.js
│  ├─ profile.js
│  └─ ui.js
└─ utils/
   ├─ apiError.js
   ├─ dateTime.js
   ├─ format.js
   ├─ query.js
   ├─ statusLabel.js
   └─ validators.js
```

### 4.4 이름 규칙

| 대상 | 규칙 | 예시 |
|---|---|---|
| Vue Component | PascalCase | `LibraryCard.vue` |
| Composable | `use` + PascalCase | `useGeolocation.js` |
| Store | camelCase + `Store` export | `useAuthStore` |
| Service 함수 | 동사 + 자원 | `fetchLibraryDetail` |
| Route name | kebab-case | `library-detail` |
| CSS class | kebab-case | `.library-card__meta` |
| 상수 | UPPER_SNAKE_CASE | `MAX_REVIEW_IMAGES` |

---

## 5. 환경변수와 API Client

### 5.1 Vue 환경변수

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_APP_NAME=도서관 나들이
VITE_REQUEST_TIMEOUT_MS=15000
VITE_USE_MOCK_API=false
VITE_KAKAO_MAP_APP_KEY=
```

금지 사항:

- `DATA4LIBRARY_API_KEY`
- `GMS_API_KEY`
- 공공데이터포털 인증키
- Django Secret Key
- JWT refresh token 또는 사용자 비밀번호

`VITE_` 변수는 브라우저 번들에 포함된다. `VITE_KAKAO_MAP_APP_KEY`는 JavaScript SDK용 공개키로 사용하되 Kakao Developers에서 개발·운영 도메인을 제한한다. 정보나루·공공데이터포털·GMS 비밀키는 Vue에 두지 않는다.

배포 시 프론트와 Django API는 같은 사이트의 `/api` 경로로 제공하는 방식을 우선한다. 이 구조는 credential cookie와 CORS 설정을 단순화한다.

### 5.2 Axios 인스턴스

`services/apiClient.js`는 단일 인스턴스를 제공한다.

```js
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS ?? 15000),
  withCredentials: true,
  headers: { Accept: 'application/json' },
})
```

요청 Interceptor:

- `authStore`의 메모리 access token이 있으면 `Authorization: Bearer <token>`을 추가한다.
- refresh token은 HttpOnly cookie이므로 JavaScript로 읽거나 저장하지 않는다.
- `FormData` 요청은 브라우저가 boundary를 생성하도록 `Content-Type`을 직접 지정하지 않는다.
- 로그인·refresh·logout 요청에도 `withCredentials=true`를 유지한다.
- 요청 ID를 프론트 로그에 남길 수 있도록 로컬 식별자를 생성할 수 있다.

### 5.3 JWT 갱신과 401 처리

인증 방식은 JWT로 고정한다.

```text
access token  → Pinia 메모리 상태
refresh token → HttpOnly cookie
```

401 응답 처리:

```text
보호 API가 401 반환
→ 해당 요청이 login/refresh/logout인지 확인
→ 이미 재시도한 요청인지 확인
→ 전역 refresh Promise가 없으면 POST /auth/refresh/
→ 동시 401 요청은 같은 Promise를 대기
→ refresh 성공: 새 access token 저장
→ 원 요청에 새 Authorization header를 붙여 1회 재시도
→ refresh 실패: 전체 Pinia Store 초기화
                 + 개인 sessionStorage 정리
                 + 현재 내부 Route를 redirect로 보존
                 + 로그인 화면 이동
```

필수 규칙:

- refresh는 동시에 한 번만 수행하는 single-flight 구조로 구현한다.
- 원 요청에는 `_retry` 같은 내부 flag를 두어 무한 반복을 방지한다.
- refresh endpoint 자체의 401은 다시 refresh하지 않는다.
- 401 이후의 원 요청 재시도는 인증 복구이며, 일반적인 POST 자동 재시도 정책과 구분한다.
- 사용자가 로그아웃한 뒤 대기 중인 refresh 결과가 인증 상태를 되살리지 않도록 generation 또는 abort 제어를 둔다.

### 5.4 인증 어댑터

프론트의 `authService`는 다음 인터페이스를 고정한다.

```text
signup(payload)
login(payload)
logout()
restoreSession()
refreshSession()
getAccessToken()
```

백엔드 계약:

- `POST /auth/login/`: 인증 성공 시 access token을 응답하고 refresh token을 HttpOnly cookie로 설정
- `POST /auth/refresh/`: cookie의 refresh token을 검증하고 새 access token 반환
- `POST /auth/logout/`: refresh cookie 만료·폐기
- 사용자 정보 endpoint 또는 login/refresh 응답으로 `authStore.user` 복원

앱 시작 시 access token이 메모리에 없으므로 `restoreSession()`이 refresh endpoint를 한 번 호출해 로그인 상태를 복원한다. 복원 완료 전 보호 Route 판단을 시작하지 않는다.

로그아웃 성공 또는 refresh 실패 시 다음을 수행한다.

1. access token 제거
2. 모든 Pinia Store `$reset()`
3. pending intent와 후기 초안 등 개인 sessionStorage 제거
4. 진행 중인 사용자 전용 요청 취소
5. 공개 Route 또는 로그인 Route로 이동

### 5.5 Kakao Map SDK Loader

`services/kakaoMapLoader.js` 또는 `useKakaoMapScript`는 Kakao Map JavaScript SDK를 중복 없이 동적으로 로드한다.

- 앱 최초 진입에서는 SDK를 로드하지 않는다.
- 도서관 상세의 `MapPanel`이 mount될 때 최초 1회 로드한다.
- 동일 시점의 여러 호출은 하나의 Promise를 공유한다.
- `window.kakao?.maps`가 이미 준비되어 있으면 재삽입하지 않는다.
- key 누락, script 오류, SDK 초기화 실패를 구분하여 `MapPanel`의 대체 UI로 전달한다.
- v1.1에서는 좌표 기반 단일 마커 표시만 사용하며 Places·Geocoder·Roadview library를 추가하지 않는다.

### 5.6 요청 취소

- 검색어·필터가 변경되어 이전 목록 요청이 불필요해지면 `AbortController`로 취소한다.
- 페이지 unmount 시 장시간 진행 중인 GET 요청을 취소한다.
- 로그아웃 시 사용자 전용 진행 요청을 취소한다.
- 취소된 요청은 사용자 오류로 표시하지 않는다.

### 5.7 공통 API 오류 모델

```ts
interface NormalizedApiError {
  status: number | null
  code: string
  detail: string
  fields: Record<string, string[]>
  retryAfterSeconds?: number
  isNetworkError: boolean
  isCanceled: boolean
}
```

오류 표시 우선순위:

1. 해당 Form field 아래의 `fields`
2. 화면 내 ErrorState의 `detail`
3. 알 수 없는 오류 기본 문구

응답 Interceptor의 추가 규칙:

- `429`는 `Retry-After`를 읽어 재시도 가능 시점을 안내한다.
- 일반 네트워크 오류 자동 재시도는 idempotent GET에 한해 최대 1회 허용한다.
- POST·PATCH·DELETE는 401 인증 복구 외에는 자동 재시도하지 않는다.

---

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
| `my-outings` | `/my-outings` | `MyOutingsDashboardView` | 회원 |
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

### 6.2 Route Meta

```js
meta: {
  requiresAuth: true,
  guestOnly: false,
  requiresAuthor: false,
  layout: 'default',
  preserveRedirect: true,
  title: '나의 나들이',
}
```

- `requiresAuth`: 인증이 끝나기 전 페이지 mount를 차단하고 비회원은 로그인으로 이동
- `guestOnly`: 로그인 사용자의 로그인·회원가입 재접근을 홈으로 이동
- `requiresAuthor`: 후기 수정처럼 로그인 후 자원 소유자 검증이 필요한 Route
- `layout`: `default`, `auth`, `member`
- `title`: `document.title` 구성에 사용

### 6.3 Router Guard

```text
앱 인증 초기화 대기
→ requiresAuth && 비로그인
   → /auth/login?redirect={to.fullPath}
→ guestOnly && 로그인
   → 안전한 redirect query 또는 /
→ 보호 Route 통과
→ requiresAuthor Route는 페이지 진입 직후 상세 응답으로 작성자 검증
   → 작성자가 아니면 /403
   → hidden 후기이면 수정 화면 대신 읽기 전용 상세
```

- 후기 작성·수정·선호 설정은 비회원 상태에서 컴포넌트를 mount하거나 API를 호출하지 않는다.
- 로그인 후에는 `redirect` query로 원래 보호 Route에 복귀한다.
- 저장·좋아요 외의 작업은 자동 실행하지 않는다.
- `redirect`는 내부 경로만 허용한다. `http://`, `https://`, `//`, 역슬래시 기반 우회 값은 무시한다.
- 작성자 여부는 URL이나 클라이언트 상태만으로 확정하지 않고 서버 응답을 최종 기준으로 사용한다.

### 6.4 Query String 규칙

- 값이 기본값이면 URL에서 생략한다.
- 다중 선택은 쉼표로 직렬화하고 중복을 제거한다.
- 빈 문자열·`undefined`·`null`은 제거한다.
- 필터가 변경되면 `page=1`로 초기화한다.
- 검색 입력 중 자동 반영은 `router.replace`, 명시적 화면 이동은 `router.push`를 사용한다.
- Query 파싱 실패 시 유효한 값만 남기고 화면에 치명적 오류를 표시하지 않는다.

예시:

```text
/libraries?sigungu=해운대구,수영구&purpose=study&facility=wifi,lounge&open_today=true&ordering=-reading_seat_count&page=2
```

### 6.5 Scroll 동작

- 새로운 상세·목록 Route: 상단으로 이동
- 브라우저 뒤로 가기: 저장된 위치 복원
- 같은 목록에서 Query만 변경: 결과 제목 또는 목록 시작점으로 Focus와 Scroll 이동
- Hash가 있으면 해당 요소로 이동하되 고정 헤더 높이를 보정

---

## 7. 상태 관리 명세

### 7.1 상태 관리 원칙

- URL로 표현할 수 있는 목록 상태는 Router Query가 원본이다.
- 인증 사용자와 기준정보는 Pinia에 유지한다.
- 페이지 상세·목록 데이터는 도메인 Store에 유지하되 서버 응답이 원본이다.
- 모달·토스트·드로어 같은 일시적 UI는 `uiStore`가 관리한다.
- 후기 작성 초안은 Pinia와 `sessionStorage`를 함께 사용한다.
- 정확한 위치 좌표는 메모리에만 유지하고 영구 저장하지 않는다.

### 7.2 Store 목록

#### `authStore`

```text
state
- user
- accessToken: 메모리 전용
- initialized
- status: idle|loading|refreshing|authenticated|anonymous|error
- pendingIntent
- authGeneration

actions
- initialize()
- signup(payload)
- login(payload)
- logout()
- refreshSession()
- refreshUser()
- setPendingIntent(intent)
- consumePendingIntent()
- clearAuthState()
```

#### `referenceStore`

```text
state
- homePurposes
- profilePurposes
- profileTags
- reviewTagGroups
- regions
- fetchedAt

actions
- ensureHomePurposes()
- ensureProfileReferences()
- ensureReviewTags()
- ensureRegions()
- clear()
```

기준정보는 세션 동안 재사용하며 서버 오류 시 이미 받은 데이터가 있으면 유지한다. 로그아웃 시 전체 Store 초기화 정책에 따라 함께 초기화한 뒤 공개 화면에서 필요할 때 다시 조회한다.

#### `homeStore`

```text
state
- recommendations
- themeItemsByPurpose
- loading
- error
- fetchedAt

actions
- fetchRecommendations({ coordinates? })
- fetchThemeRecommendations({ purpose, coordinates?, limit })
- invalidatePersonalized()
```

#### `libraryStore`

```text
state
- listResponse
- listStatus
- currentLibrary
- detailStatus
- similarItems

actions
- fetchList(query, coordinates?)
- fetchDetail(id)
- fetchSimilar(id)
- toggleSave(id, nextSaved)
- clearDetail()
```

#### `bookStore`

```text
state
- popularSnapshot
- searchResponse
- currentBook
- holdingLibraries

actions
- fetchPopular()
- searchBooks(query)
- fetchBookDetail(isbn13)
- fetchHoldingLibraries(isbn13)
- toggleSave(bookId, nextSaved)
```

#### `programStore`

```text
state
- listResponse
- currentProgram

actions
- fetchList(query)
- fetchDetail(id)
- toggleSave(id, nextSaved)
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
- createReview(formData)
- updateReview(id, formData)
- deleteReview(id)
- toggleLike(id, nextLiked)
- saveDraft(draft)
- clearDraft()
```

#### `myOutingsStore`

```text
state
- dashboard
- listsByType
- fetchedAtByType

actions
- fetchDashboard()
- fetchList(type, query)
- invalidate(type?)
```

#### `profileStore`

```text
state
- profile
- preferences

actions
- fetchProfile()
- updateProfile(payload)
- fetchPreferences()
- replacePreferences(payload)
```

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
- openProfileMenu()
- closeProfileMenu()
- openFilterDrawer()
- closeFilterDrawer()
- resetUi()
```

### 7.3 전체 Store 초기화 정책

로그아웃과 refresh 실패는 동일한 application reset 경로를 사용한다.

```text
abort user requests
→ 모든 Store $reset()
→ access token 제거
→ pending intent·개인 초안 제거
→ UI overlay 닫기
→ 공개 Route 또는 로그인 Route 이동
```

단, Router URL에 있는 공개 검색 Query는 Store가 아니므로 자동 삭제하지 않는다. 로그아웃 후 같은 공개 목록을 계속 볼 수 있다.

### 7.4 캐시와 무효화

| 데이터 | 클라이언트 재사용 기준 | 무효화 조건 |
|---|---|---|
| 지역·목적·태그 기준정보 | 세션 | 로그아웃 시 전체 Store reset, 앱 새 버전 |
| 홈 추천 | 5분 | 선호 변경, 저장·좋아요·후기 변경 |
| 도서관 목록 | 동일 Query 동안 | Query 변경, 관련 저장 상태 변경 시 item만 수정 |
| 도서관 상세 | 5분 | 해당 도서관 저장·후기 작성·수정 |
| 인기 도서 | 30분 | 수동 새로고침 |
| 책·프로그램 상세 | 10분 | 저장 상태 변경 시 item만 수정 |
| 커뮤니티 목록 | 1분 | 후기 생성·수정·삭제·좋아요 |
| 나의 나들이 | 1분 | 저장·좋아요·후기·선호 변경 |
| 프로필 | 세션 | 프로필 수정 |

### 7.5 낙관적 업데이트

저장과 좋아요는 다음 순서로 처리한다.

```text
현재 상태 보관
→ UI 즉시 반전
→ PUT 또는 DELETE
→ 성공: 서버 응답으로 확정
→ 실패: 이전 상태로 롤백 + 오류 Toast
```

동일 버튼을 요청 중 다시 누르지 못하도록 `aria-disabled`와 loading 상태를 적용한다.

후기 생성·수정·삭제는 낙관적으로 처리하지 않는다.

---

## 8. 공통 데이터 계약

### 8.1 공통 목록과 오류

```ts
interface ApiListResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

interface ApiErrorResponse {
  code: string
  detail: string
  fields?: Record<string, string[]>
}
```

### 8.2 이미지

```ts
interface ResolvedImage {
  url: string | null
  is_fallback: boolean
  fallback_key?: string | null
  attribution_text?: string | null
  license_code?: string | null
}
```

프론트 규칙:

- `url=null`: 도메인 기본 Placeholder를 표시
- `is_fallback=true`: 출처 오버레이를 강제하지 않음
- 외부 공식 이미지이며 `attribution_text`가 있으면 ⓘ 버튼 표시
- `source_page_url`은 공개 UI 계약으로 사용하지 않음

### 8.3 운영 상태

```ts
interface TodayHours {
  open: string | null
  close: string | null
  closes_next_day?: boolean
}

interface LibraryOperationSummary {
  open_today: boolean | null
  open_now: boolean | null
  today_hours: TodayHours | null
  reason_code?: string | null
  reason_text?: string | null
}
```

표시 규칙:

| 데이터 | 표시 |
|---|---|
| `open_now=true` | 지금 운영 중 |
| `open_now=false`, `open_today=true` | 오늘 운영 · 현재 운영 아님 |
| `open_today=false` | 오늘 휴관 |
| `open_today=null` | 오늘 운영 정보 확인 필요 |
| `open_today=true`, 시간 null | 오늘 운영 · 시간 확인 필요 |

### 8.4 도서관 카드

```ts
interface LibraryCardDto {
  id: number
  name: string
  library_type: 'public' | 'small' | 'children' | 'other'
  sigungu: string
  thumbnail: ResolvedImage
  open_today: boolean | null
  open_now: boolean | null
  today_hours: TodayHours | null
  book_count: number | null
  reading_seat_count: number | null
  distance_m: number | null
  purpose_score: number | null
  main_tags: TagDto[]
  is_saved: boolean | null
}
```

### 8.5 태그

```ts
interface TagDto {
  id?: number
  code: string
  label: string
  semantic_kind: 'objective' | 'experience' | 'classification' | 'content'
  review_label?: string
  group_code?: string
}
```

객관 태그와 경험 태그는 문구가 비슷해도 별도 chip으로 표시할 수 있다.

### 8.6 책

```ts
interface BookSummaryDto {
  id: number
  isbn13: string
  title: string
  authors_text: string | null
  publisher: string | null
  publication_year: string | number | null
  cover_image_url: string | null
  kdc_class_no?: string | null
  kdc_class_name?: string | null
  is_saved?: boolean | null
}
```

책 상세 Route는 ISBN을 사용하고 저장 API는 내부 `id`를 사용한다. 상세 응답에 `id`가 반드시 포함되어야 한다.

### 8.7 프로그램

```ts
interface ProgramCardDto {
  id: number
  title: string
  library: { id: number; name: string }
  category_code: string
  target_codes: string[]
  application_required: boolean | null
  application_start_date: string | null
  application_end_date: string | null
  application_status: '신청가능' | '신청마감' | '신청없음' | null
  operation_start_date: string | null
  operation_end_date: string | null
  operation_status: '예정' | '진행중' | '종료' | null
  source_url: string | null
  image: ResolvedImage
  is_saved: boolean | null
}
```

### 8.8 후기

```ts
interface ReviewCardDto {
  id: number
  author: {
    id: number
    nickname: string
    profile_image: ResolvedImage
  }
  library: { id: number; name: string }
  content: string
  tags: TagDto[]
  related_books: BookSummaryDto[]
  related_programs: Array<{
    id: number
    title: string
    library_id: number
    library_name: string
  }>
  images: ResolvedImage[]
  view_count: number
  like_count: number
  is_liked: boolean | null
  moderation_status: 'pending' | 'visible' | 'hidden'
  created_at: string
  updated_at: string
}
```

### 8.9 null과 0 표시

- `null`: 정보 미제공 또는 판단 불가
- `0`: 원천이 실제 0으로 제공한 값일 수 있음
- 면적·장서·좌석의 `null`은 `-`가 아니라 “정보 없음” 또는 항목 미표시
- `0`이 품질 경고일 수 있는 필드는 백엔드가 품질 상태를 제공하지 않는 한 프론트에서 임의 보정하지 않음

---

## 9. 디자인 시스템과 공통 UI

### 9.1 디자인 참고 원칙

첨부 시안은 **시각적 방향과 컴포넌트 패턴을 위한 참고 자료**로 사용한다. 시안에 임의로 추가된 기능이나 전국 예시 데이터는 구현 요구사항으로 간주하지 않는다. 기능·권한·데이터 구조가 충돌하면 본 명세와 Django API 명세를 우선한다.

디자인 방향:

- 밝은 아이보리 배경과 흰색 surface
- 녹색 브랜드 포인트
- 둥근 카드와 얇은 border
- 과하지 않은 부드러운 그림자
- 충분한 여백을 둔 따뜻한 공공서비스형 UI
- 딱딱한 행정 화면보다 실제 도서관 나들이를 떠올릴 수 있는 편안한 인상

시안에서 유지할 요소:

- 로고와 서비스명 조합
- 현재 메뉴의 녹색 underline
- 아이보리·연녹색 상단 배너
- 녹색 primary button과 밝은 secondary button
- 태그 chip, 상태 badge, bookmark·heart icon
- 도서관·프로그램·후기 카드의 이미지와 정보 구역 분리
- 검색·필터 패널과 결과 목록의 명확한 구획
- 도서관 상세의 정보 카드 grid
- 나의 나들이의 성향 카드·관심 태그·저장 목록 구조

시안에서 제외하거나 재해석할 요소:

- 홈 검색창
- 알림 bell, 임의 도움말 박스, 기능과 무관한 장식성 아이콘
- 전국 도서관 예시 데이터
- 내부 프로그램 신청처럼 보이는 CTA
- 명세에 없는 성향 분석 항목
- 후기 별점·제목·방문 목적 입력
- 실시간 잔여 좌석 표시

### 9.2 디자인 토큰

프론트는 직접 색상값을 컴포넌트에 반복 작성하지 않고 CSS 변수로 관리한다. 아래 값은 첨부 시안에서 추출한 초기 구현 기준이며, 접근성 대비 검증 결과에 따라 소폭 조정할 수 있다.

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
  --color-success: var(--bs-success);
  --color-warning: var(--bs-warning);
  --color-danger: var(--bs-danger);
  --radius-sm: 0.5rem;
  --radius-md: 0.75rem;
  --radius-lg: 1rem;
  --radius-xl: 1.25rem;
  --shadow-card: 0 0.25rem 1rem rgb(31 55 37 / 8%);
}
```

- Primary text와 버튼은 WCAG 대비 기준을 충족해야 한다.
- 선택 상태를 녹색만으로 표시하지 않고 border, icon, text를 함께 사용한다.
- 배너 이미지는 텍스트 대비를 해치지 않도록 overlay 또는 분리 레이아웃을 사용한다.

### 9.3 타이포그래피

- 기본 본문: 16px 이상
- 보조 정보: 14px 이상
- 화면 H1은 Route당 하나
- 카드 제목은 H2 또는 H3 계층을 문맥에 맞게 사용
- 긴 도서관명·프로그램명은 모바일 2줄, 데스크톱 2~3줄까지 허용
- 본문을 크기만으로 구분하지 않고 굵기·여백·시맨틱 heading을 함께 사용
- 상단 배너 제목은 화면 H1을 대체하거나 H1 아래의 시각적 headline으로 사용하되 heading 계층을 중복하지 않는다.

### 9.4 공통 컴포넌트

#### Layout

- `AppHeader`
- `AppFooter`
- `MobileBottomNavigation`
- `ProfileMenuDrawer`
- `PageContainer`
- `PageHeader`
- `PageHeroBanner`
- `Breadcrumbs`
- `MemberSubNavigation`

#### Card

- `LibraryCard`
- `BookCard`
- `ProgramCard`
- `ReviewCard`
- `RelatedBookMiniCard`
- `RelatedProgramMiniCard`
- `MetricCard`

#### Action

- `SaveButton`
- `LikeButton`
- `AuthGate`
- `ExternalLinkButton`
- `ShareButton` MAY

#### Filter

- `SearchBar`
- `FilterPanel`
- `FilterSidebar`
- `FilterDrawer`
- `FilterGroup`
- `ActiveFilterChips`
- `SortSelect`
- `PaginationBar`
- `ResultCount`

#### Feedback

- `LoadingSkeleton`
- `EmptyState`
- `ErrorState`
- `InlineError`
- `ConfirmDialog`
- `LoginRequiredDialog`
- `ToastRegion`
- `PermissionPrompt`
- `ModerationStatusBadge`

#### Media

- `ResponsiveImage`
- `AttributionOverlay`
- `MapPanel`
- `ImageUploader`

### 9.5 핵심 컴포넌트 계약

#### `SaveButton`

```text
props
- resourceType: library|book|program
- resourceId
- modelValue: boolean|null
- size: sm|md
- disabled

emits
- update:modelValue
- success
- error
```

동작:

- `modelValue=null`이며 비회원이면 `AuthGate` 실행
- 회원이면 PUT·DELETE를 낙관적으로 실행
- 버튼 label은 “저장하기” / “저장됨”을 제공
- icon만 보일 때도 `aria-label` 필수

#### `LikeButton`

- `likeCount`와 `isLiked`를 받는다.
- 성공 시 count와 상태를 함께 갱신한다.
- count는 0 미만으로 내려가지 않는다.
- hidden 후기에서는 렌더링하지 않거나 disabled 처리한다.

#### `AttributionOverlay`

- 이미지 위 ⓘ 버튼을 제공한다.
- hover, focus, tap에서 전체 출처 문구를 오버레이로 표시한다.
- 모바일 tap 후 바깥 영역 또는 닫기 버튼으로 닫는다.
- 오버레이 문구를 임의로 축약하지 않는다.
- `aria-expanded`, `aria-controls`, `role=note`를 사용한다.

#### `MobileBottomNavigation`

- 홈, 도서관, 책, 프로그램, 커뮤니티의 다섯 Route만 표시한다.
- 아이콘 단독 사용을 금지하고 label을 함께 표시한다.
- 현재 Route에 `aria-current="page"`를 적용한다.
- 프로필·나의 나들이는 포함하지 않는다.

### 9.6 카드 공통 원칙

- 카드 전체가 링크인 경우 내부 버튼을 중첩하지 않는다.
- 구현은 카드 제목 링크를 주 링크로 두고 클릭 가능한 시각 영역을 확장한다.
- 키보드 Focus가 저장·좋아요 버튼과 상세 링크에 각각 도달해야 한다.
- 이미지 비율은 도서관·프로그램 16:9, 책 표지 2:3을 기본으로 한다.
- 카드 border와 shadow는 정보를 구분할 정도로만 사용하고 중첩 그림자를 피한다.
- 태그 chip은 최대 노출 개수를 정하고 초과분은 `+N`으로 표시할 수 있다.
- 이미지 로딩 실패 시 동일 도메인 Placeholder로 대체한다.

---

## 10. 공통 상호작용과 화면 상태

### 10.1 로딩

- 첫 진입: 화면 구조와 유사한 Skeleton 표시
- 재조회: 기존 결과를 유지하고 목록 상단 progress 또는 필터 영역 loading 표시
- 저장·좋아요: 해당 버튼만 busy 상태
- 전체 화면 Spinner는 인증 초기화처럼 화면 구성이 불가능한 경우에만 사용

### 10.2 빈 상태

검색 결과 없음:

```text
선택한 조건에 맞는 결과가 없습니다.
필터를 줄이거나 지역 범위를 넓혀 보세요.
```

데이터 자체 없음:

```text
현재 등록된 문화 프로그램이 없습니다.
```

회원 활동 없음:

```text
아직 저장한 도서관이 없습니다.
관심 있는 도서관을 찾아 저장해 보세요.
```

### 10.3 오류 상태

| 상태 | 화면 처리 |
|---|---|
| 네트워크 오류 | 다시 시도 버튼, 입력·필터 유지 |
| 400 | 잘못된 필터·Form field 강조 |
| 401 | 인증 복구 후 원 요청 재시도 또는 로그인 이동 |
| 403 | 권한 없음 화면 또는 Toast |
| 404 | 자원별 NotFound 상태 |
| 409 | 최신 상태 재조회 후 충돌 설명 |
| 429 | 재시도 가능 시간 안내 |
| 500 이상 | 서비스 오류, 요청 ID가 있으면 표시 |

### 10.4 위치 권한

상태:

```text
idle → requesting → granted
                 ├→ denied
                 ├→ unavailable
                 └→ timeout
```

원칙:

- 홈 진입 또는 앱 진입 즉시 권한을 요청하지 않는다.
- 사용자가 “가까운 곳”을 눌렀을 때 요청 이유를 먼저 설명한다.
- 좌표는 Store 메모리에만 유지한다.
- 위치 거절을 오류 페이지로 처리하지 않는다.
- 거절 시 지역 선택 기반 도서관 찾기로 전환한다.

권장 브라우저 옵션:

```js
{
  enableHighAccuracy: false,
  timeout: 8000,
  maximumAge: 300000,
}
```

### 10.5 외부 링크

- 프로그램 원문과 도서관 홈페이지는 새 탭으로 연다.
- `target="_blank" rel="noopener noreferrer"`를 사용한다.
- 버튼 또는 링크에 “외부 사이트”를 시각적·접근 가능한 텍스트로 안내한다.
- 원문 URL이 없으면 CTA를 숨기고 “원문 링크 없음”을 별도 오류로 강조하지 않는다.

### 10.6 날짜와 숫자

- 화면 기준 Timezone: `Asia/Seoul`
- 날짜: `2026. 6. 23.` 또는 문맥상 `6. 23.`
- 기간: `2026. 6. 10. ~ 6. 24.`
- 숫자: `61,405권`, `134석`, `890.58㎡`
- 거리: 1,000m 미만은 m, 이상은 소수점 1자리 km
- 시간: `09:00~22:00`, 미확인은 “시간 확인 필요”

### 10.7 Toast

성공 Toast 예시:

- 도서관을 저장했어요.
- 저장을 해제했어요.
- 후기에 좋아요를 표시했어요.
- 후기를 등록했어요.

오류 Toast는 사용자가 취할 행동을 포함한다.

- 저장하지 못했어요. 잠시 후 다시 시도해 주세요.
- 로그인 정보가 만료되었어요. 다시 로그인해 주세요.

### 10.8 작성 중 이탈 보호

후기 작성·수정과 프로필·선호 설정에서 변경사항이 있으면 Route 이탈 전에 확인한다.

- 브라우저 새로고침: `beforeunload`
- SPA 이동: `onBeforeRouteLeave`
- 저장 성공 또는 초안 삭제 후 guard 해제

### 10.9 페이지네이션

v1.1의 목록 화면은 무한 스크롤이 아니라 페이지 번호 방식을 사용한다.

적용 대상:

- 도서관 목록
- 도서 검색 결과
- 프로그램 목록
- 커뮤니티 후기 목록
- 나의 나들이 각 목록

공통 규칙:

- 필터·검색·정렬 변경 시 `page=1`
- 현재 페이지는 URL Query에 기록
- 페이지 이동 후 결과 제목 또는 목록 시작점으로 Focus와 Scroll 이동
- 결과가 한 페이지 이하면 `PaginationBar` 숨김
- 브라우저 뒤로 가기에서 페이지와 Scroll 위치 복원
- 서버 page size 기본값을 사용하고 무한 Scroll용 cursor 상태를 만들지 않음

---

## 11. 인증·온보딩 페이지 명세

### 11.1 로그인 — `FR-AUTH-LOGIN`

| 항목 | 명세 |
|---|---|
| Route | `/auth/login` |
| 접근 | 비회원 권장, 회원 접근 시 redirect |
| API | `POST /auth/login/`, 필요 시 `POST /auth/refresh/` |
| Layout | `AuthLayout` |
| 성공 이동 | 안전한 `redirect` → 홈 순서. 대상 화면에서 pending intent를 소비 |

#### 화면 구성

1. 서비스 로고와 로그인 안내
2. 이메일 입력
3. 비밀번호 입력과 표시 전환
4. 로그인 버튼
5. 회원가입 링크
6. 전체 Form 오류 영역

#### 입력 검증

- 이메일: trim, 필수, 이메일 형식
- 비밀번호: 필수
- 제출 중 중복 클릭 금지
- 인증 실패 후 이메일은 유지하고 비밀번호만 비운다.

#### 성공 처리

```text
로그인 성공
→ 응답 access token을 authStore 메모리에 저장
→ 서버가 HttpOnly refresh cookie 설정
→ 사용자 정보 복원
→ 안전한 redirect 또는 홈 이동
→ 대상 화면 mount 후 save/like pending intent를 한 번 소비
```

#### 오류 처리

- 잘못된 인증 정보: “이메일 또는 비밀번호를 확인해 주세요.”
- 비활성 계정: 서버 문구 표시
- 네트워크 오류: Form 값을 유지하고 다시 시도 제공
- redirect가 외부 URL이면 무시

#### 완료 조건

- 키보드만으로 모든 입력과 제출 가능
- 잘못된 입력이 해당 field와 연결됨
- Enter로 제출 가능
- 로그인 성공 후 이전 공개 화면 또는 보호 Route로 안전하게 복귀
- refresh cookie를 JavaScript로 읽거나 Web Storage에 저장하지 않음

### 11.2 회원가입 — `FR-AUTH-SIGNUP`

| 항목 | 명세 |
|---|---|
| Route | `/auth/signup` |
| 접근 | 비회원 권장 |
| API | `POST /auth/signup/` |
| 성공 이동 | `/onboarding/preferences` |

#### 화면 구성

1. 이메일
2. 닉네임
3. 비밀번호
4. 비밀번호 확인
5. 필수 약관 동의 영역 — 실제 약관 문서가 없는 경우 v1.1에서는 서비스 이용 동의 Checkbox만 제공하거나 제외 여부를 팀이 확정
6. 가입 버튼
7. 로그인 링크

#### 클라이언트 검증

- 이메일: 필수, 이메일 형식
- 닉네임: trim 후 필수, 서버 max length 준수
- 비밀번호: 필수, 서버 정책 문구 표시
- 비밀번호 확인: 일치
- 서버 중복 오류는 이메일·닉네임 field에 연결

#### 성공 처리

회원가입 응답이 인증 상태를 함께 생성하면 바로 온보딩으로 이동한다. 인증을 생성하지 않으면 로그인 화면으로 이동하고 가입 완료 안내를 표시한다.

### 11.3 초기 선호 설정 — `FR-AUTH-ONBOARDING`

| 항목 | 명세 |
|---|---|
| Route | `/onboarding/preferences` |
| 접근 | 로그인 회원 |
| API | `GET /purposes/?context=profile`, `GET /tags/?context=profile`, `GET /regions/`, `PUT /profile/preferences/` |
| 필수 여부 | 선택형, 건너뛰기 가능 |

#### 단계

```text
1. 방문 목적 선택
2. 선호 지역 선택
3. 선호 시설·태그 선택
4. 확인 및 저장
```

방문 목적 예시:

- 공부
- 책 탐색
- 아이와 방문
- 분위기
- 가까운 곳
- 프로그램

선호 지역은 부산 구·군 다중 선택이며 현재 위치를 계정 정보로 저장하지 않는다.

#### 저장 Payload

```json
{
  "purpose_ids": [1, 6],
  "regions": [
    {
      "region_key": "21:21090",
      "weight": 1.0,
      "display_order": 1
    }
  ],
  "tag_ids": [31, 44, 52]
}
```

#### 건너뛰기

- API 호출 없이 홈으로 이동한다.
- 홈 개인화 섹션은 데이터가 생기기 전까지 숨긴다.
- 프로필 메뉴에서 언제든 다시 설정할 수 있음을 안내한다.

#### 접근성

- 선택 카드는 실제 Checkbox 또는 Checkbox와 연결된 label로 구현한다.
- 선택 개수와 진행 단계를 텍스트로 제공한다.
- 색상만으로 선택 상태를 표시하지 않는다.

---

## 12. 홈 페이지 명세

### 12.1 홈 — `FR-HOME-001`

| 항목 | 명세 |
|---|---|
| Route | `/` |
| 접근 | 공개 |
| API | `GET /home/recommendations/`, `GET /home/theme-recommendations/` |
| 주요 컴포넌트 | `TodayRecommendationSection`, `PersonalizedSection`, `ThemeRecommendationSection`, `LibraryCard` |

### 12.2 화면 순서

첨부 홈 시안에서 큰 아이보리 계열 Hero, 추천 카드 3열, 테마 chip, 하단 서비스 바로가기 패턴을 참고한다. 홈에는 전역 검색창을 두지 않는다.

```text
Hero/서비스 안내
→ 오늘의 추천 도서관
→ 여기는 어때요? — 조건부
→ 테마별 추천
→ 서비스 탐색 바로가기
```

핵심 콘텐츠의 고정 순서는 다음과 같다.

1. 오늘의 추천 도서관
2. 여기는 어때요?
3. 테마별 추천

### 12.3 최초 데이터 조회

```text
Home mount
→ GET /home/recommendations/
→ today 렌더링
→ personalized.is_available에 따라 조건부 렌더링
→ themes 렌더링
```

정밀 위치는 기본 요청에 포함하지 않는다. 사용자가 가까운 곳을 선택한 뒤 좌표가 확보되면 해당 테마 요청과 필요 시 홈 개인화 재조회를 수행한다.

### 12.4 오늘의 추천 도서관

응답:

```text
title
subtitle
theme_code
items 최대 3개
```

UI:

- 섹션 제목과 오른쪽 “더보기” 링크
- 오늘 기준을 설명하는 subtitle
- 최대 3개의 도서관 카드
- 결과가 1~2개여도 빈 카드로 채우지 않음

정책:

- 카드에는 오늘 운영이 확인된 도서관만 전달된다고 가정한다.
- 응답이 0개이면 “오늘 운영이 확인된 추천 도서관을 준비 중이에요.”를 표시한다.
- 클라이언트가 휴관·미확인 항목으로 임의 보충하지 않는다.

### 12.5 여기는 어때요?

노출 조건:

```js
personalized.is_available === true && personalized.items.length > 0
```

비회원 또는 데이터 부족 상태에서는 섹션 DOM 자체를 렌더링하지 않는다. 잠금 카드나 로그인 광고로 대체하지 않는다.

회원이 개인화 데이터가 없을 때는 테마 섹션 하단에 별도의 작은 안내를 MAY 제공한다.

```text
관심 도서관을 저장하거나 선호를 설정하면 맞춤 추천을 받을 수 있어요.
```

추천 근거가 API에 제공되지 않으면 프론트가 임의 문구를 생성하지 않는다. 향후 `reason_codes` 또는 `reason_text`가 추가될 때만 표시한다.

### 12.6 테마별 추천

고정 테마:

| Code | Label | 위치 필요 |
|---|---|---:|
| `study` | 공부하기 좋은 곳 | 아니요 |
| `book` | 책 보기 좋은 곳 | 아니요 |
| `kids` | 아이와 가기 좋은 곳 | 아니요 |
| `mood` | 분위기 좋은 곳 | 아니요 |
| `nearby` | 가까운 곳 | 예 |

동작:

```text
테마 선택
→ 선택 상태 표시
→ GET /home/theme-recommendations/?purpose={code}&limit=6
→ 최대 6개 카드 표시
→ 더보기 → /libraries?purpose={code}
```

`nearby` 동작:

```text
가까운 곳 선택
→ PermissionPrompt
→ Geolocation 요청
→ 허용: lat/lng를 API에만 전달
→ 거절: 지역 선택 안내 + /libraries 이동 CTA
```

좌표는 Route Query에 포함하지 않는다. 새로고침 후 nearby가 선택되어 있고 좌표가 없으면 다시 사용자 행동을 요구한다.

### 12.7 홈 상태

| 상태 | 처리 |
|---|---|
| 전체 로딩 | 세 섹션 형태 Skeleton |
| 오늘 추천 오류 | 해당 섹션 ErrorState, 테마 탐색은 가능하면 유지 |
| 테마 요청 중 | 기존 테마 결과를 유지하거나 카드 Skeleton 표시 |
| 테마 결과 없음 | “이 테마의 도서관을 더 찾고 있어요.” + 전체 찾기 |
| 개인화 없음 | 섹션 숨김 |
| 위치 거절 | 지역 기반 대체 CTA |

### 12.8 완료 조건

- 오늘 추천과 개인화 항목이 중복되더라도 서버 응답을 그대로 표시하되, 중복 제거는 서버 책임임을 테스트에서 확인
- 홈 공개 테마에 `program`이 표시되지 않음
- nearby 외 테마에서 위치 권한을 요청하지 않음
- 비회원 저장 버튼은 로그인 흐름으로 연결
- 카드 상세 이동과 저장 버튼 이벤트가 충돌하지 않음

---

## 13. 도서관 찾기·상세 명세

### 13.1 도서관 목록 — `FR-LIB-LIST`

| 항목 | 명세 |
|---|---|
| Route | `/libraries` |
| 접근 | 공개 |
| API | `GET /libraries/` |
| 주요 컴포넌트 | `LibrarySearchForm`, `LibraryFilterPanel`, `ActiveFilterChips`, `LibraryCard`, `PaginationBar` |

### 13.2 목록 레이아웃

첨부 시안의 도서관 찾기 화면을 참고해 데스크톱에서는 검색과 필터를 상단의 넓은 패널로 구성하고, 결과를 그 아래에 배치한다.

데스크톱:

```text
PageHeader + 검색 입력 + 초기화
전체 폭 FilterPanel
결과 Count + 정렬
2열 또는 가변폭 LibraryCard 목록
Pagination
```

- 복잡한 필터 그룹은 구분선과 명확한 label로 나눈다.
- 활성 필터는 green outline 또는 chip으로 표시하되 색상만 의존하지 않는다.
- 화면 폭이나 구현 복잡도에 따라 `xl` 이상에서 Sidebar 패턴을 사용할 수 있지만 같은 Route에서 두 패턴을 동시에 노출하지 않는다.

모바일:

```text
PageHeader
검색 입력
필터 버튼 + 정렬
활성 필터 Chips
카드 List
Pagination
하단 공통 Navigation
```

필터는 모바일에서 전체 높이 Drawer 또는 bottom sheet로 제공한다. 적용 버튼을 누르기 전까지 Route Query를 변경하지 않는 임시 상태를 사용한다.

### 13.3 검색

`q` 대상은 서버 계약에 따라 다음을 포함한다.

- 도서관명과 별칭
- 구·군
- 주소
- 운영기관
- 검색 가능한 태그명·코드

동작:

- Enter 또는 검색 버튼으로 실행
- 입력 후 300ms 자동 검색은 MAY이며, 적용 시 2자 이상에서만 수행
- 검색 실행 시 `page=1`
- 검색어 trim 후 빈 값이면 `q` 제거

### 13.4 필터

#### 지역

- `sigungu`
- 부산 구·군 다중 선택
- 기준정보 `GET /regions/`

#### 도서관 유형

- `library_type=public,small,children`
- 표시명은 기준정보 또는 프론트 상수로 관리

#### 방문 목적

- `purpose=study|book|kids|mood|nearby`
- 한 번에 하나만 선택
- `program`은 허용하지 않음

#### 운영 조건

- 오늘 운영: `open_today=true`
- 지금 운영: `open_now=true`
- 주말 운영: `weekend_open=true`
- 공휴일 상태: `holiday_status=open|closed|unknown`
- 늦게까지 운영: `late_open_after=18:00`

`open_today`와 `open_now`를 동시에 선택할 수 있으나 `open_now=true`는 사실상 오늘 운영을 포함한다. UI에서는 중복 의미를 설명하거나 `open_now` 선택 시 `open_today`를 자동 해제해도 된다. Query에는 사용자가 선택한 조건만 기록한다.

#### 시설·공간

`facility` 다중 선택:

```text
reading_room
children_room
digital_room
parking
cafe
wifi
nursing_room
accessible_facility
elevator
lounge
outdoor_space
```

시설 필터는 명시적으로 확인된 `True`만 결과에 포함한다. `False`, `null`, 시설 프로필 부재를 “없음”으로 표시하지 않는다.

#### 장서·좌석

- `min_book_count`, `max_book_count`
- `min_reading_seat_count`, `max_reading_seat_count`
- 숫자 field는 음수를 허용하지 않음
- 최소값이 최대값보다 크면 Form 오류

#### 거리

- `radius_km`
- 거리 필터 또는 `ordering=distance` 사용 시 좌표 필요
- 좌표 확보 실패 시 Query를 적용하지 않고 위치 안내
- 좌표는 API 요청에만 추가

### 13.5 정렬

| 표시명 | Query |
|---|---|
| 이름순 | `name` |
| 장서 많은 순 | `-book_count` |
| 좌석 많은 순 | `-reading_seat_count` |
| 가까운 순 | `distance` |
| 테마 추천순 | `purpose_score` |

- `distance`는 좌표가 있을 때만 활성화
- `purpose_score`는 `purpose`가 있을 때만 활성화
- 유효하지 않은 조합은 가장 안전한 기본 정렬로 되돌리고 Query에서 제거

### 13.6 활성 필터 Chip

- 각 Chip에 제거 버튼 제공
- “전체 초기화” 제공
- 제거 시 `page=1`
- 접근 가능한 버튼 label: “와이파이 필터 제거”

### 13.7 결과 카드

필수 표시:

- 대표 이미지
- 도서관명
- 유형과 구·군
- 오늘 운영 상태
- 오늘 운영시간
- 장서 수와 좌석 수 — 값이 있을 때
- 주요 태그 최대 3개
- 거리 — 좌표 조회 시
- 저장 버튼

태그가 3개를 초과하면 `+N`을 표시할 수 있다. 객관·경험 태그를 색상만으로 구분하지 않고 label 또는 tooltip로 의미를 제공한다.

### 13.8 Pagination

- 서버 기본 20개
- 페이지 번호 방식을 사용하고 무한 스크롤은 사용하지 않음
- 첫·이전·다음·마지막 또는 5개 범위 버튼 제공
- 페이지 변경 시 목록 시작점으로 이동
- 결과가 한 페이지 이하면 Pagination 숨김

### 13.9 결과 없음

우선 CTA:

1. 시설 필터 해제
2. 운영 조건 해제
3. 지역 범위 확대
4. 전체 필터 초기화

프론트는 현재 활성 필터를 분석해 가장 영향이 큰 조건을 단정하지 않고 일반적인 완화 옵션을 제공한다.

### 13.10 도서관 상세 — `FR-LIB-DETAIL`

| 항목 | 명세 |
|---|---|
| Route | `/libraries/:id` |
| 접근 | 공개 |
| API | `GET /libraries/{id}/`, 필요 시 관련 목록 endpoint |
| 주요 컴포넌트 | `LibraryHero`, `OperationInfo`, `FacilityChips`, `MapPanel`, `ProgramPreview`, `ReviewPreview`, `SimilarLibraries` |

#### 상세 순서

```text
상단 요약
기본 정보
운영 정보
장서·열람·공간 규모
시설·공간
위치 지도
관련 문화 프로그램
관련 후기
비슷한 도서관
```

#### 상단 요약

- 대표 이미지
- 출처 ⓘ — attribution이 있을 때
- 도서관명
- 유형·구·군
- 오늘 운영 상태
- 주요 태그
- 저장 버튼

#### 기본 정보

- 도로명주소
- 전화번호 — `tel:` 링크
- 홈페이지 — 외부 링크
- 운영기관
- 값이 없으면 행 전체를 숨기거나 “정보 없음”으로 일관되게 처리

#### 운영 정보

- 오늘 운영 상태
- 평일·토요일·공휴일 운영시간
- 휴관일 원문
- 충돌·미확인 상태는 “확인 필요”로 표시
- `00:00~00:00`을 24시간 운영으로 프론트에서 해석하지 않음

#### 통계

- 도서 자료 수
- 연속간행물 수
- 비도서 자료 수
- 열람좌석 수
- 부지면적
- 건물면적
- 대출 가능 권수·일수

모든 값은 nullable이며, 없는 값을 0으로 표시하지 않는다.

#### 시설

- `True`인 시설만 Chip으로 표시
- 확인된 시설이 하나도 없으면 “확인된 시설 정보가 아직 없습니다.”
- `False`를 “없음”으로 공개할지에 대한 별도 계약이 없으므로 부정 Chip을 만들지 않음

#### 지도

지도 Provider는 Kakao Map JavaScript SDK로 고정한다.

사용 범위:

- 도서관 상세의 위치 지도 표시
- `Library.latitude`, `Library.longitude` 기반 단일 마커
- 도서관명과 도로명주소를 포함한 간단한 정보 표시
- “지도에서 보기” 외부 링크
- “길찾기” 외부 링크

구현 규칙:

- `MapPanel` mount 시 SDK를 동적으로 로드한다.
- SDK script는 앱 전체에서 한 번만 삽입한다.
- `VITE_KAKAO_MAP_APP_KEY`를 사용하고 Kakao Developers에서 개발·운영 허용 도메인을 등록한다.
- 좌표를 주소에서 다시 찾는 Geocoder 호출은 하지 않는다. 백엔드가 제공한 좌표만 사용한다.
- v1.1에서는 Places 검색, Roadview, 교통정보, 다중 경로 탐색을 구현하지 않는다.
- 좌표가 없으면 지도 container를 렌더링하지 않고 주소와 “위치 정보가 확인되지 않았습니다.” 안내를 표시한다.
- SDK key 누락·로드 실패·초기화 실패 시 주소와 외부 Kakao 지도 CTA를 제공하고 상세 전체를 실패시키지 않는다.
- 지도는 키보드 사용자를 가두지 않으며 텍스트 주소와 외부 링크를 동등한 대체 수단으로 제공한다.

#### 관련 프로그램

- 상세 응답 preview를 우선 사용
- 전체보기: `/programs?library_id={id}`
- 카드 선택: `/programs/{programId}`
- 없으면 섹션을 숨기거나 짧은 빈 상태 표시

#### 관련 후기

- 전체보기: `/community?library_id={id}`
- 후기 작성: `/reviews/new?library_id={id}`
- 비회원 작성 버튼은 인증 흐름 후 같은 query로 복귀

#### 비슷한 도서관

- 최대 3개
- `GET /libraries/{id}/similar/?limit=3`
- 현재 도서관은 결과에서 제외된다고 가정
- 결과가 없으면 섹션 숨김

### 13.11 도서관 저장

비회원:

```text
저장 클릭
→ LoginRequiredDialog
→ pending intent 저장
→ 로그인
→ 상세 복귀
→ PUT 자동 실행
```

회원:

- `PUT /my-outings/libraries/{id}/`
- `DELETE /my-outings/libraries/{id}/`
- 메모 필드는 API에 존재하지만 v1.1 UI에서는 노출하지 않는다.

### 13.12 상세 오류와 완료 조건

- 숫자가 아닌 `id`: NotFound 처리
- 404: “도서관 정보를 찾을 수 없습니다.” + 목록 이동
- 관련 프로그램·후기 오류가 상세 전체를 실패시키지 않음
- 이미지 출처 오버레이가 hover·focus·tap 모두 동작
- 시설 `null`이 “없음”으로 표시되지 않음
- 운영 `unknown`이 “휴관”으로 표시되지 않음
- 전화·홈페이지가 없는 경우 비활성 빈 링크를 만들지 않음

---

## 14. 책 둘러보기·상세 명세

### 14.1 책 둘러보기 — `FR-BOOK-LIST`

| 항목 | 명세 |
|---|---|
| Route | `/books` |
| 접근 | 공개 |
| API | `GET /popular-books/`, `GET /books/search/` |
| 주요 컴포넌트 | `PopularBookSection`, `BookSearchForm`, `BookCard`, `PaginationBar` |

### 14.2 초기 화면

첨부 시안의 연녹색·아이보리 상단 배너, 검색 유형 segmented control, 인기 도서 랭킹 카드 패턴을 참고한다. 책 표지는 항상 세로 비율을 유지한다.

```text
PageHeroBanner + 검색 Form
→ 이번 주 인기 도서
→ 도서 검색
→ 검색 전 안내 또는 검색 결과
```

인기 도서는 검색 여부와 무관하게 상단에 유지한다. 모바일에서 검색 결과가 길어질 경우 인기 섹션을 접을 수 있게 하는 기능은 MAY다.

### 14.3 이번 주 인기 도서

표시 항목:

- 순위
- 표지
- 도서명
- 저자
- 출판사 또는 출판연도
- 집계 기간

응답 메타:

- `start_date`
- `end_date`
- `region_code`
- `generated_at`
- `is_stale`

`is_stale=true`일 때:

```text
최근 정상 수집된 인기 도서 결과를 보여드리고 있어요.
```

- 오류가 발생해도 이전 Store 데이터가 있으면 유지한다.
- 인기 도서가 없으면 검색 기능은 정상 제공한다.

### 14.4 도서 검색

검색 유형:

| UI | Query |
|---|---|
| 도서명 | `title` |
| 저자 | `author` |
| ISBN | `isbn` |
| 키워드 | `keyword` |
| 출판사 | `publisher` |

필수 Query:

```text
search_type
q
```

선택 Query:

```text
sort=loan|title|author|pub|pubYear|isbn
order=asc|desc
page
page_size
```

동작:

- 검색어 없이 요청하지 않는다.
- ISBN 선택 시 숫자와 하이픈 입력을 허용하고 요청 전 하이픈을 제거한다.
- 검색 실행 시 Route Query에 `search_type`, `q`, `sort`, `order`, `page`를 기록한다.
- 외부 API 응답 지연을 고려해 검색 Skeleton과 취소 가능한 요청을 사용한다.

### 14.5 검색 결과 카드

- 표지
- 도서명
- 저자
- 출판사
- 출판연도
- KDC 분류명 — 있을 때
- 상세 링크

저장은 책 상세에서 제공하는 것을 기본으로 하며 카드 저장 버튼은 MAY다. 카드에 저장 버튼을 넣으면 내부 `book.id`가 반드시 존재해야 한다.

### 14.6 검색 상태

| 상태 | 처리 |
|---|---|
| 검색 전 | “도서명, 저자 또는 ISBN으로 책을 찾아보세요.” |
| 결과 없음 | 검색어 강조 없이 빈 상태와 검색 조건 변경 안내 |
| 외부 API 오류 | “도서 검색 서비스를 불러오지 못했어요.” + 재시도 |
| 요청 시간 초과 | 검색어 유지, 재시도 |
| 잘못된 ISBN | field 오류 |

### 14.7 책 상세 — `FR-BOOK-DETAIL`

| 항목 | 명세 |
|---|---|
| Route | `/books/:isbn13` |
| 접근 | 공개 |
| API | `GET /books/{isbn13}/`, `GET /books/{isbn13}/libraries/` |
| 저장 API | `PUT/DELETE /my-outings/books/{book_id}/` |

#### 레이아웃

```text
책 표지 | 기본 서지정보 + 저장 버튼
책 소개
KDC·주제 태그
이 책을 보유한 부산 도서관
```

#### 기본 정보

- 도서명
- 저자
- 출판사
- 출판일 또는 출판연도
- ISBN
- 권 정보
- KDC 분류
- 표지

표지가 없으면 2:3 책 Placeholder를 사용한다.

#### 책 소개

- 서버 문자열을 plain text로 렌더링
- 줄바꿈은 CSS `white-space: pre-line`로 처리 가능
- HTML Entity가 포함되면 안전한 text decode utility만 사용하고 `v-html` 금지
- 소개가 없으면 섹션 숨김

#### 저장

- 상세 응답의 내부 `id`를 사용
- 비회원은 로그인 유도
- 회원은 PUT·DELETE 낙관적 처리
- 나의 나들이 책 목록과 대시보드 캐시 무효화

#### 소장 도서관

```text
책 상세 로드 성공
→ 소장 도서관 별도 GET
→ LibraryCard 또는 축약 카드 목록
```

표시 주의:

- “소장”은 실시간 대출 가능을 의미하지 않는다.
- 응답에 대출 가능 상태 계약이 없으므로 “대출 가능” Badge를 표시하지 않는다.
- 도서관 카드 클릭 시 도서관 상세로 이동한다.
- 결과가 없으면 “부산 지역에서 확인된 소장 도서관이 없습니다.”
- 매칭 실패한 외부 도서관을 문자열 카드로 임의 표시하지 않는다.

### 14.8 완료 조건

- 외부 API Key가 Network 요청이나 번들에 나타나지 않음
- 상세 Route의 ISBN 검증 실패 시 API 요청 없이 NotFound 또는 입력 오류 처리
- 책 저장에 ISBN이 아니라 내부 `book_id` 사용
- 소장과 대출 가능을 혼동하는 문구가 없음
- stale 인기 데이터가 최신 데이터처럼 무표시되지 않음

---

## 15. 문화 프로그램 목록·상세 명세

### 15.1 프로그램 목록 — `FR-PROGRAM-LIST`

| 항목 | 명세 |
|---|---|
| Route | `/programs` |
| 접근 | 공개 |
| API | `GET /programs/` |
| 주요 컴포넌트 | `ProgramSearchForm`, `ProgramFilterPanel`, `ProgramCard`, `PaginationBar` |

### 15.2 화면 레이아웃과 목록 Query

첨부 시안처럼 상단 배너·검색 영역과 데스크톱 좌측 FilterSidebar, 우측 카드 Grid를 기본 패턴으로 사용한다. 모바일에서는 FilterDrawer로 전환한다.

```text
q
library_id
sigungu
category
target
application_status
operation_status
ordering
page
```


| 필터 | 값 |
|---|---|
| 검색 | 프로그램명·도서관명 |
| 도서관 | `library_id` |
| 지역 | `sigungu` |
| 유형 | `lecture_humanities`, `reading_writing`, `culture_art`, `experience_education`, `exhibition`, `other` |
| 대상 | `infant`, `elementary`, `teen`, `adult`, `senior`, `family`, `other`, `all` |
| 신청 상태 | `신청가능`, `신청마감`, `신청없음` |
| 운영 상태 | `예정`, `진행중`, `종료` |

### 15.3 도서관 필터

- 도서관 상세에서 “전체 프로그램”을 누르면 `library_id`를 전달한다.
- UI는 ID를 사용자에게 보여주지 않고 도서관명을 표시한다.
- 도서관 선택기는 검색형 Combobox를 권장한다.
- 백엔드에 도서관 간단 검색 endpoint가 별도로 없다면 현재 도서관 상세 진입 경로에서는 이름을 Route state로 전달하고, 일반 목록에서는 지역 선택 후 프로그램 결과에 존재하는 도서관 또는 별도 도서관 목록 API 사용 여부를 TBD로 둔다.

### 15.4 프로그램 카드

필수 표시:

- 이미지
- 프로그램명
- 운영 도서관 링크
- 운영 기간
- 대상
- 신청 상태
- 운영 상태
- 저장 버튼

상태 Badge 우선순위:

1. 운영 상태
2. 신청 상태

예시:

```text
[진행중] [신청마감]
```

`application_required=false` 또는 `신청없음`은 “신청 없이 참여”로 확대 해석하지 않고 “별도 신청 정보 없음” 또는 “신청없음”을 그대로 표시한다.

### 15.5 정렬

| 표시명 | Query |
|---|---|
| 시작일 빠른 순 | `operation_start_date` |
| 최근 시작 순 | `-operation_start_date` |
| 이름순 | `title` |

### 15.6 프로그램 상세 — `FR-PROGRAM-DETAIL`

| 항목 | 명세 |
|---|---|
| Route | `/programs/:id` |
| 접근 | 공개 |
| API | `GET /programs/{id}/` |
| 저장 API | `PUT/DELETE /my-outings/programs/{id}/` |

#### 화면 구성

1. 이미지·프로그램명·상태·저장
2. 운영 도서관
3. 프로그램 유형과 대상
4. 신청 기간·상태
5. 운영 기간·상태
6. 원문 게시판·게시일·수집일 — 제공될 때
7. 원문 이동 CTA
8. 도서관 상세 이동 CTA

#### CTA 문구

서비스 내부 신청 기능이 없으므로 다음 원칙을 지킨다.

- 사용 금지: “신청하기”
- 권장: “원문에서 신청 정보 확인”
- 신청 기간이 지났어도 원문 확인 링크는 제공 가능
- 원문 URL이 없으면 CTA 숨김

#### 저장

- 저장은 프로그램 참여 신청이 아님을 문맥상 명확히 한다.
- 나의 나들이 저장 프로그램 목록과 대시보드 캐시 무효화

### 15.7 상태·완료 조건

- 날짜가 null이면 허위 기간을 생성하지 않음
- 신청마감과 프로그램 종료를 별도 상태로 표시
- 도서관명 클릭이 외부 원문이 아니라 내부 도서관 상세로 이동
- 원문 링크에 외부 사이트 안내와 `noopener` 적용
- 프로그램 신청 API를 호출하지 않음

---

## 16. 커뮤니티·후기 명세

### 16.1 커뮤니티 목록 — `FR-REVIEW-LIST`

| 항목 | 명세 |
|---|---|
| Route | `/community` |
| 접근 | 공개 |
| API | `GET /reviews/`, `GET /tags/?context=review` |
| 주요 컴포넌트 | `ReviewSearchForm`, `ReviewTagFilter`, `ReviewCard`, `LikeButton`, `PaginationBar` |

### 16.2 화면 레이아웃과 목록 Query

첨부 시안의 아이보리 배너, 상단 검색·초기화·후기 작성 CTA, 데스크톱 좌측 필터와 2열 후기 카드 구성을 참고한다. 알림 bell과 임의 도움말 영역은 구현하지 않는다.

```text
q
library_id
tag
ordering=-created_at|-view_count|-like_count
page
```

- `q`: 후기 본문과 도서관명
- `tag`: 경험 태그 code, 다중 선택은 백엔드 계약에 맞춰 쉼표 사용
- 기본 정렬: 최신순

정렬 UI:

| 표시 | Query |
|---|---|
| 최신순 | `-created_at` |
| 조회수순 | `-view_count` |
| 좋아요순 | `-like_count` |

### 16.3 후기 태그 필터

7개 그룹:

1. 공부·열람
2. 공간·분위기
3. 책·자료
4. 프로그램
5. 아이·가족
6. 접근·편의
7. 안내·관리

- `GET /tags/?context=review`의 그룹 순서를 사용한다.
- 후기 작성용 `review_label`과 목록 Chip의 `label`을 구분한다.
- 객관 시설 태그는 후기 선택·필터 목록에 넣지 않는다.

### 16.4 후기 카드

필수 표시:

- 작성자 프로필 이미지·닉네임
- 작성일
- 도서관명 링크
- 후기 본문
- 경험 태그
- 첫 이미지 또는 이미지 Gallery
- 관련 책 미니 카드
- 관련 프로그램 미니 카드
- 조회수
- 좋아요 수와 버튼

본문은 최대 200자이므로 목록에서 전문 표시를 기본으로 한다. 이미지와 관련 콘텐츠가 많아 카드가 지나치게 길면 본문·미니 카드 영역의 레이아웃만 조정하고 내용을 임의 생략하지 않는다.

### 16.5 후기 좋아요

비회원:

```text
좋아요 클릭
→ LoginRequiredDialog
→ pending like intent
→ 로그인
→ 후기 목록/상세 복귀
→ PUT 자동 실행
```

회원:

```text
false → PUT /reviews/{id}/like/
true  → DELETE /reviews/{id}/like/
```

낙관적 처리:

- 좋아요 추가: count +1
- 좋아요 해제: count -1, 최소 0
- 실패 시 원상복구
- 숨김 또는 삭제된 후기에 서버가 404/403을 반환하면 목록에서 재조회

### 16.6 후기 작성 CTA

- 목록 상단 또는 Floating Action Button으로 제공
- Route: `/reviews/new`
- 도서관 상세에서 진입 시 `/reviews/new?library_id={id}`
- 비회원은 로그인 후 같은 Route로 이동

### 16.7 후기 상세 — `FR-REVIEW-DETAIL`

| 항목 | 명세 |
|---|---|
| Route | `/reviews/:id` |
| 접근 | 공개 후기 공개 |
| API | `GET /reviews/{id}/` |
| 주의 | 상세 GET에서 조회수 증가 |

#### 화면 구성

- 작성자
- 작성·수정 시각
- 도서관 링크
- 본문
- 태그
- 이미지 Gallery
- 관련 책·프로그램
- 조회수·좋아요
- 작성자 메뉴

#### 조회수

- 상세 Route 진입에서 한 번 호출
- 프론트가 별도 조회수 증가 API를 호출하지 않음
- Strict mode나 개발 환경의 중복 mount로 동일 GET을 두 번 보내지 않도록 Store 요청 deduplication
- 목록 preview·prefetch로 상세 endpoint를 호출하지 않음

#### 작성자 메뉴

`moderation_status=visible`인 본인 후기:

```text
수정 → /reviews/{id}/edit
삭제 → ConfirmDialog → DELETE → 목록 또는 이전 Route
```

`moderation_status=hidden`인 본인 후기:

- “공개되지 않음” 배지 표시
- 읽기 전용
- 수정·삭제·좋아요·공유 메뉴 미표시
- 비작성자는 상세 접근 불가

삭제 성공 후 이동 우선순위:

1. `redirect`가 안전한 내부 경로이면 해당 경로
2. `/my-outings/reviews`에서 진입했다면 해당 목록
3. `/community`

### 16.8 후기 작성 — `FR-REVIEW-CREATE`

| 항목 | 명세 |
|---|---|
| Route | `/reviews/new` |
| 접근 | 회원 |
| API | `POST /reviews/`, 기준정보·검색 API |
| 전송 | 단일 `multipart/form-data` 요청 |

#### Form 순서

```text
1. 도서관 선택 — 필수
2. 후기 본문 — 필수, 1~200자
3. 경험 태그 — 필수, 1~5개
4. 관련 책 — 선택, 최대 5권
5. 관련 프로그램 — 선택, 최대 5개
6. 이미지 — 선택, 최대 5장
7. 제출
```

별도 제목, 별점, 방문 목적 field는 제공하지 않는다.

#### 도서관 선택

- Query `library_id`가 있으면 해당 도서관을 선선택한다.
- 사용자는 필요 시 변경 가능하되, 관련 프로그램 선택값은 도서관 변경 시 초기화 또는 재검증한다.
- 도서관 검색은 `/libraries/?q=&page_size=`를 사용한다.
- Combobox는 입력·결과·선택을 키보드로 조작할 수 있어야 한다.

#### 본문

- trim 후 1~200자
- 현재 글자 수 표시: `123 / 200`
- 200자를 초과하면 제출 금지
- 줄바꿈 허용
- HTML 입력을 지원하지 않음

#### 태그

- 7개 그룹으로 표시
- 선택 최소 1개, 최대 5개
- 5개 선택 후 미선택 항목은 disabled 처리하되 기존 선택 해제 가능
- 선택 수를 스크린리더에 안내

#### 관련 책

- 도서 검색 API 사용
- 최대 5권
- 같은 책 중복 선택 금지
- 선택된 책은 제거 가능한 미니 카드
- 책 검색 외부 오류가 후기 작성 전체를 막지 않음

#### 관련 프로그램

- 선택한 도서관의 프로그램만 기본 노출
- `GET /programs/?library_id={libraryId}`
- 최대 5개
- 도서관 변경 시 다른 도서관 프로그램은 자동 제거하고 사용자에게 안내

#### 이미지

- 최대 5장
- 허용 형식: JPEG, PNG, WebP
- client 검사 권장 최대 크기: 파일당 10MB — 서버 설정과 동기화
- 순서 변경은 MAY
- Preview Object URL은 제거·unmount 시 `URL.revokeObjectURL`
- EXIF·실제 MIME 검증은 서버가 최종 책임
- 업로드 실패 시 Form 값과 나머지 Preview 유지

#### Multipart 예시

```text
library_id=101
content=...
tag_ids=[81,93]
book_ids=[3]
program_ids=[8]
images=<file repeated>
```

후기 본문·태그·관련 책·관련 프로그램·이미지를 한 번의 multipart 요청으로 전송한다. 배열 직렬화 형식은 백엔드 parser와 구현 전에 확정하며 JSON 문자열 또는 반복 field 중 하나만 사용한다.

### 16.9 후기 수정 — `FR-REVIEW-EDIT`

| 항목 | 명세 |
|---|---|
| Route | `/reviews/:id/edit` |
| 접근 | 회원·작성자·`visible` 후기 |
| API | `GET /reviews/{id}/`, `PATCH /reviews/{id}/` |

접근 흐름:

```text
비회원 직접 접근
→ Router Guard가 페이지 mount 전 차단
→ /auth/login?redirect=/reviews/{id}/edit
→ 로그인 성공 후 edit Route 복귀
→ 상세 API로 작성자·moderation_status 검증
→ 작성자 아니면 403
→ hidden 후기이면 읽기 전용 상세로 이동
```

- 기존 데이터를 Form 초기값으로 사용한다.
- 제출을 자동 실행하거나 기존 값을 자동 저장하지 않는다.
- 기존 이미지 삭제·신규 이미지 추가 계약은 구현 전 백엔드와 확정한다.
- 이미지가 포함되는 수정은 한 번의 multipart 요청으로 처리한다.
- 도서관 변경은 v1.1에서 불허하고 read-only로 표시한다.
- 태그·관련 책·프로그램은 전체 교체한다.
- 403이면 `/403` 또는 상세로 이동하고 권한 안내를 표시한다.

### 16.10 초안 저장

`useReviewDraft`는 다음을 저장한다.

```ts
interface ReviewDraft {
  mode: 'create' | 'edit'
  reviewId?: number
  libraryId?: number
  content: string
  tagIds: number[]
  bookIds: number[]
  programIds: number[]
  savedAt: string
}
```

- `sessionStorage` 사용
- 이미지 File은 저장하지 않음
- 입력 변경 후 500ms debounce
- 24시간이 지난 초안은 폐기
- 제출 성공 시 삭제
- 기존 초안이 있으면 복원 여부 확인

### 16.11 후기 Form 오류

| 오류 | 처리 |
|---|---|
| 본문 없음·초과 | 본문 아래 오류 + Focus |
| 태그 0개·6개 이상 | 태그 그룹 상단 오류 |
| 관련 책·프로그램 초과 | 해당 선택 영역 오류 |
| 프로그램 도서관 불일치 | 관련 프로그램 초기화·서버 오류 표시 |
| 이미지 수·크기 초과 | 문제 파일명 포함 |
| 인증 만료 | 초안 저장 → 로그인 → Form 복귀 |

### 16.12 완료 조건

- 후기 조회수가 목록 조회로 증가하지 않음
- 본문 최대 200자, 태그 1~5개 강제
- 제목·별점·방문 목적 field가 없음
- 관련 프로그램이 선택 도서관과 일치
- 이미지 최대 5장
- 좋아요 로그인 복귀와 자동 실행 정상
- 수정·삭제 메뉴가 작성자에게만 표시
- 숨김 후기는 작성자에게 읽기 전용으로 표시하고 비작성자 404/403을 정상 처리

---

## 17. 나의 나들이 명세

### 17.1 통합 대시보드 — `FR-MY-DASHBOARD`

| 항목 | 명세 |
|---|---|
| Route | `/my-outings` |
| 접근 | 회원 |
| API | `GET /my-outings/dashboard/` |
| 주요 컴포넌트 | `ProfileSummary`, `PreferenceSummary`, `PurposeDistribution`, `TopTagList`, `InterestSummary`, `ActivityCountCards` |

### 17.2 화면 순서

```text
프로필·인사말
→ 대표 선호 문장과 분석 기준
→ 4축 나들이 성향
→ 많이 접한 태그
→ 관심 분야
→ 저장·활동 개수
→ 각 목록 바로가기 또는 preview
```

### 17.3 프로필·요약

표시:

- 프로필 이미지
- 닉네임
- greeting
- preference_summary
- analysis_basis
- 선호 설정 이동

대표 문장은 서버가 결정론적 template 또는 표현 보조를 통해 생성한 문자열을 그대로 사용한다. 프론트가 신호 데이터를 재해석해 새로운 성향 문장을 만들지 않는다.

### 17.4 4축 성향

축:

- 공부형 `study`
- 책 탐색형 `book`
- 프로그램형 `program`
- 휴식형 `rest`

표시 방식:

- 기본: 수평 Progress Bar 4개
- Pie/Donut Chart는 MAY
- 시각화와 함께 각 비율을 텍스트로 제공
- 총합이 부동소수점 반올림으로 100이 아닐 수 있으면 화면 표시 시 마지막 축을 임의 조정하지 않고 서버 값을 반올림해 표시
- 데이터가 없는 상태에서는 0% Chart를 그리지 않음

### 17.5 분석 상태

| 상태 | UI |
|---|---|
| `collecting` | “활동을 조금 더 모으고 있어요.” + 탐색 CTA |
| `pending` | 기존 결과가 있으면 유지하고 “최근 활동 반영 중” 표시 |
| `ready` | 전체 분석 표시 |
| `failed` | 기존 결과 유지, 없으면 재시도·활동 목록 안내 |

`signal_count`를 그대로 사용자에게 보여줄지는 디자인 결정이지만, 내부 진단을 위해 접근 가능한 상세 설명에 포함할 수 있다.

### 17.6 많이 접한 태그

- `top_tags` 최대 응답 수만 표시
- tag label과 상대 점수 또는 횟수 — 서버가 제공할 때
- 경험·객관 태그가 함께 있을 수 있음
- 동일 label처럼 보여도 code가 다르면 별도 항목
- 태그가 없으면 섹션 숨김 또는 collecting 안내

### 17.7 관심 분야

세 그룹:

1. 책 주제 `book_subjects`
2. 프로그램 분야 `program_categories`
3. 자주 찾는 지역 `frequent_regions`

- 각 그룹 최대 5개 권장
- 값이 없는 그룹은 숨기되 전체 섹션이 비면 행동 유도 상태 표시
- 지역은 저장한 도서관 기준이며 현재 위치 이력이 아님

### 17.8 활동 개수와 목록 이동

| Count | 이동 |
|---|---|
| 저장한 도서관 | `/my-outings/libraries` |
| 저장한 책 | `/my-outings/books` |
| 저장한 프로그램 | `/my-outings/programs` |
| 좋아요한 후기 | `/my-outings/liked-reviews` |
| 내가 쓴 후기 | `/my-outings/reviews` |

카드 전체를 링크로 제공하고 개수를 텍스트로 읽을 수 있게 한다.

### 17.9 신규 회원 행동 유도

분석 신호가 없으면 다음 CTA 중 3~5개를 제공한다.

- 관심 있는 도서관 저장하기
- 책 둘러보기
- 문화 프로그램 찾아보기
- 첫 후기 작성하기
- 선호 설정하기

개인화 추천을 받으려면 반드시 모든 행동을 해야 한다는 오해를 주지 않는다.

### 17.10 저장 목록 공통 — `FR-MY-LISTS`

공통 Route:

- `/my-outings/libraries`
- `/my-outings/books`
- `/my-outings/programs`
- `/my-outings/liked-reviews`
- `/my-outings/reviews`

공통 구성:

```text
MemberSubNavigation
PageHeader + Count
정렬 또는 간단 필터
카드 목록
Pagination
```

API:

- `GET /my-outings/libraries/`
- `GET /my-outings/books/`
- `GET /my-outings/programs/`
- `GET /my-outings/liked-reviews/`
- `GET /my-outings/reviews/`

### 17.11 저장 해제와 Undo

도서관·책·프로그램 목록에서 저장 해제:

```text
DELETE 성공
→ 목록에서 제거
→ “저장을 해제했어요. 되돌리기” Toast 5초
→ 되돌리기 클릭 시 PUT
```

- Undo 요청이 실패하면 목록 재조회와 오류 안내
- 카운트와 대시보드 캐시 무효화
- 서버 재계산 중에는 대시보드가 `pending`일 수 있음

좋아요한 후기 목록에서는 LikeButton으로 좋아요 해제하며 같은 Undo 패턴을 적용할 수 있다.

### 17.12 내가 쓴 후기

- `GET /my-outings/reviews/`는 본인의 `visible`, `hidden` 후기를 모두 반환한다.
- 각 item은 `moderation_status`를 포함한다.
- `visible`: 상세, 수정, 삭제 제공
- `hidden`: “공개되지 않음” 배지, 읽기 전용 상세만 제공
- hidden 후기에서는 수정·삭제·좋아요·공유 버튼을 표시하지 않는다.
- 후기 숨김·공개 상태 변경 UI는 만들지 않으며 Django admin에서 처리한다.
- visible 후기 삭제 후 목록 count와 대시보드 count를 갱신한다.

### 17.13 완료 조건

- 비회원 접근 시 로그인 후 `/my-outings` 복귀
- collecting 상태에서 빈 Chart를 표시하지 않음
- 수동 선호와 행동 성향을 하나의 퍼센트로 혼합해 표시하지 않음
- 저장 해제 후 목록·count·대시보드가 일관됨
- 현재 위치를 자주 찾는 지역으로 표시하지 않음
- hidden 후기가 본인 목록에 배지와 읽기 전용 상태로 표시됨

---

## 18. 프로필·선호 설정 명세

### 18.1 프로필 보기 — `FR-PROFILE-VIEW`

| 항목 | 명세 |
|---|---|
| Route | `/profile` |
| 접근 | 회원 |
| API | `GET /profile/` |

화면 구성:

- 프로필 이미지
- 닉네임
- 자기소개
- 저장·후기·좋아요 요약 — 응답에 있을 때
- 프로필 수정 버튼
- 선호 설정 버튼
- 이메일은 공개 정보 영역에 표시하지 않거나 계정 정보로만 제한

프로필 이미지가 없으면 fallback 이미지를 표시한다.

### 18.2 프로필 수정 — `FR-PROFILE-EDIT`

| 항목 | 명세 |
|---|---|
| Route | `/profile/edit` |
| 접근 | 회원 |
| API | `PATCH /profile/` |
| 전송 | 이미지 변경 시 multipart |

입력:

- 프로필 이미지
- 닉네임
- 자기소개
- 이미지 대체 텍스트 — UI 제공 여부 SHOULD

동작:

- 저장 전 Preview
- 이미지 삭제 계약이 있으면 “기본 이미지 사용” 제공
- 닉네임 trim 후 필수
- 자기소개 max length는 서버와 동기화
- 성공 후 authStore.user와 profileStore.profile 동시 갱신

### 18.3 선호 설정 — `FR-PREFERENCE-SETTINGS`

| 항목 | 명세 |
|---|---|
| Route | `/profile/preferences` |
| 접근 | 회원. 비회원은 페이지 mount 전 Router Guard가 차단 |
| API | `GET /profile/preferences/`, 기준정보 GET, `PUT /profile/preferences/` |

접근 시 비회원은 `/auth/login?redirect=/profile/preferences`로 이동한다. 로그인 후 설정 화면으로 복귀하되 선택값을 자동 변경하거나 저장하지 않는다.

섹션:

1. 방문 목적
2. 선호 지역
3. 선호 시설·태그
4. 저장

`PUT`은 전체 교체 방식이다. 일부 Checkbox만 변경하더라도 최종 선택 전체 배열을 전송한다.

### 18.4 데이터 초기화와 저장

```text
기존 preferences GET
+ profile purposes/tags/regions GET
→ ID 기준 선택 상태 구성
→ 사용자 변경
→ 전체 Payload 생성
→ PUT
→ 홈 개인화·나의 나들이 cache invalidation
```

중복 ID와 잘못된 기준정보는 클라이언트에서 제거·차단하고 서버 검증 오류도 표시한다.

### 18.5 선호 의미 안내

- 선호 목적은 개인화 추천에 사용
- 선호 시설은 실제 도서관의 객관 시설 태그와 비교
- 선호 지역은 계정에 저장
- 현재 위치 좌표는 저장하지 않음
- `nearby` 목적을 선택해도 가까운 곳 계산 시 브라우저 위치 권한이 별도로 필요
- `program`은 프로필 목적에는 있을 수 있지만 홈 공개 테마에는 표시되지 않음

### 18.6 변경사항 보호

- 선택 변경 후 이탈 시 확인
- 저장 중 모든 Checkbox를 막기보다 저장 버튼과 중복 제출만 막고, 데이터 변경은 가능하면 제한
- 저장 성공 후 “선호 설정을 저장했어요.” Toast
- 실패 시 선택 상태 유지

### 18.7 완료 조건

- 전체 교체 PUT Payload가 현재 모든 선택을 포함
- `program` 목적이 profile context에는 표시되고 home context에는 표시되지 않음
- 좌표를 preference Payload에 보내지 않음
- 저장 후 홈 개인화가 새로 조회됨

---

## 19. 시스템 페이지 명세

### 19.1 404 — `FR-SYSTEM-404`

- 존재하지 않는 Route 또는 삭제된 공개 자원
- “페이지를 찾을 수 없습니다.”
- 홈, 이전 페이지, 해당 자원 목록 CTA
- 내부 오류 상세나 Stack Trace 노출 금지

### 19.2 403 — `FR-SYSTEM-403`

- 로그인은 되어 있으나 권한 없음
- 후기 수정 등 대상 자원 상세 또는 커뮤니티로 이동
- 재로그인으로 해결되지 않는 권한 문제임을 설명

### 19.3 서비스 오류 — `FR-SYSTEM-ERROR`

- 반복되는 5xx 또는 앱 초기화 실패
- 다시 시도, 홈 이동
- 서버 요청 ID가 응답 Header 또는 body에 있으면 사용자 문의용으로 표시 가능

### 19.4 오프라인

- `navigator.onLine`은 참고 신호로만 사용
- 진행 중 입력은 유지
- 읽기 화면에 캐시가 있으면 “오프라인 상태의 이전 정보”임을 안내
- 저장·좋아요·제출을 자동 Queue하지 않음

---

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

### 20.2 Container

- 기본 `container` 사용
- 상세 본문 최대 폭은 가독성을 위해 1200px 내외
- Form 중심 화면은 640~720px 내외
- 모바일 좌우 여백 최소 16px

### 20.3 카드 Grid

| 카드 | xs | md | lg | xl 이상 |
|---|---:|---:|---:|---:|
| 도서관 | 1 | 2 | 3 | 3~4 |
| 책 | 2 | 3 | 4 | 5~6 |
| 프로그램 | 1 | 2 | 3 | 3 |
| 후기 | 1 | 1~2 | 2 | 2~3 |

책 카드의 2열 모바일은 표지와 텍스트 가독성이 확보되는 경우에만 사용하며, 작은 화면에서는 1열로 자동 전환할 수 있다.

### 20.4 필터

- `lg` 이상: 고정 Sidebar
- `lg` 미만: Filter Drawer
- Drawer 임시 선택은 적용 전 Route에 반영하지 않음
- 활성 필터 Chip은 화면 폭을 넘으면 줄바꿈

### 20.5 상세 Hero

- 데스크톱: 이미지와 요약 2열
- 모바일: 이미지 상단, 정보 하단
- 저장 버튼은 모바일에서 화면 하단 Sticky CTA로 MAY 제공
- Sticky CTA가 콘텐츠나 브라우저 안전 영역을 가리지 않게 padding 적용

### 20.6 표와 긴 데이터

- 운영시간·통계는 모바일에서 definition list 또는 카드로 전환
- 가로 Scroll 표 사용을 최소화
- 긴 URL은 실제 문자열을 그대로 노출하지 않고 의미 있는 link label 사용

### 20.7 터치

- 주요 터치 영역 최소 44×44 CSS px
- 인접 아이콘 버튼 간 최소 8px 간격
- hover 전용 정보 없이 tap·focus 대체 제공

---


### 20.8 모바일 하단 내비게이션

- `lg` 미만에서 홈, 도서관, 책, 프로그램, 커뮤니티 다섯 탭을 하단에 고정한다.
- 본문은 하단 내비게이션 높이와 safe area만큼 padding-bottom을 가진다.
- 가로 폭이 좁아도 label을 숨기지 않는다.
- 키보드가 열린 Form 화면에서는 브라우저 동작에 따라 겹치지 않도록 fixed 위치를 점검한다.
- 후기 작성·수정 같은 집중 Form 화면에서는 하단 탭을 숨길 수 있으며, 이 경우 명확한 뒤로 가기와 저장·취소 동작을 제공한다.

## 21. 웹 접근성 명세

### 21.1 기본 기준

WCAG 2.1 AA 수준을 목표로 한다.

- 시맨틱 HTML 우선
- 키보드 전체 사용 가능
- 명확한 Focus 표시
- 텍스트·UI 대비 준수
- 오류와 상태 변화를 스크린리더에 전달

### 21.2 페이지 구조

- `header`, `nav`, `main`, `footer` landmark 사용
- Route 변경 시 `main`의 H1으로 Focus 이동
- “본문 바로가기” 링크 제공
- H1→H2→H3 계층 유지

### 21.3 Form

- 모든 입력에 시각적 label 제공
- Placeholder만 label로 사용하지 않음
- 오류 메시지는 `aria-describedby`로 연결
- 오류가 여러 개면 Summary를 제공하고 첫 오류로 Focus
- 필수 입력은 텍스트와 `required` 속성으로 표시

### 21.4 Dialog와 Drawer

- `role=dialog`, `aria-modal=true`
- 제목 연결
- Focus Trap
- ESC 닫기
- 닫힌 뒤 Trigger로 Focus 복귀
- 파괴적 확인 Dialog는 취소 버튼을 기본 Focus로 권장

### 21.5 비동기 상태

- Toast 영역: `aria-live=polite`
- 치명적 Form 오류: `aria-live=assertive`는 제한적으로 사용
- 저장·좋아요 버튼: `aria-busy`, 상태 label 갱신
- 목록 결과 수 변경: “총 24개 결과”를 polite live region으로 안내

### 21.6 이미지

- 도서관 외관: 도서관명과 중복되지 않는 설명 또는 빈 alt 결정
- 책 표지: “{도서명} 표지”
- 프로그램 이미지: 장식이면 빈 alt, 정보가 있으면 program title 기반
- 프로필 이미지: “{닉네임} 프로필 이미지” 또는 장식 처리
- 이미지 출처 ⓘ는 키보드 Focus 가능

### 21.7 지도와 Chart

- Kakao 지도 내용의 텍스트 대체로 도로명주소와 외부 지도·길찾기 링크를 제공한다.
- 지도 canvas에만 도서관 위치 정보를 의존하지 않는다.
- 지도 조작 영역은 키보드 Focus를 가두지 않는다.
- SDK 로드 실패 안내는 `role="status"` 또는 적절한 live region으로 전달한다.
- 성향 Chart는 축 이름과 비율 목록을 함께 제공한다.
- 색상만으로 축을 구분하지 않는다.

### 21.8 모바일 내비게이션

- 하단 탭은 `nav` landmark와 명확한 label을 가진다.
- 현재 탭에는 `aria-current="page"`를 적용한다.
- 아이콘은 장식용이면 `aria-hidden="true"`, 의미 전달용이면 accessible name을 제공한다.
- 프로필 Drawer는 열릴 때 Focus를 이동하고 닫을 때 프로필 버튼으로 복귀한다.

### 21.9 모션

`prefers-reduced-motion: reduce`에서 다음을 축소한다.

- Drawer·Dialog animation
- Skeleton shimmer
- Scroll animation
- Chart transition

---

## 22. 보안·개인정보 명세

### 22.1 API Key

- Vue에서 직접 사용하는 외부 서비스는 Kakao Map JavaScript SDK뿐이다.
- `VITE_KAKAO_MAP_APP_KEY`는 브라우저에 노출되는 JavaScript 공개키이며 Kakao Developers의 허용 도메인을 개발·운영 환경으로 제한한다.
- 정보나루, GMS, 공공데이터포털 API는 `Vue → Django → 외부 API → Django → Vue` 흐름만 사용한다.
- 정보나루·GMS·공공데이터 인증키가 브라우저 Network, source map, 번들, 로그에 나타나면 결함으로 처리한다.
- `.env`의 `VITE_*`에는 공개 가능한 값만 사용한다.

### 22.2 인증 정보

- access token은 Pinia 메모리에만 유지하고 localStorage·sessionStorage·IndexedDB에 저장하지 않는다.
- refresh token은 HttpOnly cookie로 관리하며 JavaScript에서 읽지 않는다.
- production cookie는 `Secure`를 사용하고 SameSite·Origin 정책은 Django와 동일 사이트 배포 기준으로 설정한다.
- 모든 Axios 요청은 `withCredentials=true`를 사용한다.
- refresh는 single-flight로 수행하고 실패하면 전체 Store를 초기화한다.
- 로그아웃 시 모든 Pinia Store, pending intent, 개인 초안, 사용자 전용 cache를 제거한다.
- 공개 검색 Query는 URL에 남아 있을 수 있으나 사용자별 응답 데이터는 제거한다.

### 22.3 XSS와 출력

- 후기, 자기소개, 책 소개, 프로그램 원문 메타를 plain text로 출력
- `v-html` 금지
- URL은 서버가 정규화하더라도 `http:`·`https:`만 허용
- `javascript:` URL 렌더링 금지
- 외부 링크에 `noopener noreferrer`

### 22.4 현재 위치

- 사용자 동의 후에만 사용
- 좌표를 localStorage, sessionStorage, IndexedDB, 분석 로그에 저장하지 않음
- API 요청이 끝난 뒤 메모리 Store에서 사용자가 지울 수 있게 “위치 초기화” 제공 SHOULD
- Route Query와 공유 URL에 정확한 좌표를 포함하지 않음

### 22.5 이미지 업로드

- 브라우저 `accept`는 편의 기능이며 서버 검증을 대체하지 않음
- 파일명·경로를 신뢰하지 않음
- Preview URL을 외부로 전송하지 않음
- 실패 응답에 서버 파일 경로나 Stack Trace를 사용자에게 노출하지 않음

### 22.6 로그

프론트 오류 로그에서 다음을 제외한다.

- 비밀번호
- 인증 token
- 정확한 현재 위치
- 후기 작성 중 미제출 본문
- 사용자 선택 이미지 원본
- API Key

---

## 23. 성능·사용자 경험 명세

### 23.1 Route Lazy Loading

모든 Page Component는 동적 import를 사용한다.

```js
const LibraryDetailView = () => import('@/pages/libraries/LibraryDetailView.vue')
```

공통 Header·Router·Pinia·필수 CSS만 초기 Bundle에 포함한다.

### 23.2 이미지

- 목록 이미지는 `loading="lazy"`, `decoding="async"`
- 첫 화면 핵심 이미지 1~2개는 lazy 제외 가능
- 서버가 Thumbnail URL을 제공하면 원본 대신 사용
- 책 표지와 외관 사진의 고정 aspect ratio로 Layout Shift 방지
- 이미지 실패 이벤트의 무한 fallback loop 방지

### 23.3 요청 최적화

- 동일 상세 ID의 동시 GET deduplicate
- 검색 Query 변경 시 이전 요청 취소
- 기준정보 병렬 조회
- 상세와 관련 preview가 한 응답에 있으면 중복 API 호출 금지
- 후기 상세를 hover prefetch하지 않음 — 조회수 증가 부작용 방지
- 목록 재조회 중 기존 결과 유지

### 23.4 렌더링

- 카드 수가 서버 페이지 크기 20 수준이므로 v1.1에서 Virtual Scroll 불필요
- Chart library는 필요 화면에서만 lazy import
- Kakao Map SDK는 도서관 상세의 MapPanel mount 시 동적으로 로드하며 동일 script와 Promise를 재사용한다. IntersectionObserver 기반 추가 지연 로드는 선택 사항이다.
- 큰 태그 목록은 그룹 단위 접기 제공 가능

### 23.5 목표

정량 목표는 운영 측정 환경에 따라 조정하되 다음을 권장한다.

- 초기 public Route의 불필요한 JS 최소화
- 주요 화면의 LCP 2.5초 이내 목표
- CLS 0.1 이하 목표
- 입력 반응 200ms 이내 체감
- 저장·좋아요 즉시 피드백 100ms 이내

### 23.6 느린 네트워크

- 300ms 미만 요청에는 Spinner를 지연 표시해 깜빡임 방지 가능
- 1초 이상이면 Skeleton 표시
- 10초 이상이면 “불러오는 데 시간이 걸리고 있어요.” 안내
- Timeout 후 사용자가 명시적으로 재시도

---

## 24. 테스트 명세

### 24.1 테스트 계층

| 계층 | 대상 | 도구 |
|---|---|---|
| Unit | Query 직렬화, 상태 label, validator, formatter | Vitest |
| Store | Action 성공·실패·rollback·invalidation | Vitest |
| Component | 카드, Filter, Dialog, Form | Vue Test Utils |
| Contract Mock | API 응답 형태와 오류 처리 | MSW 권장 |
| E2E | 핵심 사용자 흐름 | Playwright 권장 |
| Accessibility | Keyboard, axe 검사 | axe-core 또는 수동 |

### 24.2 필수 Unit Test

- 쉼표 다중 Query parse·serialize
- 기본값 Query 제거
- 필터 변경 시 page 초기화
- `open_today` null·true·false label
- 프로그램 상태 label
- 거리·숫자·날짜 formatter
- 후기 1~200자와 태그 1~5개 validator
- 안전한 내부 redirect validator
- 401 동시 요청의 single-flight refresh와 1회 재시도
- refresh 실패 시 전체 Store 초기화
- 위치 좌표가 URL에 포함되지 않는지

### 24.3 필수 Component Test

- `SaveButton`: guest, false, true, loading, rollback
- `LikeButton`: count 증가·감소·0 하한
- `LibraryCard`: 내부 저장 버튼 클릭 시 상세 이동이 발생하지 않음
- `AttributionOverlay`: hover·focus·tap·ESC
- `FilterDrawer`: 적용·취소·Focus 복귀
- `ReviewForm`: 글자 수, 태그 제한, image 제한
- `MapPanel`: SDK 성공·key 누락·좌표 없음·로드 실패
- `MobileBottomNavigation`: 현재 Route와 aria-current
- hidden 후기 카드: 배지와 수정 버튼 미표시
- `EmptyState`, `ErrorState`, `LoadingSkeleton`

### 24.4 필수 E2E 시나리오

#### E2E-01 비회원 도서관 탐색

```text
홈
→ 아이와 가기 좋은 곳
→ 도서관 목록
→ 어린이자료실 필터
→ 상세
→ 저장 클릭
→ 로그인 화면
```

#### E2E-02 로그인 후 저장 복구

```text
비회원 상세에서 저장
→ 로그인
→ 원 상세 복귀
→ 저장 자동 실행
→ 나의 나들이 저장 목록 확인
```

#### E2E-03 책 기반 방문지 탐색

```text
책 둘러보기
→ 도서 검색
→ 책 상세
→ 부산 소장 도서관
→ 도서관 상세
```

#### E2E-04 프로그램 원문

```text
프로그램 필터
→ 상세
→ 운영 도서관 이동
→ 원문 정보 확인 CTA가 새 탭 속성 보유
```

#### E2E-05 후기 작성

```text
로그인
→ 도서관 상세
→ 후기 작성
→ 도서관 선선택
→ 본문·태그·관련 프로그램 입력
→ 등록
→ 후기 상세
```

#### E2E-06 후기 좋아요

```text
비회원 후기 좋아요
→ 로그인
→ 원 후기 복귀
→ 좋아요 자동 처리
→ 나의 나들이 좋아요한 후기 확인
```

#### E2E-07 선호 설정 접근과 저장

```text
비회원이 /profile/preferences 직접 접근
→ 설정 화면 미표시
→ 로그인
→ /profile/preferences 복귀
→ program 목적과 시설 태그 선택
→ 사용자가 저장
→ 홈 개인화 재조회
```

#### E2E-08 위치 거절

```text
홈 가까운 곳
→ 위치 설명
→ 권한 거절
→ 오류 페이지가 아닌 지역 탐색 CTA
```

#### E2E-09 access token 자동 갱신

```text
로그인 상태에서 보호 API 요청
→ access token 만료로 401
→ refresh cookie로 자동 갱신
→ 원 요청 1회 재시도
→ 현재 화면과 입력 상태 유지
```

#### E2E-10 refresh 실패

```text
만료된 refresh cookie 상태에서 보호 API 요청
→ refresh 실패
→ 모든 Store 초기화
→ 로그인 화면
→ 안전한 redirect 유지
```

#### E2E-11 후기 수정 권한

```text
비회원이 /reviews/{id}/edit 직접 접근
→ 로그인
→ 원 edit Route 복귀
→ 타인 후기이면 403
→ hidden 본인 후기이면 읽기 전용 상세
```

#### E2E-12 Kakao 지도

```text
좌표가 있는 도서관 상세
→ Kakao SDK 동적 로드
→ 단일 마커 표시
→ 지도에서 보기·길찾기 링크 확인
→ SDK 실패 fixture에서는 주소 대체 UI 확인
```

### 24.5 접근성 수동 점검

- 마우스 없이 Header부터 Footer까지 이동
- Modal·Drawer Focus Trap
- Route 전환 후 H1 Focus
- 색상 제거 상태에서 선택·상태 식별
- 200% Zoom에서 콘텐츠 손실 없음
- Screen Reader로 저장·좋아요 상태 변경 확인

### 24.6 Mock Fixture

최소 Fixture는 다음 경우를 포함한다.

- 이미지와 출처가 있는 도서관
- fallback 이미지 도서관
- 운영 중, 오늘 운영이지만 현재 닫힘, 휴관, unknown
- 시설 profile 없음과 일부 null
- 개인화 available true·false
- stale 인기 도서
- 날짜 일부가 없는 프로그램
- 이미지·관련 책·프로그램이 있는 후기
- collecting·pending·ready·failed 대시보드
- visible·hidden 본인 후기
- 좌표 있음·없음 도서관과 Kakao SDK 실패

---

## 25. 구현 우선순위와 단계

### 25.1 우선순위

| 우선순위 | 범위 |
|---|---|
| P0 | Router, Layout, API client, 인증, 기준정보, 도서관 목록·상세, 홈, 공통 카드·상태 |
| P0 | 책 검색·상세·소장 도서관, 프로그램 목록·상세 |
| P0 | 커뮤니티 목록·상세·작성·좋아요 |
| P0 | 저장 기능, 나의 나들이 기본 목록·대시보드 |
| P1 | 프로필·선호 설정, 후기 수정·삭제, 위치 nearby |
| P1 | Kakao 지도, 출처 오버레이, 접근성·반응형 완성, 캐시 무효화 정교화 |
| P2 | Undo, Share, 고급 Chart, IntersectionObserver 기반 지도 추가 지연, 추가 애니메이션 |

### 25.2 권장 구현 순서

#### Phase 1. 기반

1. Vite·Vue·Router·Pinia·Axios 구성
2. Layout·Header·Footer·System Page
3. API client와 공통 오류
4. JWT 인증 Store·refresh interceptor·Guard
5. 기준정보 Store
6. 공통 Skeleton·Empty·Error·Dialog·Toast

#### Phase 2. 공개 탐색

1. 홈
2. 도서관 목록과 Query 동기화
3. 도서관 상세와 Kakao MapPanel
4. 책 목록·상세
5. 프로그램 목록·상세

#### Phase 3. 회원 행동·커뮤니티

1. SaveButton·LikeButton·AuthGate
2. 커뮤니티 목록·상세
3. 후기 작성·수정·삭제
4. 작성 초안과 이미지 업로드

#### Phase 4. 개인 영역

1. 나의 나들이 대시보드
2. 저장·좋아요·내 후기 목록
3. 프로필
4. 선호 설정·온보딩
5. cache invalidation 연결

#### Phase 5. 품질

1. 반응형
2. 접근성
3. 성능
4. Unit·E2E
5. Build·배포 점검

### 25.3 작업 분리 예시

| 역할 | 담당 가능 영역 |
|---|---|
| A | App 기반, 인증, Header, Router, 공통 상태 |
| B | 홈·도서관 목록·상세 |
| C | 책·프로그램 |
| D | 커뮤니티·후기 Form |
| E | 나의 나들이·프로필·선호, 테스트·접근성 |

공통 DTO와 컴포넌트 계약을 먼저 합의해 병렬 개발의 충돌을 줄인다.

---

## 26. 완료 기준

### 26.1 기능 완료

- 모든 Route가 새로고침과 직접 URL 접근에서 동작
- 회원·비회원 권한 분기가 명세와 일치
- JWT access 만료 시 자동 refresh 후 원 요청 재시도
- refresh 실패·로그아웃 시 전체 Store 초기화
- 저장·좋아요가 idempotent API와 연결
- 후기 생성·수정·삭제·좋아요 동작
- URL Query로 목록 상태 복원
- 나의 나들이 데이터가 행동 후 갱신
- 위치 권한 거절 대체 흐름 동작
- Kakao 지도 단일 마커와 지도 실패 대체 UI 동작
- hidden 후기가 본인에게만 읽기 전용으로 표시

### 26.2 데이터 정확성

- `unknown`과 `false`를 혼합하지 않음
- 시설 `null`을 시설 없음으로 표시하지 않음
- 소장 정보를 대출 가능으로 표시하지 않음
- 프로그램 원문 CTA를 내부 신청으로 표현하지 않음
- 책 저장에 내부 ID 사용
- 외부 이미지 출처 문구 보존

### 26.3 품질 완료

- Chrome 최신 버전에서 핵심 흐름 동작
- 모바일 360px 폭에서 가로 Scroll 없이 주요 화면 사용 가능
- 키보드로 핵심 흐름 완료 가능
- Console error 없음
- Kakao JavaScript Key 외의 API Key와 민감정보가 번들·Network·로그에 비노출
- Production build 성공
- 핵심 Unit·E2E Test 통과

---

## 27. 확정 정책 및 남은 계약

### 27.1 v1.1 확정 정책

- 인증은 JWT를 사용한다.
- access token은 Pinia 메모리에 유지한다.
- refresh token은 HttpOnly cookie로 관리한다.
- 401은 single-flight refresh 후 원 요청을 한 번 재시도한다.
- 로그인 후 안전한 `redirect` query로 원래 Route에 복귀한다.
- 로그아웃과 refresh 실패 시 전체 Pinia Store를 초기화한다.
- 저장·좋아요만 로그인 후 자동 재실행한다.
- 후기 작성·수정·선호 설정은 인증 전에 접근을 차단하고 자동 제출·저장하지 않는다.
- 지도는 Kakao Map JavaScript SDK를 사용하고 도서관 상세에서 동적으로 로드한다.
- 후기 생성은 이미지와 관계 데이터를 포함한 단일 multipart 요청으로 처리한다.
- 목록은 페이지 번호 방식으로 구현하고 무한 스크롤을 사용하지 않는다.
- 모바일 하단 탭은 홈, 도서관, 책, 프로그램, 커뮤니티로 구성한다.
- 나의 나들이·프로필·선호 설정은 프로필 메뉴에 배치한다.
- 후기 숨김 처리는 Django admin에서 수행한다.
- hidden 후기는 작성자에게만 “공개되지 않음” 배지와 읽기 전용 화면으로 제공한다.
- 디자인은 첨부 시안의 녹색·아이보리·둥근 카드·태그 chip·정보 카드 grid를 참고하되 기능 명세를 우선한다.

### 27.2 v1.1 보류 범위

- 별도 SPA 관리자 페이지
- 내부 프로그램 신청·예약·결제
- 실시간 열람실 잔여 좌석
- Kakao 지도 기반 복잡한 경로·교통·Roadview·장소 검색
- 후기 자동 태깅
- AI가 직접 결정하는 추천 순위
- 무한 스크롤
- 회원 간 팔로우·알림 기능

### 27.3 구현 전에 백엔드와 확인할 계약

1. 로그인·refresh 응답의 정확한 access token field명과 사용자 정보 포함 여부
2. refresh·logout endpoint의 정확한 URL과 cookie path·SameSite 정책
3. 회원가입 성공 시 자동 로그인 여부
4. 프로필 응답의 정확한 count·이미지 field 구조
5. 후기 multipart의 `tag_ids`, `book_ids`, `program_ids` 배열 직렬화 방식
6. 후기 수정 시 기존 이미지 삭제·순서 변경 API
7. 프로그램 일반 목록의 도서관 Combobox용 간단 검색 API 사용 방식
8. 도서관 상세 응답에 관련 프로그램·후기 preview가 포함되는지 별도 API를 호출하는지
9. 홈·상세 추천 카드에 추천 이유가 추가되는지
10. 저장 memo를 후속 버전에서 UI에 노출할지
11. 프로필 이미지 삭제 방식
12. Backend pagination의 `page_size` 최대값
13. pending intent 유효시간과 서버 상태 확인 방식

남은 항목은 `TBD`로 관리하되, 위에서 확정한 인증·지도·페이지네이션·숨김 후기·모바일 내비게이션 정책을 다시 미결정 상태로 되돌리지 않는다.

---

## 28. API–화면 매핑

| 화면 | Method | Endpoint | 용도 |
|---|---|---|---|
| 로그인 | POST | `/auth/login/` | access token 발급 + refresh cookie 설정 |
| 인증 갱신 | POST | `/auth/refresh/` | HttpOnly refresh cookie로 access 갱신 |
| 회원가입 | POST | `/auth/signup/` | 계정 생성 |
| 공통 | POST | `/auth/logout/` | refresh cookie 폐기 + 전체 Store 초기화 |
| 프로필 | GET/PATCH | `/profile/` | 프로필 조회·수정 |
| 선호 설정 | GET/PUT | `/profile/preferences/` | 전체 선호 조회·교체 |
| 기준정보 | GET | `/purposes/?context=home` | 홈 테마 |
| 기준정보 | GET | `/purposes/?context=profile` | 선호 목적 |
| 기준정보 | GET | `/tags/?context=profile` | 선호 태그 |
| 기준정보 | GET | `/tags/?context=review` | 후기 태그 |
| 기준정보 | GET | `/regions/` | 부산 구·군 |
| 홈 | GET | `/home/recommendations/` | 오늘·개인화·테마 |
| 홈 | GET | `/home/theme-recommendations/` | 테마 preview |
| 도서관 목록 | GET | `/libraries/` | 검색·필터·정렬 |
| 도서관 상세 | GET | `/libraries/{id}/` | 상세 |
| 도서관 상세 | GET | `/libraries/{id}/similar/` | 비슷한 도서관 |
| 도서관 관련 | GET | `/libraries/{id}/programs/` | 관련 프로그램 |
| 도서관 관련 | GET | `/libraries/{id}/reviews/` | 관련 후기 |
| 책 | GET | `/popular-books/` | 주간 인기 |
| 책 | GET | `/books/search/` | 외부 검색 정규화 |
| 책 상세 | GET | `/books/{isbn13}/` | 상세 |
| 책 상세 | GET | `/books/{isbn13}/libraries/` | 부산 소장 도서관 |
| 프로그램 | GET | `/programs/` | 목록 |
| 프로그램 상세 | GET | `/programs/{id}/` | 상세 |
| 커뮤니티 | GET/POST | `/reviews/` | 목록·작성 |
| 후기 상세 | GET/PATCH/DELETE | `/reviews/{id}/` | 상세·수정·삭제 |
| 좋아요 | PUT/DELETE | `/reviews/{id}/like/` | 좋아요 토글 |
| 저장 | PUT/DELETE | `/my-outings/libraries/{id}/` | 도서관 저장 |
| 저장 | PUT/DELETE | `/my-outings/books/{book_id}/` | 책 저장 |
| 저장 | PUT/DELETE | `/my-outings/programs/{id}/` | 프로그램 저장 |
| 나의 나들이 | GET | `/my-outings/dashboard/` | 통합 분석 |
| 나의 나들이 | GET | `/my-outings/libraries/` | 저장 도서관 |
| 나의 나들이 | GET | `/my-outings/books/` | 저장 책 |
| 나의 나들이 | GET | `/my-outings/programs/` | 저장 프로그램 |
| 나의 나들이 | GET | `/my-outings/liked-reviews/` | 좋아요 후기 |
| 나의 나들이 | GET | `/my-outings/reviews/` | 내가 쓴 후기 |

---

# 부록 A. 목록 Query 사전

## A.1 도서관

| Query | 형식 | 기본 | UI |
|---|---|---|---|
| `q` | string | 없음 | 검색어 |
| `sigungu` | CSV | 없음 | 지역 다중 선택 |
| `library_type` | CSV | 없음 | 유형 다중 선택 |
| `purpose` | enum | 없음 | 공개 테마 단일 선택 |
| `facility` | CSV | 없음 | 시설 다중 선택 |
| `open_today` | boolean | 없음 | 오늘 운영 |
| `open_now` | boolean | 없음 | 지금 운영 |
| `weekend_open` | boolean | 없음 | 주말 운영 |
| `holiday_status` | enum | 없음 | 공휴일 open·closed·unknown |
| `holiday_date` | date | 가장 가까운 공휴일 | 고급 필터 MAY |
| `late_open_after` | HH:mm | 없음 | 늦게까지 운영 18:00 |
| `min_book_count` | integer | 없음 | 최소 장서 |
| `max_book_count` | integer | 없음 | 최대 장서 |
| `min_reading_seat_count` | integer | 없음 | 최소 좌석 |
| `max_reading_seat_count` | integer | 없음 | 최대 좌석 |
| `radius_km` | number | 없음 | 반경 |
| `ordering` | enum | 서버 기본 | 정렬 |
| `page` | integer | 1 | 페이지 |
| `page_size` | integer | 20 | v1.1 UI에서 기본값 유지 |

`lat`, `lng`는 API 요청용이며 Browser Route Query에서 제외한다.

## A.2 책

| Query | 형식 |
|---|---|
| `search_type` | `title|author|isbn|keyword|publisher` |
| `q` | string |
| `sort` | `loan|title|author|pub|pubYear|isbn` |
| `order` | `asc|desc` |
| `page` | integer |
| `page_size` | integer |

## A.3 프로그램

| Query | 형식 |
|---|---|
| `q` | string |
| `library_id` | integer |
| `sigungu` | string 또는 CSV — 백엔드 계약에 맞춤 |
| `category` | CSV |
| `target` | CSV |
| `application_status` | CSV |
| `operation_status` | CSV |
| `ordering` | enum |
| `page` | integer |

## A.4 커뮤니티

| Query | 형식 |
|---|---|
| `q` | string |
| `library_id` | integer |
| `tag` | CSV tag code |
| `ordering` | `-created_at|-view_count|-like_count` |
| `page` | integer |

---

# 부록 B. 상태 표시 사전

## B.1 도서관 운영

| 상태 | Badge | 설명 |
|---|---|---|
| 현재 운영 | 지금 운영 중 | `open_now=true` |
| 오늘 운영 | 오늘 운영 | 현재 시간 외 또는 시간 미확인 |
| 휴관 | 오늘 휴관 | `open_today=false` |
| 미확인 | 운영 정보 확인 필요 | `open_today=null` |

## B.2 프로그램 신청

| 값 | 표시 |
|---|---|
| `신청가능` | 신청가능 |
| `신청마감` | 신청마감 |
| `신청없음` | 신청정보 없음 |
| `null` | 신청 상태 확인 필요 또는 미표시 |

## B.3 프로그램 운영

| 값 | 표시 |
|---|---|
| `예정` | 예정 |
| `진행중` | 진행중 |
| `종료` | 종료 |
| `null` | 운영 상태 확인 필요 |

## B.4 개인 성향

| 값 | 표시 |
|---|---|
| `collecting` | 활동 수집 중 |
| `pending` | 최근 활동 반영 중 |
| `ready` | 분석 완료 |
| `failed` | 분석 업데이트 지연 |

---

# 부록 C. Mutation 후 캐시 무효화

| Mutation | 즉시 수정 | 무효화 |
|---|---|---|
| 도서관 저장·해제 | 현재 카드·상세 `is_saved` | 홈 개인화, 나의 나들이 도서관, 대시보드 |
| 책 저장·해제 | 책 상세 `is_saved` | 홈 개인화, 나의 나들이 책, 대시보드 |
| 프로그램 저장·해제 | 카드·상세 `is_saved` | 홈 개인화, 나의 나들이 프로그램, 대시보드 |
| 후기 좋아요·해제 | `is_liked`, `like_count` | 커뮤니티 목록·상세, 좋아요 후기, 홈 개인화, 대시보드 |
| 후기 생성 | 새 상세 이동 | 커뮤니티, 도서관 상세 후기 preview, 내 후기, 홈 개인화, 대시보드 |
| 후기 수정 | 현재 상세 | 커뮤니티, 도서관 상세, 내 후기, 홈 개인화, 대시보드 |
| 후기 삭제 | 목록에서 제거 | 커뮤니티, 도서관 상세, 내 후기, 좋아요 목록, 홈 개인화, 대시보드 |
| 선호 설정 | profileStore preferences | 홈 전체, 대시보드 상태 |
| 프로필 수정 | auth user·profile | Header, 프로필, 대시보드 profile |

---

# 부록 D. Pending Intent 계약

```ts
type PendingIntent = {
  type: 'save-library' | 'save-book' | 'save-program' | 'like-review'
  resourceId: number
  targetState: true
  redirect: string
  createdAt: string
}
```

규칙:

- 자동 재실행은 저장·좋아요처럼 멱등 목표 상태가 명확한 행동만 허용한다.
- 후기 작성·후기 수정·선호 설정은 PendingIntent를 만들지 않고 `redirect` query만 사용한다.
- `sessionStorage`에 하나만 저장한다.
- 기본 30분 경과 시 자동 폐기한다.
- 로그인 후 redirect 대상 화면에서 현재 서버 상태를 확인한 뒤 필요한 경우에만 1회 실행한다.
- 성공적으로 소비하면 즉시 삭제한다.
- 같은 자원이 이미 목표 상태이면 추가 요청 없이 완료한다.
- 안전한 내부 redirect만 허용한다.
- 사용자가 로그인 화면에서 취소해도 원래 공개 화면으로 돌아갈 수 있다.

# 부록 E. 공통 문구

| 상황 | 문구 |
|---|---|
| 저장 성공 | 저장했어요. |
| 저장 해제 | 저장을 해제했어요. |
| 로그인 필요 | 이 기능은 로그인 후 사용할 수 있어요. 로그인하면 원래 화면으로 돌아옵니다. |
| 위치 설명 | 가까운 도서관을 찾기 위해 현재 위치를 사용합니다. 위치는 계정에 저장하지 않아요. |
| 위치 거절 | 위치를 확인할 수 없어요. 지역을 선택해 찾아보세요. |
| 운영 미확인 | 오늘 운영 정보 확인 필요 |
| 시설 미수집 | 확인된 시설 정보가 아직 없습니다. |
| 인기 데이터 stale | 최근 정상 수집된 결과를 보여드리고 있어요. |
| 프로그램 원문 | 원문에서 신청 정보 확인 |
| 후기 삭제 확인 | 이 후기를 삭제할까요? 삭제한 후기는 되돌릴 수 없습니다. |
| 작성 이탈 | 작성 중인 내용이 사라질 수 있습니다. 나갈까요? |
| 숨김 후기 | 공개되지 않음 |
| 지도 오류 | 지도를 불러오지 못했어요. 주소와 외부 지도 링크를 이용해 주세요. |

---

# 부록 F. 화면별 핵심 완료 체크리스트

## 인증·공통 내비게이션

- [ ] access token 메모리 저장
- [ ] refresh token HttpOnly cookie 사용
- [ ] 동시 401 single-flight refresh
- [ ] refresh 실패·로그아웃 전체 Store 초기화
- [ ] 모바일 하단 탭 5개와 프로필 메뉴 분리
- [ ] 보호 Route가 비회원 상태에서 mount되지 않음

## 홈

- [ ] 오늘 추천 최대 3개
- [ ] 개인화 unavailable 시 섹션 숨김
- [ ] 홈 테마 5개만 표시
- [ ] nearby에서만 위치 요청

## 도서관

- [ ] Query로 필터 복원
- [ ] unknown과 closed 구분
- [ ] 시설 True만 Chip
- [ ] 출처 오버레이 접근 가능
- [ ] 상세 뒤로 가기 시 목록 상태·스크롤 복원
- [ ] Kakao 지도 단일 마커·외부 링크·실패 대체 UI

## 책

- [ ] 검색 조건 없이 외부 전체 검색 요청 금지
- [ ] stale 표시
- [ ] 상세에 내부 book id 포함
- [ ] 소장과 대출 가능 구분

## 프로그램

- [ ] 신청 상태와 운영 상태 분리
- [ ] 내부 신청 CTA 없음
- [ ] 원문 링크 외부 표시

## 커뮤니티

- [ ] 본문 1~200자
- [ ] 태그 1~5개
- [ ] 관련 책·프로그램 각 최대 5개
- [ ] 이미지 최대 5장
- [ ] 상세 GET 중복 방지
- [ ] 작성자 수정·삭제 권한
- [ ] hidden 후기는 본인에게 배지와 읽기 전용으로 표시
- [ ] 후기 작성은 단일 multipart 요청

## 나의 나들이

- [ ] 4축 텍스트 대체 제공
- [ ] collecting·pending·ready·failed 처리
- [ ] 저장 목록과 count 일치
- [ ] 활동 후 캐시 무효화

## 프로필·선호

- [ ] 전체 교체 PUT
- [ ] program 목적 profile에 노출
- [ ] 위치 좌표 미저장
- [ ] 변경사항 이탈 보호
- [ ] 비회원은 선호 설정 화면 mount 전 차단

---

# 부록 G. 참고 문서

1. `(26_0622) 관통템플릿_Python_자율_15기_13회차.pdf`
2. `메인페이지에 대한 간단한 서술.pdf`
3. `도서관 나들이 주요 페이지 구조.txt`
4. `library_outing_Django_spec_v3.md`
5. `library_outing_ERD_v3.md`
6. `LibraryBigdata_API_Manual.pdf`
7. `데이터셋 정보.pdf`
8. `GMS 사용법.pdf`
9. `전국도서관표준데이터_부산.json`
10. `도서관시설데이터.json`
11. `LibraryImage.csv`
12. 대화에서 제공된 디자인 참고 시안 7종

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| 1.0 | 2026-06-23 | Vue SPA 전체 Route, 권한, 상태, API, 페이지, 반응형, 접근성, 테스트 명세 최초 작성 |
| 1.1 | 2026-06-24 | JWT·HttpOnly refresh cookie, 자동 갱신, 전체 Store 초기화, Kakao 지도, 단일 multipart 후기, 페이지 번호 방식, 모바일 하단 탭, Django admin 후기 숨김, 디자인 시안 반영 정책 확정 |
