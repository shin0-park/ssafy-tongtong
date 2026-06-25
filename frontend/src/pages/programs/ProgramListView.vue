<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ProgramCard from '@/components/cards/ProgramCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import ResultCount from '@/components/navigation/ResultCount.vue'
import { fetchPrograms } from '@/services/programService'
import {
  APPLICATION_STATUS_LABELS,
  OPERATION_STATUS_LABELS,
  PROGRAM_CATEGORY_LABELS,
  PROGRAM_TARGET_LABELS,
} from '@/utils/display'
import { normalizeOrdering, readPageQuery } from '@/utils/query'

const route = useRoute()
const router = useRouter()

const DEFAULT_PAGE_SIZE = 12
const MAX_SIGUNGU_SELECTIONS = 3
const SIGUNGU_OPTIONS = [
  '강서구',
  '금정구',
  '기장군',
  '남구',
  '동구',
  '동래구',
  '부산진구',
  '북구',
  '사상구',
  '사하구',
  '서구',
  '수영구',
  '연제구',
  '영도구',
  '중구',
  '해운대구',
]
const CATEGORY_OPTIONS = Object.entries(PROGRAM_CATEGORY_LABELS).map(([value, label]) => ({ value, label }))
const TARGET_OPTIONS = Object.entries(PROGRAM_TARGET_LABELS)
  .filter(([value]) => value !== 'all')
  .map(([value, label]) => ({ value, label }))
const APPLICATION_OPTIONS = Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => ({ value, label }))
const OPERATION_OPTIONS = Object.entries(OPERATION_STATUS_LABELS).map(([value, label]) => ({ value, label }))
const ORDERING_OPTIONS = [
  { value: '-post_date', label: '게시 최신순' },
  { value: 'title', label: '프로그램명순' },
  { value: 'library__name', label: '도서관명순' },
]
const DEFAULT_ORDERING = '-post_date'

const programs = ref([])
const pagination = ref({ count: 0, next: null, previous: null })
const isLoading = ref(false)
const error = ref(null)

const hasPrograms = computed(() => programs.value.length > 0)
const currentPage = computed(() => readPageQuery(route).page)
const allowedValues = {
  sigungu: SIGUNGU_OPTIONS,
  category: CATEGORY_OPTIONS.map((item) => item.value),
  target: TARGET_OPTIONS.map((item) => item.value),
  application_status: APPLICATION_OPTIONS.map((item) => item.value),
  operation_status: OPERATION_OPTIONS.map((item) => item.value),
  ordering: ORDERING_OPTIONS.map((item) => item.value),
}
const filters = reactive(readFiltersFromRoute())

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function splitQuery(value, allowed = null) {
  if (!value) return []
  const values = Array.isArray(value)
    ? value.flatMap((item) => String(item).split(','))
    : String(value).split(',')
  const normalized = values.map((item) => item.trim()).filter(Boolean)
  return allowed ? normalized.filter((item) => allowed.includes(item)) : normalized
}

function readSingleQueryValue(value, allowed) {
  return splitQuery(value, allowed)[0] ?? ''
}

function createEmptyFilters() {
  return {
    q: '',
    library_id: '',
    sigungu: [],
    category: [],
    target: [],
    application_status: '',
    operation_status: '',
    ordering: DEFAULT_ORDERING,
  }
}

function readFiltersFromRoute() {
  return {
    q: normalizeText(route.query.q),
    library_id: normalizeText(route.query.library_id),
    sigungu: splitQuery(route.query.sigungu, allowedValues?.sigungu ?? SIGUNGU_OPTIONS).slice(0, MAX_SIGUNGU_SELECTIONS),
    category: splitQuery(route.query.category, allowedValues?.category ?? CATEGORY_OPTIONS.map((item) => item.value)),
    target: splitQuery(route.query.target, allowedValues?.target ?? TARGET_OPTIONS.map((item) => item.value)),
    application_status: readSingleQueryValue(
      route.query.application_status,
      allowedValues?.application_status ?? APPLICATION_OPTIONS.map((item) => item.value),
    ),
    operation_status: readSingleQueryValue(
      route.query.operation_status,
      allowedValues?.operation_status ?? OPERATION_OPTIONS.map((item) => item.value),
    ),
    ordering: normalizeOrdering(
      route.query.ordering,
      allowedValues?.ordering ?? ORDERING_OPTIONS.map((item) => item.value),
      DEFAULT_ORDERING,
    ),
  }
}

function syncFiltersFromRoute() {
  Object.assign(filters, readFiltersFromRoute())
}

function buildRequestParams() {
  const pageQuery = readPageQuery(route)
  return {
    ...pageQuery,
    page_size: pageQuery.page_size || DEFAULT_PAGE_SIZE,
    q: filters.q,
    library_id: filters.library_id,
    sigungu: filters.sigungu.join(','),
    category: filters.category.join(','),
    target: filters.target.join(','),
    application_status: filters.application_status,
    operation_status: filters.operation_status,
    ordering: filters.ordering,
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
      sigungu: filters.sigungu.length ? filters.sigungu.join(',') : undefined,
      category: filters.category.length ? filters.category.join(',') : undefined,
      target: filters.target.length ? filters.target.join(',') : undefined,
      application_status: filters.application_status || undefined,
      operation_status: filters.operation_status || undefined,
      ordering: filters.ordering === DEFAULT_ORDERING ? undefined : filters.ordering,
      page: 1,
      page_size: readPageQuery(route).page_size || DEFAULT_PAGE_SIZE,
    },
  })
}

