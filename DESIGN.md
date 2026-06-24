# 도서관 나들이 DESIGN.md v1.2

* 문서 버전: 1.2
* 작성 기준: 도서관 나들이 Vue 3 SPA / Django REST API `/api/v1`
* 적용 범위: 홈, 도서관 찾기, 책 둘러보기, 문화 프로그램, 커뮤니티, 나의 나들이, 도서관 상세, 인증·프로필·선호 설정
* 문서 성격: 기존 기능 명세와 API 계약을 바꾸지 않는 UI 디자인 기준 문서

---

## 0. 문서 목적

이 문서는 “도서관 나들이” 서비스의 화면을 일관된 시각 언어로 구현하기 위한 디자인 기준이다.

DESIGN.md는 다음을 정의한다.

* 서비스의 시각 정체성
* 웹 우선 레이아웃 원칙
* 색상, 타이포그래피, 여백, 카드, 버튼, 칩 스타일
* Bootstrap 5.3 사용 및 override 원칙
* 이미지와 fallback 이미지 사용 규칙
* 출처 표시 방식
* 로딩·빈 상태·오류 상태 UX
* 페이지별 디자인 방향
* 접근성·반응형 기준
* 금지 디자인 패턴

이 문서는 다음을 변경하지 않는다.

* API endpoint
* Request / Response 구조
* Django model / migration
* 추천 알고리즘
* 인증 방식
* 현재 구현 범위
* 보류 기능의 우선순위

문서 간 충돌이 있을 경우 우선순위는 다음을 따른다.

1. 프론트 전달용 API 계약 문서
2. Django 개발 명세서
3. ERD 명세서
4. Frontend 개발 명세서
5. DESIGN.md
6. 기존 목업과 시각 참고 자료

---

## 1. 디자인 정체성

### 1.1 한 줄 정의

도서관 나들이는 지역 도서관, 책, 문화 프로그램, 후기를 단정하고 친근하게 탐색할 수 있는 “지역 생활형 도서관 탐색 웹서비스”다.

### 1.2 핵심 인상

전체 디자인은 다음 세 가지의 균형을 기준으로 한다.

1. 공공서비스의 신뢰감
2. 주말 나들이의 상큼함
3. 지역 생활 서비스의 친근함

서비스는 지나치게 딱딱한 행정 포털처럼 보여서는 안 되지만, 반대로 유아용 앱이나 동화책처럼 보여서도 안 된다.

### 1.3 시각 방향

기본 배경은 따뜻한 크림·아이보리 계열을 사용한다. 주요 포인트는 잎색 그린을 사용하고, 보조 포인트로 부드러운 코랄·살구·연노랑·밝은 leaf/mint 계열을 제한적으로 사용한다.

카드는 부드러운 형태를 사용하되, 장난감처럼 보이지 않도록 색상 대비와 그림자, 모서리를 절제한다.

### 1.4 피해야 할 인상

* 일반 SaaS 랜딩페이지
* 파란색 중심 공공 대시보드
* 회색 관리자 페이지
* 데스크톱에서 모바일 앱 홈처럼 보이는 화면
* 어린이 교육 앱
* 과도한 일러스트 중심 서비스
* 기능보다 감성 문구가 앞서는 랜딩 페이지

---

## 2. 시각 키워드

### 2.1 핵심 키워드

* 따뜻한
* 단정한
* 신뢰감 있는
* 산책 같은
* 지역적인
* 여유 있는
* 정보가 잘 정리된

### 2.2 보조 키워드

* 크림 배경
* 잎색 그린
* 밝은 leaf/mint
* 책과 나무
* 주말 나들이
* 동네 도서관
* 부드러운 카드
* 조용한 탐색

### 2.3 금지 키워드

* 과하게 귀여운
* 유아적인
* 장난감 같은
* 앱스토어식 교육 앱
* 차가운 관리자 페이지
* 복잡한 데이터 대시보드
* 과장된 AI 서비스

---

## 3. 웹 우선 레이아웃 원칙

도서관 나들이는 모바일 앱이 아니라 웹 우선 서비스다.

### 3.1 기본 화면 기준

* 기준 화면: 데스크톱 웹
* 기본 콘텐츠 최대 폭: `1200px`
* 넓은 화면 최대 폭: `1280px`
* 페이지 좌우 여백: `24px`
* 섹션 단위 구성 우선
* 카드 그리드와 리스트 혼합 사용

### 3.2 데스크톱 레이아웃

데스크톱에서는 상단 내비게이션을 사용한다.

상단 내비게이션 구성:

* 로고 / 서비스명
* 홈
* 도서관 찾기
* 책 둘러보기
* 문화 프로그램
* 커뮤니티
* 로그인 / 회원가입 또는 프로필 메뉴

데스크톱에서는 모바일 앱처럼 하단 탭을 중심 레이아웃으로 사용하지 않는다.

### 3.3 모바일 내비게이션 원칙

모바일 화면에서는 주요 탭 접근성을 위해 하단 탭을 사용할 수 있다.

단, 모바일 하단 탭 구조가 전체 서비스의 기준 레이아웃이 되어서는 안 된다. 디자인 기준은 항상 데스크톱 웹의 정보 구조, 상단 내비게이션, 섹션형 배치, 카드 그리드를 먼저 잡고, 모바일에서는 이를 반응형으로 축약한다.

모바일 하단 탭은 다음 용도로만 사용한다.

* 홈
* 도서관
* 책
* 프로그램
* 커뮤니티 같은 주요 공개 탭 접근
* 좁은 화면에서 반복 탐색 피로를 줄이는 보조 내비게이션

모바일 하단 탭에 모든 기능을 넣지 않는다. 나의 나들이, 프로필, 선호 설정은 Header 메뉴 또는 Drawer에서 접근할 수 있다.

### 3.4 그리드 원칙

기본 카드 그리드는 다음을 기준으로 한다.

```css
.library-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
}
```

반응형 전환:

* `1200px 이상`: 3열 중심
* `768px ~ 1199px`: 2열 중심
* `767px 이하`: 1열 중심

