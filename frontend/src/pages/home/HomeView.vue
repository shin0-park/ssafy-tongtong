<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import LibraryCard from '@/components/cards/LibraryCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchHome } from '@/services/homeService'

const router = useRouter()
const homeData = ref(null)
const isLoading = ref(false)
const error = ref(null)
const locationMessage = ref('')

const PUBLIC_THEME_CODES = new Set(['study', 'book', 'kids', 'mood', 'nearby'])

const todayItems = computed(() => (homeData.value?.today_recommendations?.items ?? []).slice(0, 3))
const themeGroups = computed(() =>
  (homeData.value?.theme_recommendations ?? []).filter((group) =>
    PUBLIC_THEME_CODES.has(group.purpose?.code),
  ),
)
const personalItems = computed(() => homeData.value?.personal_recommendations?.items ?? [])
const personalRecommendations = computed(() => homeData.value?.personal_recommendations ?? {})
const showPersonalRecommendations = computed(
  () => personalRecommendations.value.available === true && personalItems.value.length > 0,
)
const hasContent = computed(
  () =>
    todayItems.value.length > 0 ||
    showPersonalRecommendations.value ||
    themeGroups.value.some((group) => group.items?.length),
)

async function loadHome() {
  isLoading.value = true
  error.value = null

  try {
    homeData.value = await fetchHome()
  } catch (requestError) {
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

function goToTheme(code) {
  locationMessage.value = ''

  if (!code) {
    router.push('/libraries')
    return
  }

  if (code !== 'nearby') {
    router.push({
      path: '/libraries',
      query: { purpose: code },
    })
    return
  }

  if (!navigator.geolocation) {
    locationMessage.value = '현재 브라우저에서는 위치를 사용할 수 없어 일반 도서관 탐색으로 이동합니다.'
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
      locationMessage.value = '위치 권한을 사용할 수 없어 일반 도서관 탐색으로 이동합니다.'
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
    <div class="page-header">
      <h1 class="page-title">오늘의 도서관 나들이</h1>
      <p class="page-subtitle">오늘의 추천, 테마 추천, 개인 추천으로 부산 도서관을 둘러보세요.</p>
    </div>

    <LoadingState v-if="isLoading" title="추천을 불러오는 중입니다." />
    <ErrorState
      v-else-if="error"
      title="홈 정보를 불러오지 못했습니다."
      :message="error.message"
      @retry="loadHome"
    />
    <EmptyState
      v-else-if="!hasContent"
      title="아직 추천할 도서관이 없습니다."
      description="백엔드 추천 API가 준비되면 이곳에 오늘의 추천이 표시됩니다."
    />

    <div v-else class="d-grid gap-5">
      <section v-if="todayItems.length">
        <div class="mb-3">
          <h2 class="section-title mb-1">
            {{ homeData.today_recommendations.theme?.title || '오늘의 추천' }}
          </h2>
          <p v-if="homeData.today_recommendations.theme?.subtitle" class="meta-text mb-0">
            {{ homeData.today_recommendations.theme.subtitle }}
          </p>
        </div>
        <div class="responsive-card-grid">
          <LibraryCard v-for="library in todayItems" :key="library.id" :library="library" />
        </div>
      </section>

      <section v-if="showPersonalRecommendations">
        <div class="d-flex flex-wrap align-items-end justify-content-between gap-2 mb-3">
          <div>
            <h2 class="section-title mb-1">
              {{ personalRecommendations.title || '나에게 맞는 추천' }}
            </h2>
            <p v-if="personalRecommendations.reason" class="meta-text mb-0">
              {{ personalRecommendations.reason }}
            </p>
          </div>
          <RouterLink
            v-if="personalRecommendations.available === false"
            class="btn btn-outline-primary btn-sm"
            to="/preferences"
          >
            선호 설정
          </RouterLink>
        </div>
        <EmptyState
          v-if="personalRecommendations.available === false || !personalItems.length"
          title="개인 추천을 준비 중입니다."
          description="선호 설정이나 저장, 후기 활동이 쌓이면 맞춤 추천을 보여드립니다."
        />
        <div class="responsive-card-grid">
          <LibraryCard v-for="library in personalItems" :key="library.id" :library="library" />
        </div>
      </section>

      <section v-if="themeGroups.length">
        <h2 class="section-title">테마로 둘러보기</h2>
        <p v-if="locationMessage" class="alert alert-info py-2">{{ locationMessage }}</p>
        <div class="theme-chip-list">
          <button
            v-for="group in themeGroups"
            :key="group.purpose?.code"
            class="theme-chip"
            type="button"
            @click="goToTheme(group.purpose?.code)"
          >
            {{ group.purpose?.label || '테마 추천' }}
          </button>
        </div>
      </section>

      <section v-for="group in themeGroups" :key="group.purpose?.code">
        <h2 class="section-title">{{ group.purpose?.label || '테마 추천' }}</h2>
        <EmptyState
          v-if="!group.items?.length"
          title="이 테마의 추천이 아직 없습니다."
          description="추천 데이터가 준비되면 자동으로 표시됩니다."
        />
        <div v-else class="responsive-card-grid">
          <LibraryCard v-for="library in group.items" :key="library.id" :library="library" />
        </div>
      </section>
    </div>
  </section>
</template>
