<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import LibraryCard from '@/components/cards/LibraryCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchHome } from '@/services/homeService'
import { fetchMyOutingsDashboard } from '@/services/myOutingsService'
import { useAuthStore } from '@/stores/auth'
import { PURPOSE_LABELS, isBrokenText } from '@/utils/display'

const router = useRouter()
const authStore = useAuthStore()
const homeData = ref(null)
const dashboardData = ref(null)
const isLoading = ref(false)
const error = ref(null)
const locationMessage = ref('')

const THEME_CODES = ['study', 'book', 'kids', 'mood', 'nearby']
const THEME_DESCRIPTIONS = {
  study: '조용한 열람실과 좌석 정보를 중심으로 골라봅니다.',
  book: '장서가 풍부하고 책 탐색에 좋은 도서관입니다.',
  kids: '어린이자료실과 가족 방문 맥락을 살펴봅니다.',
  mood: '공간과 분위기, 휴식감을 함께 봅니다.',
  nearby: '현재 위치 기준으로 가까운 도서관을 찾습니다.',
}

const todayRecommendations = computed(() => homeData.value?.today_recommendations ?? {})
const todayItems = computed(() => (todayRecommendations.value.items ?? []).slice(0, 3))
const themeGroups = computed(() => {
  const groups = homeData.value?.theme_recommendations ?? []
  return THEME_CODES.map((code) => {
    const found = groups.find((group) => group.purpose?.code === code)
    return {
      code,
      label: PURPOSE_LABELS[code],
      description: THEME_DESCRIPTIONS[code],
      items: found?.items ?? [],
    }
  })
})
const personalRecommendations = computed(() => homeData.value?.personal_recommendations ?? {})
const personalItems = computed(() => personalRecommendations.value.items ?? [])
const dashboardSummarySentence = computed(() => {
  const sentence = dashboardData.value?.summary_sentence
  return sentence && !isBrokenText(sentence) ? sentence : ''
})
const personalReasonKeywords = computed(() => {
  const sourceText = dashboardSummarySentence.value
  if (!sourceText) return []

  const keywords = []
  const addKeyword = (condition, label) => {
    if (condition && !keywords.includes(label)) keywords.push(label)
  }

  addKeyword(/공부|열람|좌석|조용|학습/.test(sourceText), '공부/열람')
  addKeyword(/책|독서|장서|도서|문학|자료/.test(sourceText), '책 탐색')
  addKeyword(/프로그램|문화|강연|체험|전시/.test(sourceText), '문화 프로그램')
  addKeyword(/휴식|분위기|공간|카페|머무/.test(sourceText), '휴식 공간')
  addKeyword(/아이|가족|어린이|유아|초등/.test(sourceText), '아이/가족')
  addKeyword(/지역|가까|동네|자주 찾/.test(sourceText), '관심 지역')
  addKeyword(/저장|후기|좋아요|활동/.test(sourceText), '활동 기반')

  return keywords.slice(0, 4)
})
const showPersonalRecommendations = computed(
  () => authStore.isAuthenticated && personalRecommendations.value.available === true && personalItems.value.length > 0,
)
const hasContent = computed(
  () => todayItems.value.length > 0 || showPersonalRecommendations.value || themeGroups.value.some((group) => group.items.length),
)