### 3.5 섹션 구성 원칙

각 페이지는 다음 구조를 기본으로 한다.

```text
PageHeader
→ Section / FilterArea
→ MainContent
→ Pagination 또는 MoreAction
```

홈 화면은 다음 순서를 기본으로 한다.

```text
Hero
→ 오늘의 추천 도서관
→ 테마별 추천
→ 여기는 어때요?
```

“여기는 어때요?”는 `personal_recommendations.available=true`일 때만 표시한다. 개인 추천 데이터가 충분히 안정화되고 화면 전환 흐름이 검증된 경우에만 오늘의 추천 바로 아래 등 더 높은 위치로 올릴 수 있다.

### 3.6 모바일 대응

모바일은 반응형 대응 대상이다.

* 모바일에서는 하단 탭을 사용할 수 있다.
* 데스크톱에서는 상단 내비게이션을 기준으로 한다.
* 화면 폭이 줄어들면 카드 열 수와 여백을 줄인다.
* 필터는 Drawer 또는 접힘 패널로 전환할 수 있다.
* 핵심 액션 버튼은 콘텐츠 흐름 안에 두는 것을 기본으로 한다.

---

## 4. Bootstrap 5.3 사용 원칙

도서관 나들이 프론트엔드는 Bootstrap 5.3을 사용할 수 있다. 단, Bootstrap 기본 시각 스타일을 그대로 사용하는 것이 아니라, 도서관 나들이 design token을 기준으로 재정의한다.

### 4.1 기본 원칙

* Bootstrap은 레이아웃, Grid, Utility, 기본 컴포넌트 생산성을 위해 사용한다.
* Bootstrap 기본 primary blue를 그대로 사용하지 않는다.
* 버튼, 폼, 카드, 포커스, 배지, 내비게이션은 도서관 나들이 token 기준으로 override한다.
* Bootstrap class를 사용하더라도 최종 인상은 크림·그린 중심의 도서관 나들이 디자인이어야 한다.

### 4.2 파일 구성 권장

```text
src/assets/styles/
├─ tokens.css
├─ base.css
├─ bootstrap-overrides.css
└─ components.css
```

역할:

* `tokens.css`: 색상, spacing, radius, shadow, typography token
* `base.css`: body, link, heading, layout 기본값
* `bootstrap-overrides.css`: Bootstrap 변수·컴포넌트 override
* `components.css`: 서비스 전용 카드, 버튼, 칩 등

### 4.3 Bootstrap Override 예시

Bootstrap `.card` override는 border, radius, shadow 정도만 담당한다. 카드 내부 여백은 Bootstrap의 `.card-body` 또는 서비스 전용 `.ui-card__body`에서 관리한다.

```css
:root {
  --bs-primary: var(--color-primary-700);
  --bs-primary-rgb: 56, 104, 72;
  --bs-body-bg: var(--color-bg-page);
  --bs-body-color: var(--color-text-primary);
  --bs-border-color: var(--color-border-subtle);
  --bs-link-color: var(--color-primary-700);
  --bs-link-hover-color: var(--color-primary-800);
}

.btn-primary {
  --bs-btn-bg: var(--color-primary-700);
  --bs-btn-border-color: var(--color-primary-700);
  --bs-btn-hover-bg: var(--color-primary-800);
  --bs-btn-hover-border-color: var(--color-primary-800);
  --bs-btn-active-bg: var(--color-primary-900);
  --bs-btn-active-border-color: var(--color-primary-900);
  --bs-btn-color: var(--color-text-inverse);
}

.form-control:focus,
.form-select:focus {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 0.2rem rgba(95, 147, 108, 0.24);
}

.card {
  border-color: var(--color-border-subtle);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xs);
}
```

### 4.4 Bootstrap 사용 시 주의

* `.btn-primary`가 Bootstrap 기본 blue로 남아 있으면 안 된다.
* `.card`가 기본 흰색 박스처럼만 보이면 안 된다.
* `.card`에 전역 padding을 부여하지 않는다.
* `.form-control:focus`의 파란 focus ring은 green focus ring으로 교체한다.
* Bootstrap spacing utility를 사용하더라도 주요 layout 간격은 design token 기준과 크게 벗어나지 않게 한다.
* Bootstrap table 중심 화면을 남용해 관리자 페이지처럼 보이게 만들지 않는다.

---

## 5. CSS Design Tokens

아래 값은 v1.2 초기 기준값이다. 실제 구현 중 시각 균형에 따라 조정할 수 있다.

### 5.1 Color Tokens

```css
:root {
  /* Brand Green */
  --color-primary-900: #1f3d2b;
  --color-primary-800: #2c5139;
  --color-primary-700: #386848;
  --color-primary-600: #477d58;
  --color-primary-500: #5f936c;
  --color-primary-400: #84b58d;
  --color-primary-300: #a9d0ae;
  --color-primary-200: #d7ead9;
  --color-primary-100: #edf7ee;

  /* Light Leaf / Mint Accent */
  --color-leaf-200: #dff0df;
  --color-leaf-100: #eff8ef;
  --color-mint-200: #d7f0e8;
  --color-mint-100: #eefaf6;

  /* Warm background */
  --color-cream-50: #fffdf7;
  --color-cream-100: #fff8e8;
  --color-cream-200: #f7edcf;
  --color-cream-300: #ead9ad;

  /* Warm Accent */
  --color-coral-500: #e88972;
  --color-coral-400: #f0a28f;
  --color-coral-100: #fde8e1;

  --color-apricot-500: #e8a85f;
  --color-apricot-300: #f4c98e;
  --color-apricot-100: #fff0d8;

  --color-yellow-300: #f3d86b;
  --color-yellow-100: #fff7cf;

  /* Neutral */
  --color-gray-900: #262a24;
  --color-gray-800: #3a3f38;
  --color-gray-700: #555b52;
  --color-gray-600: #6f766b;
  --color-gray-500: #8b9287;
  --color-gray-400: #a9afa5;
  --color-gray-300: #cbd0c5;
  --color-gray-200: #e3e6de;
  --color-gray-100: #f1f3ed;
  --color-white: #ffffff;

  /* Semantic */
  --color-success: #3f7d54;
  --color-warning: #c8852f;
  --color-danger: #c75c54;
  --color-info: #527b8f;

  /* Surface */
  --color-bg-page: var(--color-cream-50);
  --color-bg-section: var(--color-cream-100);
  --color-bg-card: var(--color-white);
  --color-bg-soft: #f8f3e5;
  --color-bg-leaf-soft: var(--color-leaf-100);
  --color-bg-mint-soft: var(--color-mint-100);
  --color-border-subtle: rgba(38, 42, 36, 0.1);
  --color-border-strong: rgba(38, 42, 36, 0.18);

  /* Text */
  --color-text-primary: var(--color-gray-900);
  --color-text-secondary: var(--color-gray-700);
  --color-text-muted: var(--color-gray-600);
  --color-text-inverse: #ffffff;
}
```

