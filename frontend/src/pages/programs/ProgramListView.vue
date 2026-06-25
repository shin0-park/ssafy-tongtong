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
import { readPageQuery } from '@/utils/query'

const route = useRoute()
const router = useRouter()

const DEFAULT_PAGE_SIZE = 12
const SIGUNGU_OPTIONS = ['강서구', '금정구', '남구', '동래구', '부산진구', '북구', '사상구', '수영구', '연제구', '해운대구']
const CATEGORY_OPTIONS = [
  { value: 'lecture', label: '강연/인문학' },
  { value: 'reading', label: '독서/글쓰기' },
  { value: 'art', label: '문화/예술' },
  { value: 'education', label: '체험/교육' },
  { value: 'exhibition', label: '전시' },
  { value: 'etc', label: '기타' },
]
const TARGET_OPTIONS = [
  { value: 'infant', label: '유아' },
  { value: 'child', label: '초등' },
  { value: 'teen', label: '청소년' },
  { value: 'adult', label: '성인' },
  { value: 'senior', label: '시니어' },
  { value: 'family', label: '가족/기타' },
]
const APPLICATION_OPTIONS = [
  { value: 'available', label: APPLICATION_STATUS_LABELS.available },
  { value: 'open', label: APPLICATION_STATUS_LABELS.open },
  { value: 'closed', label: APPLICATION_STATUS_LABELS.closed },
  { value: 'scheduled', label: APPLICATION_STATUS_LABELS.scheduled },
  { value: 'none', label: APPLICATION_STATUS_LABELS.none },
]
const OPERATION_OPTIONS = [
  { value: 'upcoming', label: OPERATION_STATUS_LABELS.upcoming },
  { value: 'scheduled', label: OPERATION_STATUS_LABELS.scheduled },
  { value: 'ongoing', label: OPERATION_STATUS_LABELS.ongoing },
  { value: 'ended', label: OPERATION_STATUS_LABELS.ended },
]

const programs = ref([])
const pagination = ref({ count: 0, next: null, previous: null })
const isLoading = ref(false)
const error = ref(null)
const filters = reactive(readFiltersFromRoute())

const hasPrograms = computed(() => programs.value.length > 0)
const currentPage = computed(() => readPageQuery(route).page)

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function splitQuery(value) {
  if (!value) return []
  if (Array.isArray(value)) return value.flatMap((item) => String(item).split(',')).filter(Boolean)
  return String(value)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function readFiltersFromRoute() {
  return {
    q: normalizeText(route.query.q),
    library_id: normalizeText(route.query.library_id),
    sigungu: splitQuery(route.query.sigungu),
    category: splitQuery(route.query.category),
    target: splitQuery(route.query.target),
    application_status: splitQuery(route.query.application_status),
    operation_status: splitQuery(route.query.operation_status),
  }
}

function syncFiltersFromRoute() {
  Object.assign(filters, readFiltersFromRoute())
}

function buildRequestParams() {
  return {
    ...readPageQuery(route),
    page_size: readPageQuery(route).page_size || DEFAULT_PAGE_SIZE,
    q: filters.q,
    library_id: filters.library_id,
    sigungu: filters.sigungu.join(','),
    category: filters.category.join(','),
    target: filters.target.join(','),
    application_status: filters.application_status.join(','),
    operation_status: filters.operation_status.join(','),
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
      application_status: filters.application_status.length ? filters.application_status.join(',') : undefined,
      operation_status: filters.operation_status.length ? filters.operation_status.join(',') : undefined,
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
    <div class="page-hero page-hero-banner page-hero-programs">
      <h1>문화 프로그램</h1>
      <p>도서관에서 열리는 강연, 독서, 전시, 체험 프로그램을 검색하고 해당 도서관으로 이동해보세요.</p>
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
          <label v-for="sigungu in SIGUNGU_OPTIONS" :key="sigungu" class="filter-chip">
            <input v-model="filters.sigungu" type="checkbox" :value="sigungu" />
            <span>{{ sigungu }}</span>
          </label>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">프로그램 유형</p>
        <div class="filter-chip-grid">
          <label v-for="category in CATEGORY_OPTIONS" :key="category.value" class="filter-chip">
            <input v-model="filters.category" type="checkbox" :value="category.value" />
            <span>{{ category.label || PROGRAM_CATEGORY_LABELS[category.value] }}</span>
          </label>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">대상</p>
        <div class="filter-chip-grid">
          <label v-for="target in TARGET_OPTIONS" :key="target.value" class="filter-chip">
            <input v-model="filters.target" type="checkbox" :value="target.value" />
            <span>{{ target.label || PROGRAM_TARGET_LABELS[target.value] }}</span>
          </label>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">신청 상태</p>
        <div class="filter-chip-grid">
          <label v-for="status in APPLICATION_OPTIONS" :key="status.value" class="filter-chip">
            <input v-model="filters.application_status" type="checkbox" :value="status.value" />
            <span>{{ status.label }}</span>
          </label>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">운영 상태</p>
        <div class="filter-chip-grid">
          <label v-for="status in OPERATION_OPTIONS" :key="status.value" class="filter-chip">
            <input v-model="filters.operation_status" type="checkbox" :value="status.value" />
            <span>{{ status.label }}</span>
          </label>
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
      description="프로그램 데이터가 추가되면 이곳에서 확인할 수 있어요."
    />

    <template v-else>
      <ResultCount class="mb-3" :count="pagination.count" label="개" />
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