async function loadHome() {
  isLoading.value = true
  error.value = null
  dashboardData.value = null

  try {
    const [homeResult, dashboardResult] = await Promise.allSettled([
      fetchHome(),
      authStore.isAuthenticated ? fetchMyOutingsDashboard() : Promise.resolve(null),
    ])

    if (homeResult.status === 'rejected') throw homeResult.reason
    homeData.value = homeResult.value
    dashboardData.value = dashboardResult.status === 'fulfilled' ? dashboardResult.value : null
  } catch (requestError) {
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

function goToTheme(code) {
  locationMessage.value = ''

  if (code !== 'nearby') {
    router.push({ path: '/libraries', query: { purpose: code } })
    return
  }

  if (!navigator.geolocation) {
    locationMessage.value = '현재 브라우저에서 위치를 사용할 수 없어 전체 도서관 목록으로 이동합니다.'
    router.push('/libraries')
    return
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      router.push({
        path: '/libraries',
        query: {
          purpose: 'nearby',
          lat: position.coords.latitude.toFixed(7),
          lng: position.coords.longitude.toFixed(7),
        },
      })
    },
    () => {
      locationMessage.value = '위치 권한을 사용할 수 없어 전체 도서관 목록으로 이동합니다.'
      router.push('/libraries')
    },
    {
      enableHighAccuracy: false,
      timeout: 8000,
      maximumAge: 300000,
    },
  )
}

onMounted(loadHome)
</script>

<template>
  <section class="page-shell">
    <div class="page-hero page-hero-banner page-hero-home">
      <h1>오늘, 어떤 도서관으로 나들이 가볼까요?</h1>
      <p>책, 공부, 프로그램, 공간 정보를 한눈에 보고 오늘 가기 좋은 도서관을 찾아보세요.</p>
      <div class="d-flex flex-wrap gap-2 mt-4">
        <RouterLink class="btn btn-primary" to="/libraries">도서관 찾기</RouterLink>
        <RouterLink class="btn btn-outline-primary" to="/books">책 둘러보기</RouterLink>
        <RouterLink class="btn btn-outline-primary" to="/programs">문화 프로그램</RouterLink>
      </div>
    </div>

    <LoadingState v-if="isLoading" title="추천 도서관을 불러오는 중입니다." />
    <ErrorState
      v-else-if="error"
      title="홈 정보를 불러오지 못했습니다."
      :message="error.message"
      @retry="loadHome"
    />
    <EmptyState
      v-else-if="!hasContent"
      title="아직 표시할 추천 도서관이 없습니다."
      description="추천 데이터가 준비되면 이곳에 표시됩니다."
    />

    <div v-else class="d-grid gap-5">
      <section v-if="todayItems.length">
        <div class="section-header-row">
          <div>
            <h2 class="section-title mb-1">
              {{ todayRecommendations.theme?.title || '오늘의 추천 도서관' }}
            </h2>
            <p class="meta-text mb-0">
              {{ todayRecommendations.theme?.subtitle || '오늘의 기준에 맞는 도서관 3곳을 골라봤어요.' }}
            </p>
          </div>
          <RouterLink class="btn btn-outline-primary btn-sm" to="/libraries">더보기</RouterLink>
        </div>
        <div class="responsive-card-grid-three">
          <LibraryCard v-for="library in todayItems" :key="library.id" :library="library" />
        </div>
      </section>

      <section v-if="showPersonalRecommendations">
        <div class="section-header-row">
          <div>
            <h2 class="section-title mb-1">{{ personalRecommendations.title || '여기는 어때요?' }}</h2>
            <div class="section-summary-line">
              <p class="meta-text mb-0">
                {{ personalRecommendations.reason || '저장한 도서관, 책, 프로그램과 후기 활동을 바탕으로 골랐어요.' }}
              </p>
              <div v-if="personalReasonKeywords.length" class="summary-keyword-row" aria-label="추천 기준 요약">
                <span v-for="keyword in personalReasonKeywords" :key="keyword" class="summary-keyword-chip">
                  {{ keyword }}
                </span>
              </div>
            </div>
          </div>
          <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/dashboard">나의 나들이</RouterLink>
        </div>
        <div class="responsive-card-grid-three">
          <LibraryCard
            v-for="library in personalItems.slice(0, 3)"
            :key="library.id"
            :library="library"
            :show-recommendation-reason="false"
          />
        </div>
      </section>

      <section>
        <div class="section-header-row">
          <div>
            <h2 class="section-title mb-1">테마별 추천</h2>
            <p class="meta-text mb-0">목적별로 도서관을 빠르게 탐색해보세요.</p>
          </div>
        </div>
        <p v-if="locationMessage" class="alert alert-info py-2">{{ locationMessage }}</p>
        <div class="theme-card-grid mb-4">
          <button
            v-for="group in themeGroups"
            :key="group.code"
            class="theme-card-button"
            type="button"
            @click="goToTheme(group.code)"
          >
            <strong>{{ group.label }}</strong>
            <span class="meta-text">{{ group.description }}</span>
          </button>
        </div>

        <div class="d-grid gap-5">
          <section v-for="group in themeGroups.filter((item) => item.items.length)" :key="group.code">
            <div class="section-header-row">
              <h3 class="section-title mb-0">{{ group.label }}</h3>
              <button class="btn btn-outline-primary btn-sm" type="button" @click="goToTheme(group.code)">
                더보기
              </button>
            </div>
            <div class="responsive-card-grid">
              <LibraryCard
                v-for="library in group.items.slice(0, 6)"
                :key="library.id"
                compact
                :library="library"
              />
            </div>
          </section>
        </div>
      </section>
    </div>
  </section>
</template>