### 5.2 색상 사용 비율

권장 비율:

```text
크림/아이보리 배경: 55~65%
화이트 카드: 20~30%
그린 계열: 10~15%
코랄·살구·연노랑·leaf/mint 포인트: 5% 이하
```

그린은 주요 버튼, 활성 메뉴, 핵심 배지, 포커스 링에 사용한다. 코랄·살구·연노랑·leaf/mint는 강조 카드, 안내 상태, 작은 포인트에만 사용한다.

밝은 leaf/mint는 상큼함을 주기 위한 보조색이다. 전체 브랜드가 민트 앱이나 파란 계열 대시보드처럼 보일 정도로 많이 사용하지 않는다.

파란색은 기본 브랜드 컬러로 사용하지 않는다. 지도, 외부 링크, 정보성 상태처럼 의미가 분명한 경우에만 제한적으로 사용한다.

---

## 6. Typography Tokens

### 6.1 기본 폰트

```css
:root {
  --font-family-base: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI",
    system-ui, sans-serif;
  --font-family-reading: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI",
    system-ui, sans-serif;
}
```

외부 폰트 로딩이 어렵다면 시스템 폰트만 사용해도 된다.

### 6.2 Font Size

```css
:root {
  --font-size-12: 0.75rem;
  --font-size-13: 0.8125rem;
  --font-size-14: 0.875rem;
  --font-size-15: 0.9375rem;
  --font-size-16: 1rem;
  --font-size-18: 1.125rem;
  --font-size-20: 1.25rem;
  --font-size-24: 1.5rem;
  --font-size-28: 1.75rem;
  --font-size-32: 2rem;
  --font-size-40: 2.5rem;
}
```

### 6.3 Line Height

```css
:root {
  --line-height-tight: 1.25;
  --line-height-title: 1.35;
  --line-height-body: 1.6;
  --line-height-card: 1.5;
}
```

### 6.4 Font Weight

```css
:root {
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
}
```

### 6.5 계층 기준

```css
.page-title {
  font-size: var(--font-size-32);
  line-height: var(--line-height-title);
  font-weight: var(--font-weight-bold);
}

.section-title {
  font-size: var(--font-size-24);
  line-height: var(--line-height-title);
  font-weight: var(--font-weight-bold);
}

.card-title {
  font-size: var(--font-size-18);
  line-height: var(--line-height-card);
  font-weight: var(--font-weight-semibold);
}

.body-text {
  font-size: var(--font-size-15);
  line-height: var(--line-height-body);
}

.meta-text {
  font-size: var(--font-size-13);
  line-height: var(--line-height-card);
  color: var(--color-text-muted);
}
```

---

## 7. Spacing Tokens

```css
:root {
  --space-0: 0;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-7: 2rem;
  --space-8: 2.5rem;
  --space-9: 3rem;
  --space-10: 4rem;
  --space-12: 5rem;
}
```

### 7.1 페이지 여백

```css
.page-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-10);
}
```

모바일:

```css
@media (max-width: 767px) {
  .page-shell {
    padding: var(--space-6) var(--space-4) var(--space-8);
  }
}
```

### 7.2 섹션 간격

```css
.section {
  margin-top: var(--space-9);
}

.section:first-child {
  margin-top: 0;
}
```

### 7.3 카드 내부 여백

Bootstrap 전역 `.card`에 padding을 직접 부여하지 않는다. Bootstrap 카드 구조를 사용하는 경우 `.card-body`를 사용하고, 서비스 전용 카드는 `.ui-card__body`를 사용한다.

```css
.ui-card__body {
  padding: var(--space-5);
}

.ui-card__body--dense {
  padding: var(--space-4);
}

.ui-card__body--detail {
  padding: var(--space-6);
}
```

권장 기준:

* 일반 카드: `var(--space-5)`
* 작은 카드 또는 미니 카드: `var(--space-4)`
* 정보량이 많은 상세 카드: `var(--space-6)`

---

## 8. Radius, Border, Shadow Tokens

### 8.1 Radius

```css
:root {
  --radius-xs: 0.25rem;
  --radius-sm: 0.5rem;
  --radius-md: 0.75rem;
  --radius-lg: 1rem;
  --radius-xl: 1.25rem;
  --radius-2xl: 1.5rem;
  --radius-pill: 999px;
}
```

권장 사용:

* 버튼: `--radius-pill` 또는 `--radius-md`
* 카드: `--radius-xl`
* 이미지: `--radius-lg`
* 필터 칩: `--radius-pill`
* 입력 요소: `--radius-md`

카드 모서리는 둥글게 하되, `2rem` 이상으로 과하게 키우지 않는다.

### 8.2 Shadow

```css
:root {
  --shadow-xs: 0 1px 2px rgba(31, 61, 43, 0.06);
  --shadow-sm: 0 4px 12px rgba(31, 61, 43, 0.08);
  --shadow-md: 0 8px 24px rgba(31, 61, 43, 0.1);
  --shadow-lg: 0 16px 40px rgba(31, 61, 43, 0.12);
}
```

기본 카드는 `--shadow-xs` 또는 `--shadow-sm`를 사용한다. Hover 시 `--shadow-md`까지만 사용한다. 강한 그림자를 남용하지 않는다.

