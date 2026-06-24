<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import LibraryCard from '@/components/cards/LibraryCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchLibraries } from '@/services/libraryService'
import { readPageQuery } from '@/utils/query'

const route = useRoute()
const router = useRouter()

const libraries = ref([])
const pagination = ref({ count: 0, next: null, previous: null })
const isLoading = ref(false)
const error = ref(null)
const filters = reactive({
  q: route.query.q || '',
  sigungu: route.query.sigungu || '',
  library_type: route.query.library_type || '',
})

const hasLibraries = computed(() => libraries.value.length > 0)

function buildRequestParams() {
  return {
    ...readPageQuery(route),
    q: route.query.q,
    sigungu: route.query.sigungu,
    library_type: route.query.library_type,
  }
}

async function loadLibraries() {
  isLoading.value = true
  error.value = null

  try {
    const data = await fetchLibraries(buildRequestParams())
    libraries.value = data.results ?? []
    pagination.value = {
      count: data.count ?? 0,
      next: data.next ?? null,
      previous: data.previous ?? null,
    }
  } catch (requestError) {
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

function applyFilters() {
  router.push({
    name: 'library-list',
    query: {
      q: filters.q || undefined,
      sigungu: filters.sigungu || undefined,
      library_type: filters.library_type || undefined,
      page: undefined,
    },
  })
}

function goToPage(page) {
  router.push({
    name: 'library-list',
    query: {
      ...route.query,
      page,
    },
  })
}

watch(
  () => route.query,
  () => {
    filters.q = route.query.q || ''
    filters.sigungu = route.query.sigungu || ''
    filters.library_type = route.query.library_type || ''
    loadLibraries()
  },
)

onMounted(loadLibraries)
</script>

<template>
  <section class="page-shell">
    <div class="mb-4">
      <h1 class="page-title">도서관 찾기</h1>
      <p class="page-subtitle">검색어, 구군, 도서관 유형으로 현재 공개 API가 지원하는 범위만 조회합니다.</p>
    </div>

    <form class="content-panel p-3 mb-4" @submit.prevent="applyFilters">
      <div class="row g-2 align-items-end">
        <div class="col-md-5">
          <label class="form-label" for="library-query">검색어</label>
          <input id="library-query" v-model.trim="filters.q" class="form-control" type="search" />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="library-sigungu">구군</label>
          <input id="library-sigungu" v-model.trim="filters.sigungu" class="form-control" type="text" />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="library-type">유형</label>
          <input
            id="library-type"
            v-model.trim="filters.library_type"
            class="form-control"
            type="text"
          />
        </div>
        <div class="col-md-1 d-grid">
          <button class="btn btn-primary" type="submit">검색</button>
        </div>
      </div>
    </form>

    <LoadingState v-if="isLoading" title="도서관 목록을 불러오는 중입니다." />
    <ErrorState
      v-else-if="error"
      title="도서관 목록을 불러오지 못했습니다."
      :message="error.message"
      @retry="loadLibraries"
    />
    <EmptyState
      v-else-if="!hasLibraries"
      title="조건에 맞는 도서관이 없습니다."
      description="검색 조건을 바꾸면 다른 결과를 볼 수 있습니다."
    />

    <template v-else>
      <p class="meta-text mb-3">총 {{ pagination.count }}곳</p>
      <div class="row g-3">
        <div v-for="library in libraries" :key="library.id" class="col-md-6 col-lg-4">
          <LibraryCard :library="library" />
        </div>
      </div>
      <div class="d-flex justify-content-center gap-2 mt-4">
        <button
          class="btn btn-outline-secondary"
          type="button"
          :disabled="!pagination.previous"
          @click="goToPage(Number(route.query.page || 1) - 1)"
        >
          이전
        </button>
        <button
          class="btn btn-outline-secondary"
          type="button"
          :disabled="!pagination.next"
          @click="goToPage(Number(route.query.page || 1) + 1)"
        >
          다음
        </button>
      </div>
    </template>
  </section>
</template>
