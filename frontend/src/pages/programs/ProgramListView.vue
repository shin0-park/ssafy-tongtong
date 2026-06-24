<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ProgramCard from '@/components/cards/ProgramCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchPrograms } from '@/services/programService'
import { readPageQuery } from '@/utils/query'

const route = useRoute()
const router = useRouter()

const DEFAULT_PAGE_SIZE = 20

const programs = ref([])
const pagination = ref({ count: 0, next: null, previous: null })
const isLoading = ref(false)
const error = ref(null)
const filters = reactive(readFiltersFromRoute())

const hasPrograms = computed(() => programs.value.length > 0)
const currentPage = computed(() => Number(route.query.page || 1))

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function readFiltersFromRoute() {
  return {
    q: normalizeText(route.query.q),
    library_id: normalizeText(route.query.library_id),
    sigungu: normalizeText(route.query.sigungu),
    category: normalizeText(route.query.category),
    target: normalizeText(route.query.target),
    application_status: normalizeText(route.query.application_status),
    operation_status: normalizeText(route.query.operation_status),
  }
}

function syncFiltersFromRoute() {
  Object.assign(filters, readFiltersFromRoute())
}

function buildRequestParams() {
  return {
    ...readPageQuery(route),
    page_size: readPageQuery(route).page_size || DEFAULT_PAGE_SIZE,
    q: route.query.q,
    library_id: route.query.library_id,
    sigungu: route.query.sigungu,
    category: route.query.category,
    target: route.query.target,
    application_status: route.query.application_status,
    operation_status: route.query.operation_status,
  }
}

async function loadPrograms() {
  isLoading.value = true
  error.value = null

  try {
    const data = await fetchPrograms(buildRequestParams())
    programs.value = data.results ?? []
    pagination.value = {
      count: data.count ?? 0,
      next: data.next ?? null,
      previous: data.previous ?? null,
    }
  } catch (requestError) {
    programs.value = []
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

function applyFilters() {
  router.push({
    name: 'program-list',
    query: {
      q: filters.q || undefined,
      library_id: filters.library_id || undefined,
      sigungu: filters.sigungu || undefined,
      category: filters.category || undefined,
      target: filters.target || undefined,
      application_status: filters.application_status || undefined,
      operation_status: filters.operation_status || undefined,
      page: 1,
      page_size: route.query.page_size || DEFAULT_PAGE_SIZE,
    },
  })
}

function clearFilters() {
  router.push({ name: 'program-list' })
}

function goToPage(page) {
  router.push({
    name: 'program-list',
    query: {
      ...route.query,
      page,
    },
  })
}

watch(
  () => route.query,
  () => {
    syncFiltersFromRoute()
    loadPrograms()
  },
)

onMounted(loadPrograms)
</script>

<template>
  <section class="page-shell">
    <div class="mb-4">
      <h1 class="page-title">문화 프로그램</h1>
      <p class="page-subtitle">
        부산 도서관의 문화 프로그램을 현재 공개 API가 지원하는 조건으로 찾아봅니다.
      </p>
    </div>

    <form class="content-panel p-3 mb-4" @submit.prevent="applyFilters">
      <div class="row g-2 align-items-end">
        <div class="col-md-4">
          <label class="form-label" for="program-query">검색어</label>
          <input id="program-query" v-model.trim="filters.q" class="form-control" type="search" />
        </div>
        <div class="col-md-2">
          <label class="form-label" for="program-library-id">도서관 ID</label>
          <input
            id="program-library-id"
            v-model.trim="filters.library_id"
            class="form-control"
            inputmode="numeric"
            type="text"
          />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="program-sigungu">구군</label>
          <input id="program-sigungu" v-model.trim="filters.sigungu" class="form-control" type="text" />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="program-category">분류</label>
          <input id="program-category" v-model.trim="filters.category" class="form-control" type="text" />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="program-target">대상</label>
          <input id="program-target" v-model.trim="filters.target" class="form-control" type="text" />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="program-application-status">신청 상태</label>
          <input
            id="program-application-status"
            v-model.trim="filters.application_status"
            class="form-control"
            type="text"
          />
        </div>
        <div class="col-md-3">
          <label class="form-label" for="program-operation-status">운영 상태</label>
          <input
            id="program-operation-status"
            v-model.trim="filters.operation_status"
            class="form-control"
            type="text"
          />
        </div>
        <div class="col-md-3 d-flex gap-2">
          <button class="btn btn-primary flex-fill" type="submit">검색</button>
          <button class="btn btn-outline-secondary" type="button" @click="clearFilters">초기화</button>
        </div>
      </div>
    </form>

    <LoadingState v-if="isLoading" title="문화 프로그램을 불러오는 중입니다." />
    <ErrorState
      v-else-if="error"
      title="문화 프로그램을 불러오지 못했습니다."
      :message="error.message"
      @retry="loadPrograms"
    />
    <EmptyState
      v-else-if="!hasPrograms"
      title="현재 표시할 문화 프로그램이 없습니다."
      description="프로그램 데이터가 추가되면 이곳에서 확인할 수 있어요."
    />

    <template v-else>
      <p class="meta-text mb-3">총 {{ pagination.count.toLocaleString() }}개</p>
      <div class="row g-3">
        <div v-for="program in programs" :key="program.id" class="col-lg-6">
          <ProgramCard :program="program" />
        </div>
      </div>
      <div class="d-flex justify-content-center gap-2 mt-4">
        <button
          class="btn btn-outline-secondary"
          type="button"
          :disabled="!pagination.previous"
          @click="goToPage(currentPage - 1)"
        >
          이전
        </button>
        <span class="meta-text align-self-center">{{ currentPage }}페이지</span>
        <button
          class="btn btn-outline-secondary"
          type="button"
          :disabled="!pagination.next"
          @click="goToPage(currentPage + 1)"
        >
          다음
        </button>
      </div>
    </template>
  </section>
</template>