### 8.3 Border

```css
:root {
  --border-subtle: 1px solid var(--color-border-subtle);
  --border-strong: 1px solid var(--color-border-strong);
}
```

---

## 9. 공통 컴포넌트 스타일

## 9.1 Card

### 기본 카드

```css
.ui-card {
  background: var(--color-bg-card);
  border: var(--border-subtle);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xs);
  overflow: hidden;
}

.ui-card__body {
  padding: var(--space-5);
}

.ui-card--interactive {
  transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
}

.ui-card--interactive:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: rgba(71, 125, 88, 0.22);
}
```

카드는 부드럽지만 절제되어야 한다. Hover 이동은 `-2px` 정도로 제한한다.

Bootstrap `.card`를 사용하는 경우에도 내부 padding은 `.card-body` 또는 별도 body class에서 관리한다.

### 도서관 카드

도서관 카드는 다음 정보를 우선 표시한다.

1. 이미지 또는 fallback 이미지
2. 도서관명
3. 구/군, 도서관 유형
4. 도로명주소
5. 장서 수, 열람좌석 수
6. 저장 버튼

도서관 카드에서 정밀 운영 상태, 실시간 좌석, 거리 정보는 현재 API 응답에 없으면 표시하지 않는다.

### 책 카드

책 카드는 표지를 중심으로 하되, 표지가 없을 경우 기본 책 fallback을 사용한다.

표시 정보:

1. 책 표지
2. 도서명
3. 저자
4. 출판사 / 출판연도
5. KDC 분류가 있으면 작은 메타 정보로 표시
6. 저장 버튼

### 프로그램 카드

프로그램 카드는 일정과 도서관 연결이 명확해야 한다.

표시 정보:

1. 프로그램명
2. 운영 도서관
3. 프로그램 유형
4. 대상
5. 신청 상태 / 운영 상태
6. 운영 기간
7. 원문 링크
8. 저장 버튼

서비스 내부 신청 버튼은 만들지 않는다.

### 후기 카드

후기 카드는 짧은 본문 중심으로 구성한다.

표시 정보:

1. 도서관명
2. 작성자 닉네임
3. 후기 본문
4. 후기 태그
5. 작성일
6. 조회수
7. 좋아요 수
8. 좋아요 버튼

별점, 이미지 업로드 상태, 방문 목적은 현재 활성 정보로 가정하지 않는다.

---

## 9.2 Button

### 기본 버튼 토큰

```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: 0 var(--space-5);
  border-radius: var(--radius-pill);
  font-size: var(--font-size-14);
  font-weight: var(--font-weight-semibold);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background-color 160ms ease, border-color 160ms ease,
    color 160ms ease, box-shadow 160ms ease;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
```

### Primary Button

```css
.btn-primary {
  color: var(--color-text-inverse);
  background: var(--color-primary-700);
  border-color: var(--color-primary-700);
}

.btn-primary:hover {
  background: var(--color-primary-800);
  border-color: var(--color-primary-800);
}
```

주요 CTA에만 사용한다.

예시:

* 로그인
* 회원가입
* 후기 작성 완료
* 선호 설정 저장
* 검색 실행

### Secondary Button

```css
.btn-secondary {
  color: var(--color-primary-800);
  background: var(--color-primary-100);
  border-color: var(--color-primary-200);
}

.btn-secondary:hover {
  background: var(--color-primary-200);
}
```

예시:

* 상세 보기
* 목록으로 돌아가기
* 선호 설정으로 이동

### Ghost Button

```css
.btn-ghost {
  color: var(--color-gray-800);
  background: transparent;
  border-color: var(--color-border-subtle);
}

.btn-ghost:hover {
  background: var(--color-cream-100);
}
```

### Icon Button

```css
.icon-button {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-pill);
  border: var(--border-subtle);
  background: var(--color-white);
}
```

저장, 좋아요, 출처 표시 등에 사용한다.

---

## 9.3 Chip / Tag / Badge

### 필터 칩

```css
.filter-chip {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-pill);
  border: var(--border-subtle);
  background: var(--color-white);
  color: var(--color-text-secondary);
  font-size: var(--font-size-14);
}

.filter-chip[aria-pressed="true"] {
  background: var(--color-primary-100);
  color: var(--color-primary-800);
  border-color: var(--color-primary-300);
}
```

### 시설 칩

확인된 시설만 표시한다.

```css
.facility-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  background: var(--color-primary-100);
  color: var(--color-primary-800);
  font-size: var(--font-size-13);
  font-weight: var(--font-weight-medium);
}
```

`null`, 데이터 부재, 미수집 상태는 시설 칩으로 표시하지 않는다.

### 상태 Badge

프로그램 상태에 사용한다.

```css
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  font-size: var(--font-size-12);
  font-weight: var(--font-weight-semibold);
}
```

권장 매핑:

```text
신청가능 / 진행중: green
신청마감 / 종료: gray
예정: apricot
신청없음: neutral
unknown/null: 표시하지 않거나 “상태 미확인”으로 약하게 표시
```

---

## 9.4 Form

### 입력 요소

```css
.form-control {
  min-height: 44px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-md);
  border: var(--border-subtle);
  background: var(--color-white);
  color: var(--color-text-primary);
  font-size: var(--font-size-15);
}

.form-control:focus {
  outline: 3px solid rgba(95, 147, 108, 0.24);
  border-color: var(--color-primary-500);
}
```

### Textarea

후기 본문은 최대 200자다.

```css
.review-textarea {
  min-height: 140px;
  padding: var(--space-4);
  resize: vertical;
}
```

하단에 글자 수를 표시한다.

```text
0 / 200
```

태그는 1~5개 선택 가능 상태를 명확히 표시한다.

---

## 10. 이미지 규칙

### 10.1 공통 이미지 비율

```css
:root {
  --ratio-library-card: 16 / 9;
  --ratio-library-hero: 21 / 9;
  --ratio-book-cover: 2 / 3;
  --ratio-program-card: 16 / 9;
  --ratio-review-thumb: 4 / 3;
}
```

