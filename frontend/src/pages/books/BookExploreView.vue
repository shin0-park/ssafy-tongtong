<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BookCard from '@/components/cards/BookCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { searchBooks } from '@/services/bookService'
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
const responseMeta = ref({ num_found: 0, page: 1, page_size: DEFAULT_PAGE_SIZE })
const isLoading = ref(false)
const error = ref(null)
const filters = reactive({
  search_type: normalizeSearchType(route.query.search_type),
  q: normalizeText(route.query.q),
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

function applySearch() {
  const nextQuery = normalizeText(filters.q)

  router.push({
    name: 'book-list',
    query: nextQuery
      ? {
          search_type: normalizeSearchType(filters.search_type),
          q: nextQuery,
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
    loadBooks()
  },
)

onMounted(loadBooks)
</script>

<template>
  <section class="page-shell">
    <div class="mb-4">
      <h1 class="page-title">책 둘러보기</h1>
      <p class="page-subtitle">
        정보나루 책 검색을 통해 부산 도서관에서 찾고 싶은 책의 기본 정보를 확인합니다.
      </p>
    </div>

    <form class="content-panel p-3 mb-4" @submit.prevent="applySearch">
      <div class="row g-2 align-items-end">
        <div class="col-md-3">
          <label class="form-label" for="book-search-type">검색 기준</label>
          <select id="book-search-type" v-model="filters.search_type" class="form-select">
            <option v-for="type in SEARCH_TYPES" :key="type.value" :value="type.value">
              {{ type.label }}
            </option>
          </select>
        </div>
        <div class="col-md-7">
          <label class="form-label" for="book-query">검색어</label>
          <input
            id="book-query"
            v-model.trim="filters.q"
            class="form-control"
            type="search"
            placeholder="도서명, 저자, ISBN, 키워드, 출판사"
          />
        </div>
        <div class="col-md-2 d-grid">
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
      description="검색어를 바꾸거나 다른 검색 기준을 선택해보세요."
    />

    <template v-else>
      <p class="meta-text mb-3">총 {{ responseMeta.num_found.toLocaleString() }}권</p>
      <div class="row g-3">
        <div v-for="book in books" :key="book.isbn13" class="col-md-6 col-lg-4">
          <BookCard :book="book" />
        </div>
      </div>
      <div class="d-flex justify-content-center gap-2 mt-4">
        <button
          class="btn btn-outline-secondary"
          type="button"
          :disabled="!hasPreviousPage"
          @click="goToPage(currentPage - 1)"
        >
          이전
        </button>
        <span class="meta-text align-self-center">{{ currentPage }}페이지</span>
        <button
          class="btn btn-outline-secondary"
          type="button"
          :disabled="!hasNextPage"
          @click="goToPage(currentPage + 1)"
        >
          다음
        </button>
      </div>
    </template>
  </section>
</template>
