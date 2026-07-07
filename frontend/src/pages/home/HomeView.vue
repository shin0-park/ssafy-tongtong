<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import LibraryCard from '@/components/cards/LibraryCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import LocationPermissionPanel from '@/components/location/LocationPermissionPanel.vue'
import { fetchHome, fetchPersonalHomeRecommendations } from '@/services/homeService'
import { fetchMyOutingsDashboard } from '@/services/myOutingsService'
import { useAuthStore } from '@/stores/auth'
import { PURPOSE_LABELS, isBrokenText } from '@/utils/display'
import { readStoredLocation, storeLocation } from '@/utils/locationPreference'

const router = useRouter()
const authStore = useAuthStore()
const homeData = ref(null)
const personalRecommendationData = ref(null)
const dashboardData = ref(null)
const isHomeLoading = ref(false)
const isPersonalLoading = ref(false)
const homeError = ref(null)
const personalError = ref(null)
const locationMessage = ref('')
const currentLocation = ref(readStoredLocation())
const showLocationPanel = ref(false)
const isLocationLoading = ref(false)

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
const selectedThemeCode = ref('study')
const selectedThemeGroup = computed(() =>
  themeGroups.value.find((group) => group.code === selectedThemeCode.value) ?? themeGroups.value[0],
)
const personalRecommendations = computed(() => personalRecommendationData.value ?? {})
const personalItems = computed(() => personalRecommendations.value.items ?? [])
const personalPriorityTags = computed(() =>
  Array.isArray(personalRecommendations.value.priority_tags)
    ? personalRecommendations.value.priority_tags.filter((tag) => tag?.label || tag?.code).slice(0, 5)
    : [],
)
const dashboardSummarySentence = computed(() => {
  const sentence = dashboardData.value?.summary_sentence
  return sentence && !isBrokenText(sentence) ? sentence : ''
})
const personalReasonKeywords = computed(() => {
  if (personalPriorityTags.value.length) {
    return personalPriorityTags.value.map((tag) => tag.label || tag.code).slice(0, 4)
  }

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
  () =>
    todayItems.value.length > 0 ||
    showPersonalRecommendations.value ||
    (authStore.isAuthenticated && (isPersonalLoading.value || personalError.value)) ||
    themeGroups.value.some((group) => group.items.length),
)

async function loadHome() {
  isHomeLoading.value = true
  homeError.value = null
  personalError.value = null
  homeData.value = null
  personalRecommendationData.value = null
  dashboardData.value = null

  try {
    homeData.value = await fetchHome(currentLocation.value ?? {})
  } catch (requestError) {
    homeError.value = requestError
  } finally {
    isHomeLoading.value = false
  }

  if (authStore.isAuthenticated && homeData.value) {
    loadPersonalRecommendations()
  }
}

async function loadPersonalRecommendations() {
  isPersonalLoading.value = true
  personalError.value = null
  personalRecommendationData.value = null
  dashboardData.value = null

  try {
    const [personalResult, dashboardResult] = await Promise.allSettled([
      fetchPersonalHomeRecommendations(),
      fetchMyOutingsDashboard(),
    ])

    if (personalResult.status === 'rejected') throw personalResult.reason
    personalRecommendationData.value = personalResult.value
    dashboardData.value = dashboardResult.status === 'fulfilled' ? dashboardResult.value : null
  } catch (requestError) {
    personalError.value = requestError
  } finally {
    isPersonalLoading.value = false
  }
}

function selectTheme(code) {
  locationMessage.value = ''
  selectedThemeCode.value = code
  showLocationPanel.value = code === 'nearby' && !currentLocation.value
}

function goToTheme(code) {
  locationMessage.value = ''

  if (code !== 'nearby') {
    router.push({ path: '/libraries', query: { purpose: code } })
    return
  }

  if (currentLocation.value) {
    router.push({
      path: '/libraries',
      query: {
        purpose: 'nearby',
        lat: currentLocation.value.lat,
        lng: currentLocation.value.lng,
      },
    })
    return
  }

  showLocationPanel.value = true
}

async function applyCurrentLocation({ navigateAfterApply = false } = {}) {
  locationMessage.value = ''

  if (!navigator.geolocation) {
    locationMessage.value = '현재 브라우저에서 위치 정보를 사용할 수 없습니다.'
    return
  }

  isLocationLoading.value = true
  navigator.geolocation.getCurrentPosition(
    (position) => {
      currentLocation.value = storeLocation(position)
      if (!currentLocation.value) {
        locationMessage.value = '현재 위치를 확인하지 못했습니다.'
        isLocationLoading.value = false
        return
      }
      showLocationPanel.value = false
      isLocationLoading.value = false
      loadHome()
      if (navigateAfterApply) goToTheme('nearby')
    },
    () => {
      locationMessage.value = '위치 권한을 사용할 수 없어 가까운 곳 추천을 적용하지 않았습니다.'
      isLocationLoading.value = false
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

    <LoadingState v-if="isHomeLoading" title="추천 도서관을 불러오는 중입니다." />
    <ErrorState
      v-else-if="homeError"
      title="홈 정보를 불러오지 못했습니다."
      :message="homeError.message"
      @retry="loadHome"
    />
    <EmptyState
      v-else-if="!hasContent"
      title="아직 표시할 추천 도서관이 없습니다."
      description="추천 데이터가 준비되면 이곳에 표시됩니다."
    />

    <div v-else class="home-section-stack">
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
        <div class="home-feature-grid">
          <LibraryCard
            v-for="library in todayItems"
            :key="library.id"
            :library="library"
            :show-recommendation-reason="false"
          />
        </div>
      </section>

      <section v-if="authStore.isAuthenticated && (isPersonalLoading || personalError || showPersonalRecommendations)">
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
        <LoadingState
          v-if="isPersonalLoading"
          title="추천 도서관을 불러오는 중입니다."
          message="잠시만 기다려주세요."
        />
        <EmptyState
          v-else-if="personalError"
          title="맞춤 추천을 불러오지 못했습니다."
          description="오늘의 추천과 테마별 추천은 계속 이용할 수 있어요."
        />
        <div v-else class="home-feature-grid home-feature-grid-secondary">
          <LibraryCard
            v-for="library in personalItems.slice(0, 3)"
            :key="library.id"
            :library="library"
            :show-recommendation-reason="true"
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
            class="theme-tab-button"
            :class="{ 'is-active': selectedThemeCode === group.code }"
            type="button"
            @click="selectTheme(group.code)"
          >
            <strong>{{ group.label }}</strong>
          </button>
        </div>

        <LocationPermissionPanel
          v-if="showLocationPanel"
          class="mb-4"
          :is-loading="isLocationLoading"
          :error-message="locationMessage"
          @confirm="applyCurrentLocation()"
          @dismiss="showLocationPanel = false"
        />

        <section v-if="selectedThemeGroup">
          <div class="section-header-row">
            <div>
              <h3 class="section-title mb-1">{{ selectedThemeGroup.label }}</h3>
              <p class="meta-text mb-0">{{ selectedThemeGroup.description }}</p>
            </div>
            <button class="btn btn-outline-primary btn-sm" type="button" @click="goToTheme(selectedThemeGroup.code)">
              더보기
            </button>
          </div>
          <EmptyState
            v-if="!selectedThemeGroup.items.length"
            title="이 테마에 맞는 추천 도서관이 아직 없어요."
            description="추천 데이터가 준비되면 이곳에 표시됩니다."
          />
          <div v-else class="library-result-grid">
              <LibraryCard
                v-for="library in selectedThemeGroup.items.slice(0, 4)"
                :key="library.id"
                :library="library"
                :show-recommendation-reason="false"
              />
          </div>
        </section>
      </section>
    </div>
  </section>
</template>