### 10.2 도서관 이미지

도서관 카드는 `16:9` 비율을 사용한다. 상세 상단 이미지는 `21:9` 또는 `16:9`를 사용할 수 있다.

이미지가 fallback인 경우 실제 도서관 사진처럼 설명하지 않는다.

잘못된 문구:

```text
부산광역시립시민도서관 전경
```

권장 문구:

```text
기본 도서관 이미지
```

### 10.3 책 표지

책 표지는 `2:3` 비율을 유지한다. 표지 이미지가 없으면 기본 책 이미지를 사용한다.

책 표지는 카드 전체를 지나치게 지배하지 않도록 데스크톱 카드에서는 최대 폭을 제한한다.

### 10.4 프로그램 이미지

현재 프로그램 API는 이미지 필드를 핵심으로 요구하지 않는다. 프로그램 카드는 이미지 없이도 성립해야 한다.

프로그램 fallback 이미지를 사용할 경우 유형별 기본 이미지를 사용하되, 카드가 과하게 일러스트 중심이 되지 않도록 정보 영역을 우선한다.

### 10.5 프로필 이미지

프로필 이미지·자기소개는 현재 보류 기능이다. 현재는 email·nickname 중심 화면으로 구성하고, 기본 아바타 이미지를 핵심 기능처럼 강조하지 않는다.

---

## 11. 출처 표시 규칙

이미지 응답에 `attribution_text`가 있으면 출처 표시를 제공한다.

### 11.1 기본 표시

이미지 우하단 또는 좌하단에 작은 `ⓘ 출처` 버튼을 둔다.

```text
ⓘ 출처
```

### 11.2 상호작용

* hover
* focus
* tap

위 상호작용 시 이미지 위에 출처 문구를 오버레이로 표시한다.

### 11.3 출처 오버레이 스타일

```css
.image-attribution {
  position: absolute;
  left: var(--space-3);
  right: var(--space-3);
  bottom: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: rgba(31, 61, 43, 0.86);
  color: var(--color-white);
  font-size: var(--font-size-12);
  line-height: 1.5;
}
```

### 11.4 fallback 이미지

`is_fallback=true`이면 출처가 없을 수 있다. 이 경우 출처 버튼을 표시하지 않아도 된다.

fallback 이미지는 실제 도서관 사진이 아니므로, 카드 설명이나 alt에서 실제 장소 사진으로 표현하지 않는다.

---

## 12. 상태 UX

## 12.1 Loading

로딩은 Skeleton을 우선 사용한다.

```css
.skeleton {
  border-radius: var(--radius-md);
  background: linear-gradient(
    90deg,
    var(--color-gray-100),
    var(--color-cream-100),
    var(--color-gray-100)
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.2s ease-in-out infinite;
}
```

목록 페이지는 카드 Skeleton 6개를 기본으로 표시한다.

### 12.2 Empty State

빈 상태는 오류가 아니다. 특히 프로그램, 후기, 저장 목록은 초기 데이터가 없을 수 있다.

빈 상태 구성:

```text
아이콘 또는 작은 일러스트
제목
설명
가능한 경우 다음 행동 버튼
```

예시:

```text
아직 저장한 도서관이 없어요.
마음에 드는 도서관을 저장하면 이곳에서 다시 볼 수 있어요.
[도서관 찾기]
```

### 12.3 Error State

오류 상태는 원인을 구분한다.

* 네트워크 오류
* 인증 만료
* 권한 없음
* 찾을 수 없음
* 외부 API 설정 누락
* 서버 오류

### 12.4 503 외부 API 오류

정보나루 API Key가 없거나 외부 API 호출이 실패할 수 있다.

이 경우 책 검색 영역에 다음처럼 표시한다.

```text
책 검색 서비스를 잠시 사용할 수 없어요.
도서관 정보는 계속 둘러볼 수 있습니다.
```

전체 서비스를 오류 화면으로 막지 않는다.

### 12.5 저장·좋아요 처리 중

저장·좋아요는 처리 중 상태를 명확히 표시한다.

* 중복 클릭 방지
* 버튼 내부 spinner 또는 텍스트 변경
* 실패 시 rollback
* 실패 Toast 표시

---

## 13. 페이지별 디자인 방향

## 13.1 홈

### 목적

첫 진입에서 서비스의 성격을 이해하고, 추천 도서관과 테마별 탐색으로 자연스럽게 이동하게 한다.

### 기본 구성

```text
Hero
→ 오늘의 추천 도서관
→ 테마별 추천
→ 여기는 어때요?
```

개인 추천인 “여기는 어때요?”는 `personal_recommendations.available=true`일 때만 표시한다. 개인 추천 데이터가 충분히 안정화되고 사용자 경험상 더 중요한 섹션으로 검증된 경우에만 오늘의 추천 바로 아래 등 더 높은 위치로 조정할 수 있다.

### Hero

Hero는 SaaS 랜딩페이지처럼 과장하지 않는다.

권장 방향:

* 크림 배경
* 짧은 서비스 문장
* 도서관·책·나들이 감성의 작은 시각 요소
* 검색창 없음
* 기능에 없는 CTA 없음

권장 문구 예시:

```text
오늘, 어떤 도서관을 둘러볼까요?
우리 지역의 도서관, 책, 문화 프로그램과 후기를 한곳에서 찾아보세요.
```

또는 더 지역명을 덜 드러내는 문구를 사용할 수 있다.

```text
도서관, 책, 문화 프로그램과 후기를 한곳에서 둘러보세요.
```

CTA는 실제 기능과 연결되는 것만 사용한다.

가능한 CTA:

* 도서관 찾기
* 책 둘러보기
* 문화 프로그램 보기

홈에 검색창을 넣지 않는다.

### 오늘의 추천 도서관

카드 3개 이하를 보여준다.

* 추천 기준 제목
* 추천 기준 설명
* 도서관 카드
* 추천 사유

정밀 운영 상태, 실시간 좌석, 개인화 분석 문장은 표시하지 않는다.

### 테마별 추천

