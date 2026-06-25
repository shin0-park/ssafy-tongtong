<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import LibraryCard from '@/components/cards/LibraryCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import ResultCount from '@/components/navigation/ResultCount.vue'
import { fetchLibraries } from '@/services/libraryService'
import { readPageQuery, readStringQuery } from '@/utils/query'

const route = useRoute()
const router = useRouter()

const libraries = ref([])
const pagination = ref({ count: 0, next: null, previous: null })
const isLoading = ref(false)
const error = ref(null)
const filters = reactive({
  q: '',
  sigungu: '',
  library_type: '',
  purpose: '',
  lat: '',
  lng: '',
  min_book_count: '',
  min_reading_seat_count: '',
  ordering: '',
  open_today: false,
  open_now: false,
  weekend_open: false,
  holiday_status: '',
  holiday_date: '',
  facilities: [],
})

const hasLibraries = computed(() => libraries.value.length > 0)
const pageQuery = computed(() => readPageQuery(route))
const page = computed(() => pageQuery.value.page)
const pageSize = computed(() => pageQuery.value.page_size || 12)
const nearbyNeedsLocation = computed(
  () => filters.purpose === 'nearby' && (!filters.lat || !filters.lng),
)

const facilityOptions = [
  { value: 'has_reading_room', label: '열람실' },
  { value: 'has_children_room', label: '어린이실' },
  { value: 'has_digital_room', label: '디지털 자료실' },
  { value: 'has_parking', label: '주차장' },
  { value: 'has_cafe', label: '카페' },
  { value: 'has_wifi', label: '와이파이' },
  { value: 'has_nursing_room', label: '수유실' },
  { value: 'has_accessible_facility', label: '장애인 편의시설' },
  { value: 'has_elevator', label: '엘리베이터' },
  { value: 'has_lounge', label: '휴게 공간' },
  { value: 'has_outdoor_space', label: '야외 공간' },
]

function syncFromRoute() {
  filters.q = readStringQuery(route, 'q')
  filters.sigungu = readStringQuery(route, 'sigungu')
  filters.library_type = readStringQuery(route, 'library_type')
  filters.purpose = readStringQuery(route, 'purpose')
  filters.lat = readStringQuery(route, 'lat')
  filters.lng = readStringQuery(route, 'lng')
  filters.min_book_count = readStringQuery(route, 'min_book_count')
  filters.min_reading_seat_count = readStringQuery(route, 'min_reading_seat_count')
  filters.ordering = readStringQuery(route, 'ordering')
  filters.holiday_status = readStringQuery(route, 'holiday_status')
  filters.holiday_date = readStringQuery(route, 'holiday_date')
  filters.open_today = route.query.open_today === 'true'
  filters.open_now = route.query.open_now === 'true'
  filters.weekend_open = route.query.weekend_open === 'true'
  filters.facilities = facilityOptions
    .map((item) => item.value)
    .filter((key) => route.query[key] === 'true')
}

