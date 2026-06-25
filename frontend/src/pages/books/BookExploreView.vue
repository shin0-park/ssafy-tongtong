<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BookCard from '@/components/cards/BookCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import ResultCount from '@/components/navigation/ResultCount.vue'
import { fetchPopularBooks, searchBooks } from '@/services/bookService'
import { readPageQuery } from '@/utils/query'

const route = useRoute()
const router = useRouter()

const SORT_OPTIONS = [
  { value: 'title', label: '도서명' },
  { value: 'author', label: '저자' },
  { value: 'pub', label: '출판사' },
  { value: 'pubYear', label: '출판연도' },
]
const ORDER_OPTIONS = [
  { value: 'asc', label: '오름차순' },
  { value: 'desc', label: '내림차순' },
]
const DEFAULT_PAGE_SIZE = 12
const DEFAULT_SORT = 'title'
const DEFAULT_ORDER = 'asc'

const books = ref([])
const popularBooks = ref([])
const popularSnapshot = ref(null)
const responseMeta = ref({ num_found: 0, page: 1, page_size: DEFAULT_PAGE_SIZE })
const isLoading = ref(false)
const isPopularLoading = ref(false)
const error = ref(null)
const popularError = ref(null)
const popularRail = ref(null)
const filters = reactive({
  q: normalizeText(route.query.q),
  sort: normalizeSort(route.query.sort),
  order: normalizeOrder(route.query.order),
})

const hasSearchQuery = computed(() => normalizeText(route.query.q).length > 0)
const hasBooks = computed(() => books.value.length > 0)
const currentPage = computed(() => responseMeta.value.page || 1)
const pageSize = computed(() => responseMeta.value.page_size || DEFAULT_PAGE_SIZE)
const hasPreviousPage = computed(() => currentPage.value > 1)
const hasNextPage = computed(() => currentPage.value * pageSize.value < responseMeta.value.num_found)
const errorTitle = computed(() =>
  isData4LibraryConfigError(error.value)
    ? '정보나루 검색 설정이 필요합니다.'
    : '책 검색 결과를 불러오지 못했습니다.',
)
const errorMessage = computed(() =>
  isData4LibraryConfigError(error.value)
    ? '정보나루 API Key 설정이 완료되면 책 검색을 사용할 수 있습니다.'
    : error.value?.message || '네트워크 상태를 확인한 뒤 다시 시도해주세요.',
)

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeSort(value) {
  return SORT_OPTIONS.some((option) => option.value === value) ? value : DEFAULT_SORT
}

function normalizeOrder(value) {
  return ORDER_OPTIONS.some((option) => option.value === value) ? value : DEFAULT_ORDER
}

function isData4LibraryConfigError(requestError) {
  return (
    requestError?.status === 503 &&
    typeof requestError.message === 'string' &&
    requestError.message.includes('Data4Library API key')
  )
}

function buildRequestParams() {
  const pageQuery = readPageQuery(route)
  const query = normalizeText(route.query.q)

  return {
    keyword: query,
    page: pageQuery.page,
    page_size: pageQuery.page_size || DEFAULT_PAGE_SIZE,
    sort: normalizeSort(route.query.sort),
    order: normalizeOrder(route.query.order),
  }
}

function resetResults() {
  books.value = []
  responseMeta.value = { num_found: 0, page: 1, page_size: DEFAULT_PAGE_SIZE }
  error.value = null
}