5개 테마만 표시한다.

* 공부하기 좋은 곳
* 책을 빌리러 가요
* 아이와 함께 가요
* 분위기 좋은 곳에 머물고 싶어요
* 가까운 곳이 좋아요

`program` 목적은 홈 테마로 표시하지 않는다.

### 여기는 어때요?

`personal_recommendations.available=true`일 때만 표시한다.

`available=false`이면 섹션을 숨기거나, 작은 안내 카드로 처리한다.

추천 데이터가 없는데 임의로 개인화 추천처럼 보이게 만들지 않는다.

---

## 13.2 도서관 찾기

### 목적

지역 도서관을 검색하고, 구/군과 도서관 유형 기준으로 탐색하게 한다.

### 활성 필터

현재 활성 필터는 다음만 사용한다.

* 검색어 `q`
* 구/군 `sigungu`
* 도서관 유형 `library_type`

보류 필터는 활성 UI로 배치하지 않는다.

보류 필터 예시:

* 오늘 운영
* 현재 운영
* 시설 필터
* 좌석 수 필터
* 장서 수 필터
* 거리순
* 목적 기반 고급 필터
* 공휴일 운영

### 레이아웃

데스크톱:

```text
PageHeader
→ 검색·필터 Bar
→ 결과 수 / 정렬 안내
→ 3열 카드 그리드
→ Pagination
```

모바일:

```text
PageHeader
→ 검색
→ 필터 Drawer 버튼
→ 1열 카드 리스트
```

### 카드 표시 정보

* 이미지
* 도서관명
* 구/군
* 유형
* 주소
* 장서 수
* 열람좌석 수
* 저장 버튼

시설 정보는 상세 페이지에서 더 강조한다. 목록 카드에는 확인된 핵심 정보만 작게 표시한다.

---

## 13.3 도서관 상세

### 목적

도서관 방문 전 확인해야 할 기본 정보, 시설, 위치, 관련 후기·프로그램을 제공한다.

### 구성

```text
상단 요약
→ 기본 정보
→ 통계 정보
→ 확인된 시설
→ 위치 지도
→ 관련 프로그램
→ 관련 후기
```

### 상단 요약

* 대표 이미지 또는 fallback
* 도서관명
* 구/군
* 유형
* 주소
* 저장 버튼
* 출처 표시

정밀 운영 여부를 큰 Badge로 표시하지 않는다. 운영 시간 데이터가 있더라도 현재 계약에서 구조가 확정되지 않은 raw object는 그대로 노출하지 않는다.

### 통계 정보

가능한 정보:

* 도서 자료 수
* 비도서 수
* 연속간행물 수
* 열람좌석 수
* 건물면적
* 부지면적

`null`이면 `정보 없음` 또는 항목 미표시로 처리한다. `0`과 `null`을 같은 의미로 합치지 않는다.

### 확인된 시설

`facility_profile`에서 `true`인 시설만 칩으로 표시한다.

`false`, `null`, profile 부재는 “없음”으로 단정하지 않는다.

권장 안내:

```text
확인된 시설만 표시하고 있어요.
```

### 지도

Kakao 지도는 좌표가 있을 때만 표시한다.

좌표나 SDK Key가 없으면 지도 영역에 fallback을 표시한다.

```text
지도를 불러올 수 없어요.
주소를 확인한 뒤 지도 앱에서 검색해 주세요.
```

### 비슷한 도서관

현재 활성 기능으로 표시하지 않는다.

---

## 13.4 책 둘러보기

### 목적

정보나루 책 검색과 책 상세, 소장 도서관 조회를 제공한다.

### 구성

```text
PageHeader
→ 책 검색 Form
→ 검색 결과
→ 책 상세
→ 이 책을 보유한 도서관
```

### 검색

검색 유형:

* 도서명
* 저자
* ISBN
* 키워드
* 출판사

검색 전에는 과도한 추천 영역을 만들지 않는다.

주간 인기 도서는 현재 활성 기능으로 표시하지 않는다.

### 책 카드

* 표지
* 제목
* 저자
* 출판사
* 출판연도
* 저장 버튼

### 소장 도서관

`matched=true`이면 내부 도서관 상세로 연결한다.

`matched=false`이면 외부 도서관 정보 카드로 표시하되 내부 상세 링크를 만들지 않는다.

---

## 13.5 문화 프로그램

### 목적

도서관 문화 프로그램을 검색하고, 원문 게시글과 도서관 상세로 연결한다.

### 구성

```text
PageHeader
→ 검색·필터
→ 프로그램 카드 목록
→ Pagination
```

### 필터

활성 필터:

* 검색어 `q`
* 도서관 ID `library_id`
* 구/군 `sigungu`
* 프로그램 유형 `category`
* 대상 `target`
* 신청 상태 `application_status`
* 운영 상태 `operation_status`

### 카드

* 프로그램명
* 도서관명
* 유형
* 대상
* 신청 상태
* 운영 상태
* 운영 기간
* 원문 링크
* 저장 버튼

서비스 내부 신청·예약 버튼은 만들지 않는다.

---

## 13.6 커뮤니티

### 목적

도서관 후기를 읽고 작성하며, 좋아요로 반응할 수 있게 한다.

### 구성

```text
PageHeader
→ 후기 검색·정렬
→ 후기 카드 목록
→ 후기 작성 CTA
```

### 정렬

활성 정렬:

* 최신순
* 조회수순
* 좋아요순

### 후기 작성

작성 Form:

* 도서관 선택
* 본문
* 후기 태그 1~5개
* 관련 책 선택
* 관련 프로그램 선택

이미지 업로드 UI는 현재 제공하지 않는다.

본문은 1~200자다.

### 후기 카드

* 도서관명
* 작성자
* 본문
* 태그
* 작성일
* 조회수
* 좋아요 수
* 좋아요 버튼

작성자 본인에게만 수정·삭제 메뉴를 표시한다.

---

## 13.7 나의 나들이

### 목적

사용자가 저장하거나 작성·좋아요한 항목을 다시 확인하는 회원 전용 영역이다.