function buildRequestParams() {
  const facilityParams = Object.fromEntries(filters.facilities.map((key) => [key, true]))
  const purpose = nearbyNeedsLocation.value ? '' : filters.purpose

  return {
    q: filters.q,
    sigungu: filters.sigungu,
    library_type: filters.library_type,
    purpose,
    lat: filters.lat,
    lng: filters.lng,
    min_book_count: filters.min_book_count,
    min_reading_seat_count: filters.min_reading_seat_count,
    ordering: filters.ordering,
    open_today: filters.open_today ? true : undefined,
    open_now: filters.open_now ? true : undefined,
    weekend_open: filters.weekend_open ? true : undefined,
    holiday_status: filters.holiday_status,
    holiday_date: filters.holiday_date,
    page: page.value,
    page_size: pageSize.value,
    ...facilityParams,
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
  const facilityQuery = Object.fromEntries(filters.facilities.map((key) => [key, 'true']))
  const purpose = nearbyNeedsLocation.value ? '' : filters.purpose

  router.push({
    name: 'library-list',
    query: {
      q: filters.q || undefined,
      sigungu: filters.sigungu || undefined,
      library_type: filters.library_type || undefined,
      purpose: purpose || undefined,
      lat: filters.lat || undefined,
      lng: filters.lng || undefined,
      min_book_count: filters.min_book_count || undefined,
      min_reading_seat_count: filters.min_reading_seat_count || undefined,
      ordering: filters.ordering || undefined,
      open_today: filters.open_today ? 'true' : undefined,
      open_now: filters.open_now ? 'true' : undefined,
      weekend_open: filters.weekend_open ? 'true' : undefined,
      holiday_status: filters.holiday_status || undefined,
      holiday_date: filters.holiday_date || undefined,
      ...facilityQuery,
      page: 1,
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
    syncFromRoute()
    loadLibraries()
  },
)

onMounted(() => {
  syncFromRoute()
  loadLibraries()
})
</script>

<template>
  <section class="page-shell">
    <div class="page-header">
      <h1 class="page-title">도서관 찾기</h1>
      <p class="page-subtitle">검색어, 지역, 시설과 운영 조건으로 부산 도서관을 찾아봅니다.</p>
    </div>

    <form class="content-panel p-4 mb-4" @submit.prevent="applyFilters">
      <div class="filter-grid mb-3">
        <label class="form-field">
          <span>검색어</span>
          <input v-model.trim="filters.q" class="form-control" type="search" />
        </label>
        <label class="form-field">
          <span>구군</span>
          <input v-model.trim="filters.sigungu" class="form-control" type="text" placeholder="해운대구, 수영구" />
        </label>
        <label class="form-field">
          <span>유형</span>
          <input
            v-model.trim="filters.library_type"
            class="form-control"
            type="text"
            placeholder="공공도서관, 작은도서관"
          />
        </label>
        <label class="form-field">
          <span>목적</span>
          <input v-model.trim="filters.purpose" class="form-control" type="text" />
        </label>
        <label class="form-field">
          <span>위도</span>
          <input v-model.trim="filters.lat" class="form-control" inputmode="decimal" />
        </label>
        <label class="form-field">
          <span>경도</span>
          <input v-model.trim="filters.lng" class="form-control" inputmode="decimal" />
        </label>
        <label class="form-field">
          <span>최소 장서 수</span>
          <input v-model.trim="filters.min_book_count" class="form-control" type="number" min="0" />
        </label>
        <label class="form-field">
          <span>최소 열람석</span>
          <input v-model.trim="filters.min_reading_seat_count" class="form-control" type="number" min="0" />
        </label>
        <label class="form-field">
          <span>공휴일 상태</span>
          <input v-model.trim="filters.holiday_status" class="form-control" type="text" />
        </label>
        <label class="form-field">
          <span>공휴일 기준일</span>
          <input v-model.trim="filters.holiday_date" class="form-control" type="date" />
        </label>
        <label class="form-field">
          <span>정렬</span>
          <input v-model.trim="filters.ordering" class="form-control" type="text" />
        </label>
      </div>

      <div class="d-flex flex-wrap gap-3 mb-3">
        <label class="form-check">
          <input v-model="filters.open_today" class="form-check-input" type="checkbox" />
          <span class="form-check-label">오늘 운영</span>
        </label>
        <label class="form-check">
          <input v-model="filters.open_now" class="form-check-input" type="checkbox" />
          <span class="form-check-label">지금 운영</span>
        </label>
        <label class="form-check">
          <input v-model="filters.weekend_open" class="form-check-input" type="checkbox" />
          <span class="form-check-label">주말 운영</span>
        </label>
      </div>

      <p v-if="nearbyNeedsLocation" class="alert alert-info py-2 mb-3">
        가까운 도서관 목적은 위도와 경도가 있을 때만 적용됩니다. 좌표가 없으면 일반 도서관 검색으로 조회합니다.
      </p>

      <fieldset class="preference-fieldset mb-3">
        <legend>확인된 시설</legend>
        <label v-for="facility in facilityOptions" :key="facility.value" class="preference-option">
          <input v-model="filters.facilities" class="form-check-input" type="checkbox" :value="facility.value" />
          <span>{{ facility.label }}</span>
        </label>
      </fieldset>

      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" type="button" @click="router.push({ name: 'library-list' })">
          초기화
        </button>
        <button class="btn btn-primary" type="submit">검색</button>
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
      <ResultCount :count="pagination.count" label="곳" />
      <div class="responsive-card-grid">
        <LibraryCard v-for="library in libraries" :key="library.id" :library="library" />
      </div>
      <PaginationBar
        :current-page="page"
        :has-previous="Boolean(pagination.previous)"
        :has-next="Boolean(pagination.next)"
        @change="goToPage"
      />
    </template>
  </section>
</template>