async function loadBooks() {
  if (!hasSearchQuery.value) {
    resetResults()
    return
  }

  isLoading.value = true
  error.value = null

  try {
    const data = await searchBooks(buildRequestParams())
    books.value = data.results ?? []
    responseMeta.value = {
      num_found: data.num_found ?? data.count ?? 0,
      page: data.page ?? Number(route.query.page || 1),
      page_size: data.page_size ?? DEFAULT_PAGE_SIZE,
    }
  } catch (requestError) {
    books.value = []
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

async function loadPopularBooks() {
  isPopularLoading.value = true
  popularError.value = null

  try {
    const data = await fetchPopularBooks({ limit: 10, region: '21' })
    popularSnapshot.value = data.snapshot ?? null
    popularBooks.value = (data.items ?? data.results ?? data.books ?? [])
      .map((item) => item.book ?? item)
      .filter(Boolean)
  } catch (requestError) {
    popularBooks.value = []
    popularSnapshot.value = null
    popularError.value = requestError
  } finally {
    isPopularLoading.value = false
  }
}

function applySearch() {
  const nextQuery = normalizeText(filters.q)

  router.push({
    name: 'book-list',
    query: nextQuery
      ? {
          q: nextQuery,
          sort: filters.sort === DEFAULT_SORT ? undefined : filters.sort,
          order: filters.order === DEFAULT_ORDER ? undefined : filters.order,
          page: 1,
          page_size: route.query.page_size || DEFAULT_PAGE_SIZE,
        }
      : {},
  })
}

function resetSearch() {
  filters.q = ''
  filters.sort = DEFAULT_SORT
  filters.order = DEFAULT_ORDER
  router.push({ name: 'book-list' })
}

function applySort() {
  if (!hasSearchQuery.value) return

  router.push({
    name: 'book-list',
    query: {
      ...route.query,
      sort: filters.sort === DEFAULT_SORT ? undefined : filters.sort,
      order: filters.order === DEFAULT_ORDER ? undefined : filters.order,
      page: 1,
    },
  })
}

function scrollPopularBooks(direction) {
  if (!popularRail.value) return

  popularRail.value.scrollBy({
    left: direction * popularRail.value.clientWidth * 0.85,
    behavior: 'smooth',
  })
}

function goToPage(page) {
  router.push({
    name: 'book-list',
    query: {
      ...route.query,
      page,
    },
  })
}

watch(
  () => route.query,
  () => {
    filters.q = normalizeText(route.query.q)
    filters.sort = normalizeSort(route.query.sort)
    filters.order = normalizeOrder(route.query.order)
    loadBooks()
  },
)

onMounted(() => {
  loadPopularBooks()
  loadBooks()
})
</script>

<template>
  <section class="page-shell">
    <div class="page-hero page-hero-banner page-hero-books">
      <h1>책 둘러보기</h1>
      <p>읽고 싶은 책을 찾고, 부산에서 그 책을 소장한 도서관을 함께 확인해보세요.</p>
    </div>

    <section class="mb-5">
      <div class="section-header-row">
        <div>
          <h2 class="section-title mb-1">이번 주 인기 도서</h2>
          <p class="meta-text mb-0">
            {{
              popularSnapshot
                ? `${popularSnapshot.period_start} ~ ${popularSnapshot.period_end}`
                : '정보나루 인기대출도서 기반으로 보여드립니다.'
            }}
          </p>
        </div>
      </div>
      <LoadingState v-if="isPopularLoading" title="인기 도서를 불러오는 중입니다." />
      <p v-else-if="popularError" class="meta-text">인기 도서를 불러오지 못했어요.</p>
      <EmptyState
        v-else-if="!popularBooks.length"
        title="인기 도서가 아직 없습니다."
        description="집계 데이터가 준비되면 이곳에 표시됩니다."
      />
      <div v-else class="popular-book-carousel">
        <button
          class="carousel-arrow"
          type="button"
          aria-label="이전 인기 도서 보기"
          @click="scrollPopularBooks(-1)"
        >
          ‹
        </button>
        <div ref="popularRail" class="popular-book-rail" tabindex="0" aria-label="이번 주 인기 도서 목록">
          <div v-for="(book, index) in popularBooks" :key="book.isbn13 || index" class="popular-book-item">
            <BookCard :book="book" :rank="index + 1" />
          </div>
        </div>
        <button
          class="carousel-arrow"
          type="button"
          aria-label="다음 인기 도서 보기"
          @click="scrollPopularBooks(1)"
        >
          ›
        </button>
      </div>
    </section>

    <form class="content-panel p-4 mb-4" @submit.prevent="applySearch">
      <div class="book-search-row">
        <label class="form-field">
          <span>검색어</span>
          <input
            v-model.trim="filters.q"
            class="form-control"
            type="search"
            placeholder="도서명, 저자, ISBN을 입력해주세요"
          />
        </label>
        <div class="book-search-actions">
          <button class="btn btn-outline-secondary" type="button" @click="resetSearch">초기화</button>
          <button class="btn btn-primary" type="submit">검색</button>
        </div>
      </div>
    </form>

    <LoadingState v-if="isLoading" title="책 검색 결과를 불러오는 중입니다." />
    <ErrorState
      v-else-if="error"
      :title="errorTitle"
      :message="errorMessage"
      @retry="loadBooks"
    />
    <EmptyState
      v-else-if="!hasSearchQuery"
      title="도서명, 저자, ISBN으로 책을 찾아보세요."
      description="검색어를 입력하면 정보나루 책 검색 결과를 보여드립니다."
    />
    <EmptyState
      v-else-if="!hasBooks"
      title="검색 결과가 없습니다."
      description="검색어를 바꿔 다시 찾아보세요."
    />

    <template v-else>
      <div class="result-toolbar mb-3">
        <ResultCount :count="responseMeta.num_found" label="권" />
        <div class="result-sort-controls" aria-label="검색 결과 정렬">
          <label class="result-sort-select">
            <span>정렬 기준</span>
            <select v-model="filters.sort" class="form-select form-select-sm" @change="applySort">
              <option v-for="option in SORT_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label class="result-sort-select">
            <span>정렬 방향</span>
            <select v-model="filters.order" class="form-select form-select-sm" @change="applySort">
              <option v-for="option in ORDER_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
      </div>
      <div class="book-result-grid">
        <BookCard v-for="book in books" :key="book.isbn13" :book="book" />
      </div>
      <PaginationBar
        :current-page="currentPage"
        :has-previous="hasPreviousPage"
        :has-next="hasNextPage"
        @change="goToPage"
      />
    </template>
  </section>
</template>
