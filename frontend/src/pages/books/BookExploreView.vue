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

const SEARCH_TYPES = [
  { value: 'title', label: '도서명' },
  { value: 'author', label: '저자' },
  { value: 'isbn', label: 'ISBN' },
  { value: 'keyword', label: '키워드' },
  { value: 'publisher', label: '출판사' },
]
const SEARCH_TYPE_VALUES = new Set(SEARCH_TYPES.map((type) => type.value))
const DEFAULT_PAGE_SIZE = 20

const books = ref([])
const popularBooks = ref([])
const responseMeta = ref({ num_found: 0, page: 1, page_size: DEFAULT_PAGE_SIZE })
const isLoading = ref(false)
const isPopularLoading = ref(false)
const error = ref(null)
const popularError = ref(null)
const filters = reactive({
  search_type: normalizeSearchType(route.query.search_type),
  q: normalizeText(route.query.q),
  sort: normalizeText(route.query.sort),
  order: normalizeText(route.query.order),
})

const hasSearchQuery = computed(() => normalizeText(route.query.q).length > 0)
const hasBooks = computed(() => books.value.length > 0)
const currentPage = computed(() => responseMeta.value.page || 1)
const pageSize = computed(() => responseMeta.value.page_size || DEFAULT_PAGE_SIZE)
const hasPreviousPage = computed(() => currentPage.value > 1)
const hasNextPage = computed(() => currentPage.value * pageSize.value < responseMeta.value.num_found)

const errorTitle = computed(() => {
  if (isData4LibraryConfigError(error.value)) {
    return '외부 도서 검색 설정이 아직 완료되지 않았어요.'
  }

  return '책 검색 결과를 불러오지 못했습니다.'
})

const errorMessage = computed(() => {
  if (isData4LibraryConfigError(error.value)) {
    return '정보나루 API Key 설정이 끝나면 책 검색을 사용할 수 있습니다.'
  }

  return error.value?.message || '네트워크 상태를 확인한 뒤 다시 시도해주세요.'
})

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeSearchType(value) {
  return SEARCH_TYPE_VALUES.has(value) ? value : 'title'
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

  return {
    search_type: normalizeSearchType(route.query.search_type),
    q: normalizeText(route.query.q),
    page: pageQuery.page,
    page_size: pageQuery.page_size || DEFAULT_PAGE_SIZE,
    sort: normalizeText(route.query.sort),
    order: normalizeText(route.query.order),
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
      num_found: data.num_found ?? 0,
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
    const data = await fetchPopularBooks({ limit: 6 })
    popularBooks.value = data.results ?? data.books ?? []
  } catch (requestError) {
    popularBooks.value = []
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
          search_type: normalizeSearchType(filters.search_type),
          q: nextQuery,
          sort: filters.sort || undefined,
          order: filters.order || undefined,
          page: 1,
          page_size: route.query.page_size || DEFAULT_PAGE_SIZE,
        }
      : {},
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
    filters.search_type = normalizeSearchType(route.query.search_type)
    filters.q = normalizeText(route.query.q)
    filters.sort = normalizeText(route.query.sort)
    filters.order = normalizeText(route.query.order)
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
    <div class="page-header">
      <h1 class="page-title">책 둘러보기</h1>
      <p class="page-subtitle">
        정보나루 책 검색과 주간 인기 도서를 함께 살펴봅니다.
      </p>
    </div>

    <section class="mb-5">
      <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <h2 class="section-title mb-0">주간 인기 도서</h2>
      </div>
      <LoadingState v-if="isPopularLoading" title="인기 도서를 불러오는 중입니다." />
      <p v-else-if="popularError" class="meta-text">인기 도서를 불러오지 못했어요.</p>
      <EmptyState
        v-else-if="!popularBooks.length"
        title="인기 도서가 아직 없어요."
        description="집계 데이터가 준비되면 이곳에 표시됩니다."
      />
      <div v-else class="responsive-card-grid">
        <BookCard v-for="book in popularBooks" :key="book.isbn13" :book="book" />
      </div>
    </section>

    <form class="content-panel p-4 mb-4" @submit.prevent="applySearch">
      <div class="filter-grid">
        <label class="form-field">
          <span>검색 기준</span>
          <select v-model="filters.search_type" class="form-select">
            <option v-for="type in SEARCH_TYPES" :key="type.value" :value="type.value">
              {{ type.label }}
            </option>
          </select>
        </label>
        <label class="form-field">
          <span>검색어</span>
          <input
            v-model.trim="filters.q"
            class="form-control"
            type="search"
            placeholder="도서명, 저자, ISBN, 키워드, 출판사"
          />
        </label>
        <label class="form-field">
          <span>정렬 기준</span>
          <input v-model.trim="filters.sort" class="form-control" type="text" placeholder="loan_count" />
        </label>
        <label class="form-field">
          <span>정렬 방향</span>
          <select v-model="filters.order" class="form-select">
            <option value="">기본</option>
            <option value="asc">오름차순</option>
            <option value="desc">내림차순</option>
          </select>
        </label>
      </div>
      <div class="d-flex justify-content-end gap-2 mt-3">
        <button class="btn btn-primary" type="submit">검색</button>
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
      description="검색어를 바꾸거나 다른 검색 기준을 선택해보세요."
    />

    <template v-else>
      <ResultCount :count="responseMeta.num_found" label="권" />
      <div class="responsive-card-grid">
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
