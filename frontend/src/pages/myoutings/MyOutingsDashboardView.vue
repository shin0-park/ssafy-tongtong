<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchMyOutingsDashboard } from '@/services/myOutingsService'
import { extractErrorMessage } from '@/utils/apiError'

const dashboard = ref(null)
const isLoading = ref(false)
const errorMessage = ref('')

const hasDashboard = computed(() => Boolean(dashboard.value && Object.keys(dashboard.value).length))
const summaryItems = computed(() => [
  {
    title: '프로필',
    value: dashboard.value?.profile_summary,
  },
  {
    title: '활동',
    value: dashboard.value?.activity_summary,
  },
  {
    title: '선호',
    value: dashboard.value?.preference_summary,
  },
  {
    title: '나들이 유형',
    value: dashboard.value?.outing_type_summary,
  },
])

async function loadDashboard() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    dashboard.value = await fetchMyOutingsDashboard()
  } catch (error) {
    dashboard.value = null
    errorMessage.value = extractErrorMessage(error, '나의 나들이 정보를 불러오지 못했어요.')
  } finally {
    isLoading.value = false
  }
}

function displayText(value) {
  if (!value) {
    return '정보 없음'
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : '정보 없음'
  }

  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([key, item]) => `${key}: ${Array.isArray(item) ? item.join(', ') : item}`)
      .join('\n')
  }

  return value
}

onMounted(loadDashboard)
</script>

<template>
  <section class="page-shell">
    <div class="page-header">
      <p class="eyebrow">나의 나들이</p>
      <h1>Dashboard</h1>
      <p class="page-description mb-0">
        저장, 후기, 선호 정보를 기반으로 나의 도서관 이용 흐름을 확인합니다.
      </p>
    </div>

    <div class="myoutings-nav mb-4">
      <RouterLink class="btn btn-primary btn-sm" to="/my-outings/dashboard">Dashboard</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/libraries">도서관</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/books">책</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/programs">프로그램</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/reviews">내 후기</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/liked-reviews">좋아요한 후기</RouterLink>
    </div>

    <LoadingState v-if="isLoading" title="나의 나들이를 불러오는 중입니다." />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadDashboard" />
    <EmptyState
      v-else-if="!hasDashboard || dashboard.preference_status === 'collecting'"
      title="아직 분석할 정보가 부족해요."
      description="선호 설정과 저장, 후기 활동이 쌓이면 이곳에 요약이 표시됩니다."
    />
    <template v-else>
      <section v-if="dashboard.summary_sentence" class="summary-hero mb-4">
        <p class="eyebrow">Summary</p>
        <h2>{{ dashboard.summary_sentence }}</h2>
      </section>

      <div class="dashboard-grid mb-4">
        <article v-for="item in summaryItems" :key="item.title" class="summary-card">
          <h2>{{ item.title }}</h2>
          <p>{{ displayText(item.value) }}</p>
        </article>
      </div>

      <section class="content-panel p-4 mb-4">
        <h2 class="h5 mb-3">분석 기준</h2>
        <p class="meta-text mb-0 preserve-lines">{{ displayText(dashboard.analysis_basis) }}</p>
      </section>

      <section class="content-panel p-4">
        <h2 class="h5 mb-3">선호 상태</h2>
        <p class="meta-text mb-0">{{ dashboard.preference_status || '정보 없음' }}</p>
      </section>
    </template>
  </section>
</template>
