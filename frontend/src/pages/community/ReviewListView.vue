<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ReviewCard from '@/components/cards/ReviewCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import ResultCount from '@/components/navigation/ResultCount.vue'
import { fetchReviews } from '@/services/reviewService'
import { extractErrorMessage } from '@/utils/apiError'
import { REVIEW_TAG_LABELS } from '@/utils/display'
import { normalizeOrdering, readPageQuery, readStringQuery } from '@/utils/query'

const ORDERING_OPTIONS = [
  { value: '-created_at', label: '최신순' },
  { value: '-view_count', label: '조회순' },
  { value: '-like_count', label: '좋아요순' },
]
const TAG_OPTIONS = [
  { value: 'review_quiet_study', label: REVIEW_TAG_LABELS.review_quiet_study },
  { value: 'review_seats_sufficient', label: REVIEW_TAG_LABELS.review_seats_sufficient },
  { value: 'review_comfortable_reading_space', label: REVIEW_TAG_LABELS.review_comfortable_reading_space },
  { value: 'review_comfortable_space', label: REVIEW_TAG_LABELS.review_comfortable_space },
  { value: 'review_clean_space', label: REVIEW_TAG_LABELS.review_clean_space },
  { value: 'review_books_diverse', label: REVIEW_TAG_LABELS.review_books_diverse },
  { value: 'review_easy_book_finding', label: REVIEW_TAG_LABELS.review_easy_book_finding },
  { value: 'review_good_programs', label: REVIEW_TAG_LABELS.review_good_programs },
  { value: 'review_children_friendly', label: REVIEW_TAG_LABELS.review_children_friendly },
  { value: 'review_parking_convenient', label: REVIEW_TAG_LABELS.review_parking_convenient },
  { value: 'review_wifi_reliable', label: REVIEW_TAG_LABELS.review_wifi_reliable },
  { value: 'review_kind_guidance', label: REVIEW_TAG_LABELS.review_kind_guidance },
  { value: 'review_well_managed', label: REVIEW_TAG_LABELS.review_well_managed },
]

const route = useRoute()
const router = useRouter()

const reviews = ref([])
const count = ref(0)
const isLoading = ref(false)
const errorMessage = ref('')
const filters = reactive({
  q: '',
  library_id: '',
  tag: [],
  ordering: '-created_at',
})

const pageQuery = computed(() => readPageQuery(route))
const page = computed(() => pageQuery.value.page)
const pageSize = computed(() => pageQuery.value.page_size || 12)
const hasSearched = computed(() => Boolean(filters.q || filters.library_id || filters.tag.length))

function splitQuery(value) {
  if (!value) return []
  if (Array.isArray(value)) return value.flatMap((item) => String(item).split(',')).filter(Boolean)
  return String(value).split(',').map((item) => item.trim()).filter(Boolean)
}

function syncFromRoute() {
  filters.q = readStringQuery(route, 'q')
  filters.library_id = readStringQuery(route, 'library_id')
  filters.tag = splitQuery(route.query.tag)
  filters.ordering = normalizeOrdering(route.query.ordering, ORDERING_OPTIONS.map((item) => item.value), '-created_at')
}

async function loadReviews() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const data = await fetchReviews({
      q: filters.q,
      library_id: filters.library_id,
      tag: filters.tag.join(','),
      ordering: filters.ordering,
      page: page.value,
      page_size: pageSize.value,
    })
    reviews.value = data.results ?? []
    count.value = data.count ?? reviews.value.length
  } catch (error) {
    reviews.value = []
    count.value = 0
    errorMessage.value = extractErrorMessage(error, '후기 목록을 불러오지 못했어요.')
  } finally {
    isLoading.value = false
  }
}

function applyFilters() {
  router.push({
    path: '/community',
    query: {
      q: filters.q || undefined,
      library_id: filters.library_id || undefined,
      tag: filters.tag.length ? filters.tag.join(',') : undefined,
      ordering: filters.ordering !== '-created_at' ? filters.ordering : undefined,
      page: 1,
      page_size: pageSize.value !== 12 ? pageSize.value : undefined,
    },
  })
}

function resetFilters() {
  router.push({ path: '/community' })
}

function applySort() {
  router.push({
    path: '/community',
    query: {
      ...route.query,
      ordering: filters.ordering !== '-created_at' ? filters.ordering : undefined,
      page: 1,
    },
  })
}

function goToPage(nextPage) {
  router.push({
    path: '/community',
    query: { ...route.query, page: nextPage },
  })
}

watch(
  () => route.query,
  async () => {
    syncFromRoute()
    await loadReviews()
  },
)

onMounted(async () => {
  syncFromRoute()
  await loadReviews()
})
</script>

<template>
  <section class="page-shell">
    <div class="page-hero page-hero-banner page-hero-community">
      <h1>커뮤니티</h1>
      <p>도서관 이용 후기와 관련 책, 프로그램 이야기를 함께 둘러보세요.</p>
      <RouterLink class="btn btn-primary mt-4" to="/reviews/new">후기 작성</RouterLink>
    </div>

    <form class="content-panel p-4 mb-4 filter-panel" @submit.prevent="applyFilters">
      <div class="filter-grid">
        <label class="form-field">
          <span>도서관명 또는 후기 내용</span>
          <input v-model.trim="filters.q" class="form-control" type="search" placeholder="검색어 입력" />
        </label>
        <label class="form-field">
          <span>도서관 ID</span>
          <input v-model.trim="filters.library_id" class="form-control" inputmode="numeric" />
        </label>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">후기 태그</p>
        <div class="filter-chip-grid">
          <label v-for="tag in TAG_OPTIONS" :key="tag.value" class="filter-chip">
            <input v-model="filters.tag" type="checkbox" :value="tag.value" />
            <span>{{ tag.label }}</span>
          </label>
        </div>
      </div>

      <div class="d-flex flex-wrap justify-content-end gap-2">
        <button class="btn btn-outline-secondary" type="button" @click="resetFilters">초기화</button>
        <button class="btn btn-primary" type="submit">검색</button>
      </div>
    </form>

    <LoadingState v-if="isLoading" title="후기를 불러오는 중입니다." />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadReviews" />
    <EmptyState
      v-else-if="!reviews.length"
      :title="hasSearched ? '조건에 맞는 후기가 없어요.' : '아직 등록된 후기가 없어요.'"
      description="첫 후기를 남기거나 검색 조건을 바꿔보세요."
    />
    <template v-else>
      <div class="result-toolbar mb-3">
        <ResultCount :count="count" label="개" />
        <div class="result-sort-controls" aria-label="후기 목록 정렬">
          <label class="result-sort-select">
            <span>정렬</span>
            <select v-model="filters.ordering" class="form-select form-select-sm" @change="applySort">
              <option v-for="option in ORDERING_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
      </div>
      <div class="stack-list">
        <ReviewCard v-for="review in reviews" :key="review.id" :review="review" />
      </div>
      <PaginationBar
        class="mt-4"
        :page="page"
        :page-size="pageSize"
        :total-count="count"
        @change="goToPage"
      />
    </template>
  </section>
</template>