현재 API v1.1 구현에서는 목록 중심으로 구성한다. 다만 최종 기획상 나의 나들이는 성향 요약, 태그 요약, 관심 분야 섹션으로 확장될 수 있으므로 레이아웃은 확장 가능하게 설계한다.

### 현재 활성 탭

* 저장한 도서관
* 저장한 책
* 저장한 문화 프로그램
* 좋아요한 후기
* 내가 쓴 후기

### 현재 구현 기준

현재 응답에 없는 분석 수치나 요약 문장을 임의로 만들지 않는다.

예를 들어 다음 항목은 현재 응답이 없으면 표시하지 않는다.

* 공부형 42%
* 책 탐색형 28%
* 자주 찾는 지역 1위
* 내 취향 요약 문장
* 태그 기반 관심 분야 자동 분석

### 향후 확장 가능한 레이아웃

나의 나들이 페이지는 다음 구조로 확장 가능하게 설계한다.

```text
프로필 요약 영역
→ 성향 요약 영역
→ 태그 요약 영역
→ 관심 분야 영역
→ 저장·작성·좋아요 목록 탭
```

단, 현재 API에서 제공되지 않는 영역은 placeholder로 고정 배치하지 않는다. 후속 API가 확정되기 전까지는 목록 탭 중심으로 구현한다.

### 레이아웃

데스크톱:

```text
MemberLayout
→ 요약 영역이 있을 경우 상단 Section
→ 목록 Tab
→ 목록 카드
```

모바일:

```text
상단 요약 영역
→ Tab scroll
→ 1열 목록
```

---

## 13.8 로그인·회원가입·프로필·선호 설정

### 로그인·회원가입

인증 식별자는 email이다.

입력 필드:

회원가입:

* email
* password
* nickname

로그인:

* email
* password

`username` 입력은 만들지 않는다.

### 프로필

현재 프로필은 email·nickname 중심으로 구성한다.

* email 조회
* nickname 조회
* nickname 수정

프로필 이미지·자기소개는 현재 보류 기능처럼 다룬다. 단, 후속 확장을 고려해 프로필 영역의 레이아웃은 이미지가 추가되어도 무너지지 않도록 구성할 수 있다.

### 선호 설정

선호 설정은 다음을 다룬다.

* 선호 목적
* 선호 지역
* 선호 시설 태그

저장 방식은 전체 교체 저장 UI로 이해한다. 사용자가 저장 버튼을 누르기 전에는 실제 선호가 반영된 것처럼 표현하지 않는다.

---

## 14. 접근성 기준

### 14.1 색 대비

* 본문 텍스트는 배경 대비 4.5:1 이상을 목표로 한다.
* 큰 제목은 최소 3:1 이상을 유지한다.
* 코랄·살구·연노랑·밝은 mint는 텍스트 색으로 단독 사용하지 않는다.

### 14.2 Focus Style

```css
:focus-visible {
  outline: 3px solid rgba(95, 147, 108, 0.35);
  outline-offset: 3px;
}
```

포커스 표시를 제거하지 않는다.

Bootstrap 기본 파란 focus ring이 보이는 경우 `bootstrap-overrides.css`에서 green 계열 focus ring으로 교체한다.

### 14.3 버튼과 링크 구분

* 상세 이동은 `<a>` 또는 RouterLink
* 저장·좋아요·삭제는 `<button>`
* 카드 전체를 클릭 가능한 `div`로 만들지 않는다.

### 14.4 현재 위치 표시

상단 내비게이션의 현재 메뉴에는 `aria-current="page"`를 사용한다.

### 14.5 이미지 대체 텍스트

실제 이미지:

```text
{도서관명} 이미지
```

fallback 이미지:

```text
기본 도서관 이미지
```

책 표지:

```text
{책 제목} 표지
```

출처 버튼:

```text
이미지 출처 보기
```

### 14.6 지도 접근성

지도 영역 아래에 주소 텍스트와 외부 지도 링크를 제공한다. 지도만으로 위치 정보를 전달하지 않는다.

---

## 15. 반응형 기준

### 15.1 Breakpoints

아래 breakpoint token은 문서 기준값이다.

```css
:root {
  --breakpoint-sm: 576px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 992px;
  --breakpoint-xl: 1200px;
}
```

다만 실제 CSS media query에서는 CSS custom property를 직접 사용하지 않고 px 값을 직접 사용한다. CSS custom property는 일반적인 media query 조건에서 안정적으로 사용할 수 없으므로 다음처럼 작성한다.

```css
@media (max-width: 767px) {
  /* mobile styles */
}

@media (min-width: 768px) and (max-width: 1199px) {
  /* tablet styles */
}

@media (min-width: 1200px) {
  /* desktop styles */
}
```

### 15.2 Desktop

* 상단 내비게이션 고정
* 최대 폭 `1200px`
* 카드 3열
* 필터 Bar 가로 배치
* 상세 페이지는 2열 정보 배치 가능
* 하단 탭을 사용하지 않음

### 15.3 Tablet

* 카드 2열
* 필터 일부 줄바꿈
* 상세 페이지는 이미지와 정보 영역을 세로 배치할 수 있음

### 15.4 Mobile

* 카드 1열
* 필터 Drawer 또는 접힘 패널
* 상단 내비게이션은 메뉴 버튼으로 전환 가능
* 주요 공개 탭 접근성을 위해 하단 탭 사용 가능
* 하단 탭은 모바일 전용 보조 내비게이션으로만 사용
* 버튼 터치 영역 최소 `40px`

---

## 16. 금지 디자인 패턴

### 16.1 일반 SaaS 랜딩페이지 금지

금지 요소:

* 과장된 Hero 문구
* “지금 시작하기”만 반복되는 CTA
* 기능보다 마케팅 카피 중심 구성
* 추상 3D 일러스트
* 실제 기능과 무관한 성장 그래프

### 16.2 과한 파란색 대시보드 금지

도서관 나들이의 기본 색은 크림·그린이다. 파란색 중심의 Admin Dashboard, 데이터 시각화 SaaS처럼 만들지 않는다.

