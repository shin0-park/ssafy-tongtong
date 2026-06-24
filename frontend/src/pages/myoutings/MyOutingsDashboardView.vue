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
const preferenceStatus = computed(() => dashboard.value?.preference_status ?? {})
const preferenceStatusCode = computed(() => preferenceStatus.value.status ?? '')
const shouldShowCollectingState = computed(() =>
  !hasDashboard.value || ['collecting', 'pending'].includes(preferenceStatusCode.value),
)
const countCards = computed(() => {
  const profile = dashboard.value?.profile_summary ?? {}
  const activity = dashboard.value?.activity_summary ?? {}

  return [
    { label: '저장 도서관', value: profile.saved_library_count },
    { label: '저장 책', value: profile.saved_book_count },
    { label: '저장 프로그램', value: profile.saved_program_count },
    { label: '내 후기', value: profile.review_count },
    { label: '좋아요한 후기', value: profile.liked_review_count },
    { label: '총 활동 신호', value: activity.total_signal_count },
  ]
})
const preferenceGroups = computed(() => {
  const summary = dashboard.value?.preference_summary ?? {}

  return [
    { title: '선호 지역', items: summary.top_regions ?? [] },
    { title: '도서관 시설', items: summary.top_library_facilities ?? [] },
    { title: '책 주제', items: summary.top_book_subjects ?? [] },
    { title: '프로그램 분류', items: summary.top_program_categories ?? [] },
    { title: '후기 태그', items: summary.top_review_tags ?? [] },
  ]
})
const outingTypeItems = computed(() => Object.entries(dashboard.value?.outing_type_summary ?? {}))

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

function displayValue(value) {
  return value === null || value === undefined ? '-' : Number(value).toLocaleString()
}

function preferenceStatusText(status) {
  const labels = {
    collecting: '행동 신호 수집 중',
    pending: '재계산 대기 중',
    ready: '계산 완료',
    failed: '계산 실패',
  }

  return labels[status] || '정보 없음'
}

function chipText(item) {
  if (typeof item === 'string') {
    return item
  }

  return item.label || item.name || item.code || item.sigungu || item.subject || displayText(item)
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
      v-else-if="shouldShowCollectingState"
      title="아직 분석할 정보가 부족해요."
      :description="preferenceStatusText(preferenceStatusCode)"
    />
    <template v-else>
      <section v-if="dashboard.summary_sentence" class="summary-hero mb-4">
        <p class="eyebrow">Summary</p>
        <h2>{{ dashboard.summary_sentence }}</h2>
      </section>

      <div class="dashboard-grid mb-4">
        <article v-for="item in countCards" :key="item.label" class="summary-card metric-card">
          <p class="meta-text mb-1">{{ item.label }}</p>
          <h2>{{ displayValue(item.value) }}</h2>
        </article>
      </div>

      <section v-if="outingTypeItems.length" class="content-panel p-4 mb-4">
        <h2 class="h5 mb-3">나들이 유형</h2>
        <div class="outing-score-list">
          <div v-for="[type, score] in outingTypeItems" :key="type" class="outing-score-row">
            <span>{{ type }}</span>
            <div class="outing-score-track" aria-hidden="true">
              <span :style="{ width: `${Math.min(Number(score) || 0, 100)}%` }"></span>
            </div>
            <strong>{{ Number(score || 0).toFixed(1) }}</strong>
          </div>
        </div>
      </section>

      <section class="content-panel p-4 mb-4">
        <h2 class="h5 mb-3">선호 요약</h2>
        <div class="preference-summary-grid">
          <div v-for="group in preferenceGroups" :key="group.title">
            <h3 class="h6">{{ group.title }}</h3>
            <p v-if="!group.items.length" class="meta-text mb-0">정보 없음</p>
            <div v-else class="d-flex flex-wrap gap-2">
              <span v-for="item in group.items" :key="chipText(item)" class="book-chip">
                {{ chipText(item) }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="content-panel p-4 mb-4">
        <h2 class="h5 mb-3">분석 기준</h2>
        <p class="meta-text mb-2">
          {{ dashboard.analysis_basis?.basis_text || displayText(dashboard.analysis_basis) }}
        </p>
        <p class="meta-text mb-0">
          신호 {{ displayValue(dashboard.analysis_basis?.signal_count) }}개
        </p>
      </section>

      <section class="content-panel p-4">
        <h2 class="h5 mb-3">선호 상태</h2>
        <div class="d-flex flex-wrap align-items-center gap-2">
          <span class="status-badge status-badge-muted">
            {{ preferenceStatusText(preferenceStatusCode) }}
          </span>
          <span class="meta-text">신호 {{ displayValue(preferenceStatus.signal_count) }}개</span>
          <span v-if="preferenceStatus.calculated_at" class="meta-text">
            {{ new Date(preferenceStatus.calculated_at).toLocaleString('ko-KR') }}
          </span>
        </div>
      </section>
    </template>
  </section>
</template>
