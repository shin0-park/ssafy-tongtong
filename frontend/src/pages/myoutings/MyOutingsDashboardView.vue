<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchMyOutingsDashboard } from '@/services/myOutingsService'
import { extractErrorMessage } from '@/utils/apiError'
import { FACILITY_LABELS, PURPOSE_SHORT_LABELS, formatNumber, isBrokenText, labelFromMap } from '@/utils/display'

const dashboard = ref(null)
const isLoading = ref(false)
const errorMessage = ref('')

const hasDashboard = computed(() => Boolean(dashboard.value && Object.keys(dashboard.value).length))
const profileSummary = computed(() => dashboard.value?.profile_summary ?? {})
const activitySummary = computed(() => dashboard.value?.activity_summary ?? {})
const preferenceSummary = computed(() => dashboard.value?.preference_summary ?? {})
const outingTypeSummary = computed(() => dashboard.value?.outing_type_summary ?? {})
const signalCount = computed(() => activitySummary.value.total_signal_count ?? dashboard.value?.analysis_basis?.signal_count ?? 0)
const hasEnoughData = computed(() => signalCount.value > 0)
const greetingName = computed(() => profileSummary.value.nickname || '나들이')
const summarySentence = computed(() => {
  const sentence = dashboard.value?.summary_sentence
  if (sentence && !isBrokenText(sentence)) return sentence
  const topAxis = axisItems.value[0]
  if (!hasEnoughData.value) return '저장과 후기 활동이 쌓이면 나의 도서관 취향을 분석해드릴게요.'
  return `${labelFromMap(PURPOSE_SHORT_LABELS, topAxis?.code, '도서관')} 성향이 가장 두드러져요. 저장한 도서관, 책, 프로그램과 후기 태그를 바탕으로 분석했어요.`
})
const basisText = computed(() => {
  const text = dashboard.value?.analysis_basis?.basis_text
  if (text && !isBrokenText(text)) return text
  return hasEnoughData.value
    ? '저장한 도서관, 책, 프로그램과 작성·좋아요한 후기를 바탕으로 분석했어요.'
    : '도서관, 책, 프로그램을 저장하거나 후기를 남기면 분석이 시작됩니다.'
})
const axisItems = computed(() =>
  Object.entries(outingTypeSummary.value)
    .map(([code, value]) => ({
      code,
      label: labelFromMap(PURPOSE_SHORT_LABELS, code, code),
      value: Number(value) || 0,
    }))
    .sort((a, b) => b.value - a.value),
)
const countCards = computed(() => [
  { label: '저장한 도서관', value: profileSummary.value.saved_library_count, to: '/my-outings/libraries' },
  { label: '저장한 책', value: profileSummary.value.saved_book_count, to: '/my-outings/books' },
  { label: '저장한 프로그램', value: profileSummary.value.saved_program_count, to: '/my-outings/programs' },
  { label: '내가 쓴 후기', value: profileSummary.value.review_count, to: '/my-outings/reviews' },
  { label: '좋아요한 후기', value: profileSummary.value.liked_review_count, to: '/my-outings/liked-reviews' },
  { label: '분석 신호', value: signalCount.value, to: null },
])
const interestGroups = computed(() => [
  { title: '내가 많이 접한 태그', items: preferenceSummary.value.top_review_tags ?? [] },
  { title: '도서 주제', items: preferenceSummary.value.top_book_subjects ?? [] },
  { title: '프로그램 분야', items: preferenceSummary.value.top_program_categories ?? [] },
  { title: '자주 찾는 지역', items: preferenceSummary.value.top_regions ?? [] },
  { title: '선호 시설', items: preferenceSummary.value.top_library_facilities ?? [] },
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

function itemLabel(item) {
  if (typeof item === 'string') return item
  if (item.sigungu) return item.sigungu
  if (item.code && FACILITY_LABELS[item.code]) return FACILITY_LABELS[item.code]
  return item.label || item.name || item.subject || item.code || '정보 없음'
}

onMounted(loadDashboard)
</script>

<template>
  <section class="page-shell">
    <div class="page-hero">
      <h1>나의 나들이</h1>
      <p>저장한 도서관, 책, 문화 프로그램과 후기 활동을 모아 보고 나의 이용 성향을 확인합니다.</p>
      <div class="page-hero-visual" aria-hidden="true">▧</div>
    </div>

    <LoadingState v-if="isLoading" title="나의 나들이를 불러오는 중입니다." />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadDashboard" />
    <EmptyState
      v-else-if="!hasDashboard"
      title="나의 나들이 정보가 아직 없습니다."
      description="도서관, 책, 프로그램을 저장하거나 후기를 남기면 이곳에 표시됩니다."
    />
    <template v-else>
      <section class="dashboard-hero-grid mb-4">
        <article class="content-panel p-4">
          <p class="eyebrow">프로필 및 요약</p>
          <h2 class="section-title">{{ greetingName }}님, 반가워요!</h2>
          <p class="mb-3">{{ summarySentence }}</p>
          <p class="meta-text mb-0">{{ basisText }}</p>
        </article>

        <article class="content-panel p-4">
          <p class="eyebrow">최근 활동 기준</p>
          <h2 class="section-title">{{ formatNumber(signalCount, '0') }}개 활동 신호</h2>
          <p class="meta-text mb-0">
            저장 {{ formatNumber(activitySummary.total_saved_count, '0') }}개 · 후기
            {{ formatNumber(activitySummary.total_review_count, '0') }}개 · 좋아요
            {{ formatNumber(activitySummary.total_like_count, '0') }}개
          </p>
        </article>
      </section>

      <div class="dashboard-grid mb-4">
        <RouterLink
          v-for="item in countCards"
          :key="item.label"
          class="summary-card metric-card text-decoration-none"
          :to="item.to || '/my-outings/dashboard'"
        >
          <p class="meta-text mb-1">{{ item.label }}</p>
          <h2>{{ formatNumber(item.value, '0') }}</h2>
        </RouterLink>
      </div>

      <section class="content-panel p-4 mb-4">
        <h2 class="section-title">나의 나들이 성향</h2>
        <div v-if="axisItems.length" class="outing-score-list">
          <div v-for="item in axisItems" :key="item.code" class="outing-score-row">
            <span>{{ item.label }}</span>
            <div class="outing-score-track" aria-hidden="true">
              <span :style="{ width: `${Math.min(item.value, 100)}%` }"></span>
            </div>
            <strong>{{ item.value.toFixed(1) }}%</strong>
          </div>
        </div>
        <p v-else class="meta-text mb-0">성향 분석을 위한 활동이 아직 부족합니다.</p>
      </section>

      <section class="content-panel p-4 mb-4">
        <h2 class="section-title">나의 관심 분야</h2>
        <div class="preference-summary-grid">
          <div v-for="group in interestGroups" :key="group.title">
            <h3 class="h6">{{ group.title }}</h3>
            <p v-if="!group.items.length" class="meta-text mb-0">정보 없음</p>
            <div v-else class="d-flex flex-wrap gap-2">
              <span v-for="item in group.items" :key="`${group.title}-${itemLabel(item)}`" class="book-chip">
                {{ itemLabel(item) }}
                <template v-if="item.count"> {{ item.count }}회</template>
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="content-panel p-4">
        <h2 class="section-title">저장·후기 목록</h2>
        <div class="theme-card-grid">
          <RouterLink class="theme-card-button text-decoration-none" to="/my-outings/libraries">
            <strong>저장한 도서관</strong>
            <span class="meta-text">찜한 도서관 목록</span>
          </RouterLink>
          <RouterLink class="theme-card-button text-decoration-none" to="/my-outings/books">
            <strong>저장한 책</strong>
            <span class="meta-text">관심 도서 목록</span>
          </RouterLink>
          <RouterLink class="theme-card-button text-decoration-none" to="/my-outings/programs">
            <strong>저장한 문화 프로그램</strong>
            <span class="meta-text">관심 프로그램 목록</span>
          </RouterLink>
          <RouterLink class="theme-card-button text-decoration-none" to="/my-outings/liked-reviews">
            <strong>좋아요한 후기</strong>
            <span class="meta-text">공감한 후기 목록</span>
          </RouterLink>
          <RouterLink class="theme-card-button text-decoration-none" to="/my-outings/reviews">
            <strong>내가 쓴 후기</strong>
            <span class="meta-text">작성한 후기 목록</span>
          </RouterLink>
        </div>
      </section>
    </template>
  </section>
</template>
