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
import { FACILITY_LABELS, PURPOSE_LABELS } from '@/utils/display'
import { readPageQuery, readStringQuery } from '@/utils/query'

const route = useRoute()
const router = useRouter()

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
const LIBRARY_TYPE_OPTIONS = [
  { value: 'public', label: '공공도서관' },
  { value: 'small', label: '작은도서관' },
  { value: 'children', label: '어린이도서관' },
]
const PURPOSE_OPTIONS = Object.entries(PURPOSE_LABELS).map(([value, label]) => ({ value, label }))
const FACILITY_OPTIONS = Object.entries(FACILITY_LABELS).map(([value, label]) => ({ value, label }))
const ORDERING_OPTIONS = [
  { value: '', label: '추천순' },
  { value: 'name', label: '이름순' },
  { value: '-book_count', label: '장서 많은 순' },
  { value: '-reading_seat_count', label: '좌석 많은 순' },
  { value: 'purpose_score', label: '테마 적합순' },
]

const libraries = ref([])
const pagination = ref({ count: 0, next: null, previous: null })
const isLoading = ref(false)
const error = ref(null)
const locationMessage = ref('')
const filters = reactive({
  q: '',
  sigungu: [],
  library_type: [],
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
  facilities: [],
})

const hasLibraries = computed(() => libraries.value.length > 0)
const pageQuery = computed(() => readPageQuery(route))
const page = computed(() => pageQuery.value.page)
const pageSize = computed(() => pageQuery.value.page_size || 12)
const needsLocation = computed(() => filters.purpose === 'nearby' && (!filters.lat || !filters.lng))
const hasFilter = computed(() =>
  Boolean(
    filters.q ||
      filters.sigungu.length ||
      filters.library_type.length ||
      filters.purpose ||
      filters.min_book_count ||
      filters.min_reading_seat_count ||
      filters.open_today ||
      filters.open_now ||
      filters.weekend_open ||
      filters.holiday_status ||
      filters.facilities.length,
  ),
)

function readMultiQuery(name) {
  const raw = route.query[name]
  if (Array.isArray(raw)) return raw.flatMap((item) => String(item).split(',')).filter(Boolean)
  if (typeof raw === 'string') return raw.split(',').map((item) => item.trim()).filter(Boolean)
  return []
}

function syncFromRoute() {
  filters.q = readStringQuery(route, 'q')
  filters.sigungu = readMultiQuery('sigungu')
  filters.library_type = readMultiQuery('library_type')
  filters.purpose = readStringQuery(route, 'purpose')
  filters.lat = readStringQuery(route, 'lat')
  filters.lng = readStringQuery(route, 'lng')
  filters.min_book_count = readStringQuery(route, 'min_book_count')
  filters.min_reading_seat_count = readStringQuery(route, 'min_reading_seat_count')
  filters.ordering = readStringQuery(route, 'ordering')
  filters.holiday_status = readStringQuery(route, 'holiday_status')
  filters.open_today = route.query.open_today === 'true'
  filters.open_now = route.query.open_now === 'true'
  filters.weekend_open = route.query.weekend_open === 'true'
  filters.facilities = FACILITY_OPTIONS.map((item) => item.value).filter((key) => route.query[key] === 'true')
}

function buildRequestParams() {
  const facilityParams = Object.fromEntries(filters.facilities.map((key) => [key, true]))
  const purpose = needsLocation.value ? '' : filters.purpose
  const ordering = filters.ordering === 'purpose_score' && !purpose ? '' : filters.ordering

  return {
    q: filters.q,
    sigungu: filters.sigungu.join(','),
    library_type: filters.library_type.join(','),
    purpose,
    lat: filters.lat,
    lng: filters.lng,
    min_book_count: filters.min_book_count,
    min_reading_seat_count: filters.min_reading_seat_count,
    ordering,
    open_today: filters.open_today ? true : undefined,
    open_now: filters.open_now ? true : undefined,
    weekend_open: filters.weekend_open ? true : undefined,
    holiday_status: filters.holiday_status,
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
  const purpose = needsLocation.value ? '' : filters.purpose
  const ordering = filters.ordering === 'purpose_score' && !purpose ? '' : filters.ordering

  router.push({
    name: 'library-list',
    query: {
      q: filters.q || undefined,
      sigungu: filters.sigungu.length ? filters.sigungu.join(',') : undefined,
      library_type: filters.library_type.length ? filters.library_type.join(',') : undefined,
      purpose: purpose || undefined,
      lat: filters.lat || undefined,
      lng: filters.lng || undefined,
      min_book_count: filters.min_book_count || undefined,
      min_reading_seat_count: filters.min_reading_seat_count || undefined,
      ordering: ordering || undefined,
      open_today: filters.open_today ? 'true' : undefined,
      open_now: filters.open_now ? 'true' : undefined,
      weekend_open: filters.weekend_open ? 'true' : undefined,
      holiday_status: filters.holiday_status || undefined,
      ...facilityQuery,
      page: 1,
    },
  })
}

function resetFilters() {
  locationMessage.value = ''
  router.push({ name: 'library-list' })
}

function requestNearby() {
  locationMessage.value = ''
  filters.purpose = 'nearby'

  if (!navigator.geolocation) {
    locationMessage.value = '현재 브라우저에서 위치 정보를 사용할 수 없습니다.'
    return
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      filters.lat = position.coords.latitude.toFixed(7)
      filters.lng = position.coords.longitude.toFixed(7)
      applyFilters()
    },
    () => {
      locationMessage.value = '위치 권한을 사용할 수 없어 가까운 곳 필터를 적용하지 않았습니다.'
      filters.purpose = ''
    },
    { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 },
  )
}

