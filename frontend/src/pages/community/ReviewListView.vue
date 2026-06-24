<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import ReviewCard from '@/components/cards/ReviewCard.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import ResultCount from '@/components/navigation/ResultCount.vue'
import { fetchReviews } from '@/services/reviewService'
import { extractErrorMessage } from '@/utils/apiError'
import { normalizeOrdering, readPageQuery, readStringQuery } from '@/utils/query'

const ORDERING_OPTIONS = ['-created_at', '-view_count', '-like_count']

const route = useRoute()
const router = useRouter()

const reviews = ref([])
const count = ref(0)
const isLoading = ref(false)
const errorMessage = ref('')

const filters = reactive({
  q: '',
  library_id: '',
  tag: '',
  user_id: '',
  ordering: '-created_at',
})

const page = computed(() => readPageQuery(route))
const pageSize = computed(() => Number(route.query.page_size) || 12)
const hasSearched = computed(() =>
  Boolean(filters.q || filters.library_id || filters.tag || filters.user_id),
)

function syncFromRoute() {
  filters.q = readStringQuery(route, 'q')
  filters.library_id = readStringQuery(route, 'library_id')
  filters.tag = readStringQuery(route, 'tag')
  filters.user_id = readStringQuery(route, 'user_id')
  filters.ordering = normalizeOrdering(route.query.ordering, ORDERING_OPTIONS, '-created_at')
}

async function loadReviews() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const data = await fetchReviews({
      ...filters,
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
      tag: filters.tag || undefined,
      user_id: filters.user_id || undefined,
      ordering: filters.ordering !== '-created_at' ? filters.ordering : undefined,
      page: 1,
      page_size: pageSize.value !== 12 ? pageSize.value : undefined,
    },
  })
}

function resetFilters() {
  router.push({ path: '/community' })
}

function goToPage(nextPage) {
  router.push({
    path: '/community',
    query: {
      ...route.query,
      page: nextPage,
    },
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
    <div class="page-header">
      <p class="eyebrow">커뮤니티</p>
      <div class="d-flex flex-wrap align-items-end justify-content-between gap-3">
        <div>
          <h1>도서관 후기</h1>
          <p class="page-description mb-0">
            이용자들이 남긴 도서관 경험과 관련 책, 프로그램을 함께 살펴보세요.
          </p>
        </div>
        <RouterLink class="btn btn-primary" to="/reviews/new">후기 작성</RouterLink>
      </div>
    </div>

    <form class="content-panel p-4 mb-4" @submit.prevent="applyFilters">
      <div class="filter-grid">
        <label class="form-field">
          <span>검색어</span>
          <input v-model.trim="filters.q" class="form-control" type="search" placeholder="후기 내용 검색" />
        </label>
        <label class="form-field">
          <span>도서관 ID</span>
          <input v-model.trim="filters.library_id" class="form-control" inputmode="numeric" />
        </label>
        <label class="form-field">
          <span>태그</span>
          <input v-model.trim="filters.tag" class="form-control" />
        </label>
        <label class="form-field">
          <span>정렬</span>
          <select v-model="filters.ordering" class="form-select">
            <option value="-created_at">최신순</option>
            <option value="-view_count">조회순</option>
            <option value="-like_count">좋아요순</option>
          </select>
        </label>
      </div>
      <div class="d-flex flex-wrap justify-content-end gap-2 mt-3">
        <button class="btn btn-outline-secondary" type="button" @click="resetFilters">초기화</button>
        <button class="btn btn-primary" type="submit">검색</button>
      </div>
    </form>

    <LoadingState v-if="isLoading" title="후기를 불러오는 중입니다." />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadReviews" />
    <EmptyState
      v-else-if="!reviews.length"
      :title="hasSearched ? '조건에 맞는 후기가 없어요.' : '아직 등록된 후기가 없어요.'"
      description="후기가 0건인 상태는 오류가 아니며, 데이터가 쌓이면 이곳에 표시됩니다."
    />
    <template v-else>
      <ResultCount class="mb-3" :count="count" label="후기" />
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