function applySort() {
  router.push({
    name: 'program-list',
    query: {
      ...route.query,
      ordering: filters.ordering === DEFAULT_ORDERING ? undefined : filters.ordering,
      page: 1,
    },
  })
}

function clearFilters() {
  Object.assign(filters, createEmptyFilters())
  router.push({ name: 'program-list' })
}

function toggleSingleFilter(field, value) {
  filters[field] = filters[field] === value ? '' : value
}

function toggleMultiFilter(field, value, maxSelections = Infinity) {
  const selectedValues = filters[field]
  const selectedIndex = selectedValues.indexOf(value)

  if (selectedIndex >= 0) {
    selectedValues.splice(selectedIndex, 1)
    return
  }

  if (selectedValues.length >= maxSelections) {
    return
  }

  selectedValues.push(value)
}

function isSigunguSelectionDisabled(sigungu) {
  return !filters.sigungu.includes(sigungu) && filters.sigungu.length >= MAX_SIGUNGU_SELECTIONS
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
    <div class="page-hero page-hero-banner page-hero-programs">
      <h1>문화 프로그램</h1>
      <p>도서관에서 열리는 강연, 독서, 전시, 체험 프로그램을 검색하고 해당 도서관으로 이동해 보세요.</p>
    </div>

    <form class="content-panel p-4 mb-4 filter-panel" @submit.prevent="applyFilters">
      <div class="filter-grid">
        <label class="form-field">
          <span>프로그램명 또는 도서관명</span>
          <input v-model.trim="filters.q" class="form-control" type="search" placeholder="검색어 입력" />
        </label>
        <label class="form-field">
          <span>도서관 ID</span>
          <input v-model.trim="filters.library_id" class="form-control" inputmode="numeric" type="text" />
        </label>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">지역</p>
        <div class="filter-chip-grid">
          <button
            v-for="sigungu in SIGUNGU_OPTIONS"
            :key="sigungu"
            class="filter-chip"
            :class="{ active: filters.sigungu.includes(sigungu) }"
            type="button"
            :aria-pressed="filters.sigungu.includes(sigungu)"
            :disabled="isSigunguSelectionDisabled(sigungu)"
            @click="toggleMultiFilter('sigungu', sigungu, MAX_SIGUNGU_SELECTIONS)"
          >
            <span>{{ sigungu }}</span>
          </button>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">프로그램 유형</p>
        <div class="filter-chip-grid">
          <button
            v-for="category in CATEGORY_OPTIONS"
            :key="category.value"
            class="filter-chip"
            :class="{ active: filters.category.includes(category.value) }"
            type="button"
            :aria-pressed="filters.category.includes(category.value)"
            @click="toggleMultiFilter('category', category.value)"
          >
            <span>{{ category.label }}</span>
          </button>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">대상</p>
        <div class="filter-chip-grid">
          <label v-for="target in TARGET_OPTIONS" :key="target.value" class="filter-chip">
            <input v-model="filters.target" type="checkbox" :value="target.value" />
            <span>{{ target.label }}</span>
          </label>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">신청 상태</p>
        <div class="filter-chip-grid">
          <button
            v-for="status in APPLICATION_OPTIONS"
            :key="status.value"
            class="filter-chip"
            :class="{ active: filters.application_status === status.value }"
            type="button"
            :aria-pressed="filters.application_status === status.value"
            @click="toggleSingleFilter('application_status', status.value)"
          >
            <span>{{ status.label }}</span>
          </button>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">운영 상태</p>
        <div class="filter-chip-grid">
          <button
            v-for="status in OPERATION_OPTIONS"
            :key="status.value"
            class="filter-chip"
            :class="{ active: filters.operation_status === status.value }"
            type="button"
            :aria-pressed="filters.operation_status === status.value"
            @click="toggleSingleFilter('operation_status', status.value)"
          >
            <span>{{ status.label }}</span>
          </button>
        </div>
      </div>

      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" type="button" @click="clearFilters">초기화</button>
        <button class="btn btn-primary" type="submit">검색</button>
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
      description="검색어나 필터를 조정해 보세요."
    />

    <template v-else>
      <div class="result-toolbar mb-3">
        <ResultCount :count="pagination.count" label="개" />
        <div class="result-sort-controls" aria-label="문화 프로그램 목록 정렬">
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
      <div class="program-result-grid">
        <ProgramCard v-for="program in programs" :key="program.id" :program="program" />
      </div>
      <PaginationBar
        :current-page="currentPage"
        :has-previous="Boolean(pagination.previous)"
        :has-next="Boolean(pagination.next)"
        @change="goToPage"
      />
    </template>
  </section>
</template>