Bootstrap의 기본 primary blue도 그대로 사용하지 않는다.

### 16.3 회색 관리자 페이지 금지

테이블과 회색 박스만 반복하는 화면을 피한다. 공공서비스의 단정함은 유지하되, 카드와 여백, 따뜻한 배경으로 생활 서비스 느낌을 준다.

### 16.4 데스크톱에서 모바일 앱 홈처럼 보이는 구조 금지

데스크톱에서 모바일 앱처럼 보이는 구조를 피한다.

금지:

* 데스크톱 하단 탭
* 모바일 카드만 크게 늘린 홈
* 화면 대부분을 아이콘 버튼으로 구성
* 앱 런처 같은 홈 메뉴

모바일에서는 하단 탭을 사용할 수 있지만, 그것이 전체 정보 구조의 기준이 되어서는 안 된다.

### 16.5 기능에 없는 CTA 금지

금지 CTA 예시:

* 프로그램 신청하기
* 예약하기
* 결제하기
* 실시간 좌석 보기
* AI 추천받기
* 내 취향 분석 새로고침
* 지도에서 도서관 찾기
* 비슷한 도서관 더보기

현재 API와 기능에 없는 행동은 버튼으로 만들지 않는다.

### 16.6 API에 없는 데이터 연출 금지

금지 표시 예시:

* 현재 운영 중
* 지금 좌석 여유
* 내 취향 87% 일치
* 이번 주 인기 도서
* 비슷한 도서관
* 방문자 수
* 혼잡도
* AI 추천 사유

응답에 없는 필드는 화면에서 추론하지 않는다.

나의 나들이의 성향 요약·태그 요약·관심 분야는 후속 확장 가능 영역이지만, 현재 API 응답에 없는 수치나 문장을 임의 생성하지 않는다.

---

## 17. 후속 확장 시 디자인 메모

다음 기능은 현재 활성 UI가 아니라 후속 확장 영역이다.

* 도서관 open_today / open_now 정밀 판정
* 목적·시설·좌석·장서·공휴일·거리 기반 고급 필터
* 주간 인기 도서
* 비슷한 도서관
* 행동 기반 개인화 추천 계산
* 사용자 취향 요약 문장
* 나의 나들이 통합 분석 Dashboard
* 후기 이미지 업로드
* 프로필 이미지·자기소개
* 서비스 내부 프로그램 신청·예약·결제
* 실시간 열람실 좌석
* GMS/AI 문구 생성
* 도서관 찾기 지도 중심 모드
* 무한 스크롤

후속 확장 시에도 기존 디자인 정체성은 유지한다.

* 크림·그린 기반
* 단정한 공공서비스 인상
* 부드럽지만 절제된 카드
* 기능이 먼저, 감성은 보조
* API와 데이터 계약 우선

---

## 18. 구현 체크리스트

### 18.1 공통

* [ ] CSS token을 `tokens.css`로 분리한다.
* [ ] Bootstrap override를 `bootstrap-overrides.css`로 분리한다.
* [ ] Bootstrap 기본 primary blue를 그대로 사용하지 않는다.
* [ ] Bootstrap `.card`에 전역 padding을 부여하지 않는다.
* [ ] 카드 내부 여백은 `.card-body` 또는 `.ui-card__body`에서 관리한다.
* [ ] media query에는 breakpoint custom property 대신 px 값을 직접 사용한다.
* [ ] 페이지 최대 폭을 통일한다.
* [ ] 카드 radius와 shadow를 통일한다.
* [ ] Primary color를 그린으로 통일한다.
* [ ] fallback 이미지를 실제 이미지처럼 설명하지 않는다.
* [ ] 출처 오버레이를 구현한다.
* [ ] focus-visible 스타일을 제거하지 않는다.

### 18.2 홈

* [ ] 홈에 검색창을 넣지 않는다.
* [ ] 기본 섹션 순서를 Hero → 오늘의 추천 도서관 → 테마별 추천 → 여기는 어때요?로 구성한다.
* [ ] Hero 문구는 전국 확장 가능성을 고려해 “우리 지역” 또는 지역명을 생략한 표현을 우선한다.
* [ ] 오늘의 추천 도서관을 최대 3개로 표시한다.
* [ ] 개인 추천은 available일 때만 표시한다.
* [ ] 테마는 5개만 표시한다.
* [ ] program 목적을 홈 테마로 표시하지 않는다.

### 18.3 도서관

* [ ] 활성 필터는 q, sigungu, library_type만 사용한다.
* [ ] 고급 필터를 활성 UI로 만들지 않는다.
* [ ] 상세에서 true 시설만 칩으로 표시한다.
* [ ] null 시설을 “없음”으로 단정하지 않는다.
* [ ] 지도 fallback을 제공한다.

### 18.4 책

* [ ] 주간 인기 도서 섹션을 활성 UI로 만들지 않는다.
* [ ] 정보나루 검색 오류를 전체 서비스 오류로 처리하지 않는다.
* [ ] matched=false 소장 도서관은 내부 상세 링크를 만들지 않는다.

### 18.5 프로그램

* [ ] 내부 신청 버튼을 만들지 않는다.
* [ ] 원문 링크는 외부 새 탭으로 처리한다.
* [ ] 프로그램 데이터 0건을 오류로 표현하지 않는다.

### 18.6 커뮤니티

* [ ] 후기 본문은 1~200자로 제한한다.
* [ ] 태그는 1~5개 선택으로 안내한다.
* [ ] 이미지 업로드 UI를 만들지 않는다.
* [ ] 작성자 본인에게만 수정·삭제 메뉴를 노출한다.

### 18.7 나의 나들이

* [ ] 현재 구현은 저장 도서관·책·프로그램·내 후기·좋아요 후기 목록 중심으로 구성한다.
* [ ] 향후 성향 요약·태그 요약·관심 분야 섹션이 추가될 수 있도록 상단 요약 영역 확장을 고려한다.
* [ ] 현재 API 응답에 없는 분석 수치나 취향 요약 문장을 임의로 만들지 않는다.