function goToPage(nextPage) {
  router.push({
    name: 'library-list',
    query: {
      ...route.query,
      page: nextPage,
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
    <div class="page-hero">
      <h1>도서관 찾기</h1>
      <p>지역, 테마, 운영 조건, 시설 정보를 조합해 오늘 가기 좋은 부산 도서관을 찾아보세요.</p>
      <div class="page-hero-visual" aria-hidden="true">⌕</div>
    </div>

    <form class="content-panel p-4 mb-4 filter-panel" @submit.prevent="applyFilters">
      <div class="filter-grid">
        <label class="form-field">
          <span>검색</span>
          <input
            v-model.trim="filters.q"
            class="form-control"
            type="search"
            placeholder="도서관명, 지역, 키워드 검색"
          />
        </label>
        <label class="form-field">
          <span>정렬</span>
          <select v-model="filters.ordering" class="form-select">
            <option v-for="option in ORDERING_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label class="form-field">
          <span>최소 자료 수</span>
          <input v-model.trim="filters.min_book_count" class="form-control" type="number" min="0" />
        </label>
        <label class="form-field">
          <span>최소 열람좌석 수</span>
          <input v-model.trim="filters.min_reading_seat_count" class="form-control" type="number" min="0" />
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
        <p class="filter-group-title">도서관 유형</p>
        <div class="filter-chip-grid">
          <label v-for="type in LIBRARY_TYPE_OPTIONS" :key="type.value" class="filter-chip">
            <input v-model="filters.library_type" type="checkbox" :value="type.value" />
            <span>{{ type.label }}</span>
          </label>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">테마</p>
        <div class="filter-chip-grid">
          <label v-for="purpose in PURPOSE_OPTIONS" :key="purpose.value" class="filter-chip">
            <input v-model="filters.purpose" type="radio" :value="purpose.value" />
            <span>{{ purpose.label }}</span>
          </label>
          <button class="btn btn-outline-primary btn-sm" type="button" @click="requestNearby">
            가까운 곳 위치 적용
          </button>
        </div>
        <p v-if="locationMessage" class="meta-text mb-0">{{ locationMessage }}</p>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">운영 조건</p>
        <div class="filter-chip-grid">
          <label class="filter-chip">
            <input v-model="filters.open_today" type="checkbox" />
            <span>오늘 운영</span>
          </label>
          <label class="filter-chip">
            <input v-model="filters.open_now" type="checkbox" />
            <span>지금 운영</span>
          </label>
          <label class="filter-chip">
            <input v-model="filters.weekend_open" type="checkbox" />
            <span>주말 운영</span>
          </label>
          <label class="filter-chip">
            <input v-model="filters.holiday_status" type="radio" value="open" />
            <span>공휴일 운영</span>
          </label>
          <label class="filter-chip">
            <input v-model="filters.holiday_status" type="radio" value="closed" />
            <span>공휴일 휴관</span>
          </label>
        </div>
        <p class="meta-text mb-0">“늦게까지 운영”은 별도 query 없이 현재 운영 및 오늘 운영시간 표시로 안내합니다.</p>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">시설/공간</p>
        <div class="filter-chip-grid">
          <label v-for="facility in FACILITY_OPTIONS" :key="facility.value" class="filter-chip">
            <input v-model="filters.facilities" type="checkbox" :value="facility.value" />
            <span>{{ facility.label }}</span>
          </label>
        </div>
      </div>

      <div class="d-flex flex-wrap justify-content-end gap-2">
        <button class="btn btn-outline-secondary" type="button" @click="resetFilters">필터 초기화</button>
        <button class="btn btn-primary" type="submit">검색하기</button>
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
      description="검색어나 필터를 조정해보세요."
    />

    <template v-else>
      <div class="section-header-row">
        <ResultCount :count="pagination.count" label="곳" />
        <p class="meta-text mb-0">{{ hasFilter ? '검색/필터 결과입니다.' : '전체 도서관 목록입니다.' }}</p>
      </div>
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
