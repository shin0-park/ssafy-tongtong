<script setup>
import { computed, onMounted, ref } from 'vue'

import LibraryCard from '@/components/cards/LibraryCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchHome } from '@/services/homeService'

const homeData = ref(null)
const isLoading = ref(false)
const error = ref(null)

const todayItems = computed(() => homeData.value?.today_recommendations?.items ?? [])
const themeGroups = computed(() => homeData.value?.theme_recommendations ?? [])
const hasContent = computed(
  () => todayItems.value.length > 0 || themeGroups.value.some((group) => group.items?.length),
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

onMounted(loadHome)
</script>

<template>
  <section class="page-shell">
    <div class="mb-4">
      <h1 class="page-title">오늘의 도서관 나들이</h1>
      <p class="page-subtitle">부산 지역 도서관을 추천과 테마별 목록으로 둘러보세요.</p>
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
        <h2 class="section-title">
          {{ homeData.today_recommendations.theme?.title || '오늘의 추천' }}
        </h2>
        <div class="row g-3">
          <div v-for="library in todayItems" :key="library.id" class="col-md-6 col-lg-4">
            <LibraryCard :library="library" />
          </div>
        </div>
      </section>

      <section v-for="group in themeGroups" :key="group.purpose?.code">
        <h2 class="section-title">{{ group.purpose?.label || '테마 추천' }}</h2>
        <EmptyState
          v-if="!group.items?.length"
          title="이 테마의 추천이 아직 없습니다."
          description="추천 데이터가 준비되면 자동으로 표시됩니다."
        />
        <div v-else class="row g-3">
          <div v-for="library in group.items" :key="library.id" class="col-md-6 col-lg-4">
            <LibraryCard :library="library" />
          </div>
        </div>
      </section>
    </div>
  </section>
</template>
