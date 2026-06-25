<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import LibraryCard from '@/components/cards/LibraryCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import LocationPermissionPanel from '@/components/location/LocationPermissionPanel.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import ResultCount from '@/components/navigation/ResultCount.vue'
import { fetchLibraries } from '@/services/libraryService'
import { FACILITY_LABELS, PURPOSE_LABELS } from '@/utils/display'
import { readStoredLocation, storeLocation } from '@/utils/locationPreference'
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
  { value: 'name', label: '이름순' },
  { value: '-book_count', label: '장서 많은 순' },
  { value: '-reading_seat_count', label: '좌석 많은 순' },
  { value: 'purpose_score', label: '테마 적합순' },
]
const HOLIDAY_STATUS_OPTIONS = [
  { value: 'open', label: '공휴일 운영' },
  { value: 'closed', label: '공휴일 휴관' },
]

const libraries = ref([])
const pagination = ref({ count: 0, next: null, previous: null })
const isLoading = ref(false)
const error = ref(null)
const locationMessage = ref('')
const sigunguMessage = ref('')
const currentLocation = ref(readStoredLocation())
const showLocationPanel = ref(false)
const isLocationLoading = ref(false)
const filters = reactive({
  q: '',
  sigungu: [],
  library_type: '',
  purpose: '',
  lat: '',
  lng: '',
  min_book_count: '',
  min_reading_seat_count: '',
  ordering: 'name',
  open_today: false,
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
      filters.library_type ||
      filters.purpose ||
      filters.min_book_count ||
      filters.min_reading_seat_count ||
      filters.open_today ||
      filters.weekend_open ||
      filters.holiday_status ||
      filters.facilities.length,
  ),
)

function readMultiQuery(name, allowedValues = null) {
  const raw = route.query[name]
  const values = Array.isArray(raw)
    ? raw.flatMap((item) => String(item).split(','))
    : typeof raw === 'string'
      ? raw.split(',')
      : []
  const normalized = values.map((item) => item.trim()).filter(Boolean)
  return allowedValues ? normalized.filter((value) => allowedValues.includes(value)) : normalized
}

function readSingleQueryValue(name, allowedValues) {
  return readMultiQuery(name, allowedValues)[0] ?? ''
}

function syncFromRoute() {
  filters.q = readStringQuery(route, 'q')
  filters.sigungu = readMultiQuery('sigungu', SIGUNGU_OPTIONS).slice(0, 3)
  sigunguMessage.value = ''
  filters.library_type = readSingleQueryValue(
    'library_type',
    LIBRARY_TYPE_OPTIONS.map((item) => item.value),
  )
  filters.purpose = PURPOSE_LABELS[route.query.purpose] ? readStringQuery(route, 'purpose') : ''
  filters.lat = readStringQuery(route, 'lat')
  filters.lng = readStringQuery(route, 'lng')
  filters.min_book_count = readStringQuery(route, 'min_book_count')
  filters.min_reading_seat_count = readStringQuery(route, 'min_reading_seat_count')
  const routeOrdering = ORDERING_OPTIONS.some((item) => item.value === route.query.ordering)
    ? readStringQuery(route, 'ordering')
    : 'name'
  filters.ordering = routeOrdering === 'purpose_score' && !filters.purpose ? 'name' : routeOrdering
  filters.holiday_status = HOLIDAY_STATUS_OPTIONS.some((item) => item.value === route.query.holiday_status)
    ? readStringQuery(route, 'holiday_status')
    : ''
  filters.open_today = route.query.open_today === 'true'
  filters.weekend_open = route.query.weekend_open === 'true'
  filters.facilities = FACILITY_OPTIONS.map((item) => item.value).filter((key) => route.query[key] === 'true')
  if (filters.lat && filters.lng) {
    currentLocation.value = { lat: filters.lat, lng: filters.lng }
  } else if (filters.purpose === 'nearby' && currentLocation.value) {
    filters.lat = currentLocation.value.lat
    filters.lng = currentLocation.value.lng
  }
  showLocationPanel.value = filters.purpose === 'nearby' && !filters.lat && !filters.lng
}

function buildRequestParams() {
  const facilityParams = Object.fromEntries(filters.facilities.map((key) => [key, true]))
  const purpose = needsLocation.value ? '' : filters.purpose
  const ordering = filters.ordering === 'purpose_score' && !purpose ? '' : filters.ordering

  return {
    q: filters.q,
    sigungu: filters.sigungu,
    library_type: filters.library_type,
    purpose,
    lat: purpose ? filters.lat : '',
    lng: purpose ? filters.lng : '',
    min_book_count: filters.min_book_count,
    min_reading_seat_count: filters.min_reading_seat_count,
    ordering,
    open_today: filters.open_today ? true : undefined,
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
    libraries.value = []
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

function applyFilters() {
  if (needsLocation.value) {
    locationMessage.value = '가까운 도서관을 보려면 현재 위치를 먼저 적용해 주세요.'
    showLocationPanel.value = true
    return
  }

  const facilityQuery = Object.fromEntries(filters.facilities.map((key) => [key, 'true']))
  const purpose = filters.purpose
  const ordering = filters.ordering === 'purpose_score' && !purpose ? '' : filters.ordering

  router.push({
    name: 'library-list',
    query: {
      q: filters.q || undefined,
      sigungu: filters.sigungu.length ? filters.sigungu.join(',') : undefined,
      library_type: filters.library_type || undefined,
      purpose: purpose || undefined,
      lat: purpose ? filters.lat || undefined : undefined,
      lng: purpose ? filters.lng || undefined : undefined,
      min_book_count: filters.min_book_count || undefined,
      min_reading_seat_count: filters.min_reading_seat_count || undefined,
      ordering: ordering === 'name' ? undefined : ordering,
      open_today: filters.open_today ? 'true' : undefined,
      weekend_open: filters.weekend_open ? 'true' : undefined,
      holiday_status: filters.holiday_status || undefined,
      ...facilityQuery,
      page: 1,
      page_size: pageSize.value,
    },
  })
}

function resetFilters() {
  locationMessage.value = ''
  showLocationPanel.value = false
  router.push({ name: 'library-list' })
}

function applySort() {
  const ordering = filters.ordering === 'purpose_score' && !filters.purpose ? 'name' : filters.ordering
  filters.ordering = ordering

  router.push({
    name: 'library-list',
    query: {
      ...route.query,
      ordering: ordering === 'name' ? undefined : ordering,
      page: 1,
    },
  })
}

function togglePurpose(value) {
  locationMessage.value = ''
  if (filters.purpose === value) {
    filters.purpose = ''
    filters.lat = ''
    filters.lng = ''
    if (filters.ordering === 'purpose_score') {
      filters.ordering = 'name'
    }
    return
  }
  filters.purpose = value
  if (value !== 'nearby') {
    filters.lat = ''
    filters.lng = ''
    showLocationPanel.value = false
    return
  }
  if (currentLocation.value) {
    filters.lat = currentLocation.value.lat
    filters.lng = currentLocation.value.lng
    showLocationPanel.value = false
    return
  }
  if (!filters.lat || !filters.lng) {
    locationMessage.value = '가까운 도서관을 보려면 현재 위치를 적용해 주세요.'
    showLocationPanel.value = true
  }
}

function toggleSingleFilter(field, value) {
  filters[field] = filters[field] === value ? '' : value
}

function toggleSigungu(sigungu) {
  sigunguMessage.value = ''
  if (filters.sigungu.includes(sigungu)) {
    filters.sigungu = filters.sigungu.filter((item) => item !== sigungu)
    return
  }
  if (filters.sigungu.length >= 3) {
    sigunguMessage.value = '지역은 최대 3개까지 선택할 수 있습니다.'
    return
  }
  filters.sigungu = [...filters.sigungu, sigungu]
}

function toggleHolidayStatus(value) {
  filters.holiday_status = filters.holiday_status === value ? '' : value
}

function applyCurrentLocation() {
  locationMessage.value = ''
  filters.purpose = 'nearby'

  if (!navigator.geolocation) {
    locationMessage.value = '현재 브라우저에서 위치 정보를 사용할 수 없습니다.'
    return
  }

  isLocationLoading.value = true
  navigator.geolocation.getCurrentPosition(
    (position) => {
      currentLocation.value = storeLocation(position)
      if (!currentLocation.value) {
        locationMessage.value = '현재 위치를 확인하지 못했습니다.'
        isLocationLoading.value = false
        return
      }
      filters.lat = currentLocation.value.lat
      filters.lng = currentLocation.value.lng
      locationMessage.value = ''
      showLocationPanel.value = false
      isLocationLoading.value = false
      applyFilters()
    },
    () => {
      locationMessage.value = '위치 권한을 사용할 수 없어 가까운 도서관 필터를 적용하지 않았습니다.'
      filters.lat = ''
      filters.lng = ''
      isLocationLoading.value = false
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
    <div class="page-hero page-hero-banner page-hero-libraries">
      <h1>도서관 찾기</h1>
      <p>지역, 테마, 운영 조건, 시설 정보를 조합해 오늘 가기 좋은 도서관을 찾아보세요.</p>
    </div>

    <div class="explore-layout">
    <form class="content-panel p-4 filter-panel explore-filter-panel" @submit.prevent="applyFilters">
      <div class="filter-grid">
        <label class="form-field">
          <span>검색</span>
          <input v-model.trim="filters.q" class="form-control" type="search" placeholder="도서관명, 지역, 주소 검색" />
        </label>
        <label class="form-field">
          <span>최소 장서 수</span>
          <input v-model.trim="filters.min_book_count" class="form-control" type="number" min="0" />
        </label>
        <label class="form-field">
          <span>최소 열람좌석 수</span>
          <input v-model.trim="filters.min_reading_seat_count" class="form-control" type="number" min="0" />
        </label>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">
          지역
          <span class="filter-group-note">최대 3개</span>
        </p>
        <div class="filter-chip-grid">
          <button
            v-for="sigungu in SIGUNGU_OPTIONS"
            :key="sigungu"
            class="filter-chip"
            :class="{ active: filters.sigungu.includes(sigungu) }"
            type="button"
            :aria-pressed="filters.sigungu.includes(sigungu)"
            @click="toggleSigungu(sigungu)"
          >
            <span>{{ sigungu }}</span>
          </button>
        </div>
        <p v-if="sigunguMessage" class="field-error mb-0">{{ sigunguMessage }}</p>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">도서관 유형</p>
        <div class="filter-chip-grid">
          <button
            v-for="type in LIBRARY_TYPE_OPTIONS"
            :key="type.value"
            class="filter-chip"
            :class="{ active: filters.library_type === type.value }"
            type="button"
            :aria-pressed="filters.library_type === type.value"
            @click="toggleSingleFilter('library_type', type.value)"
          >
            <span>{{ type.label }}</span>
          </button>
        </div>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">테마</p>
        <div class="filter-chip-grid">
          <button
            v-for="purpose in PURPOSE_OPTIONS"
            :key="purpose.value"
            class="filter-chip"
            :class="{ active: filters.purpose === purpose.value }"
            type="button"
            :aria-pressed="filters.purpose === purpose.value"
            @click="togglePurpose(purpose.value)"
          >
            <span>{{ purpose.label }}</span>
          </button>
        </div>
        <LocationPermissionPanel
          v-if="showLocationPanel"
          class="mt-3"
          :is-loading="isLocationLoading"
          :error-message="locationMessage"
          @confirm="applyCurrentLocation"
          @dismiss="showLocationPanel = false"
        />
        <p v-else-if="locationMessage" class="meta-text mb-0">{{ locationMessage }}</p>
      </div>

      <div class="filter-group">
        <p class="filter-group-title">운영 조건</p>
        <div class="filter-chip-grid">
          <label class="filter-chip">
            <input v-model="filters.open_today" type="checkbox" />
            <span>오늘 운영</span>
          </label>
          <label class="filter-chip">
            <input v-model="filters.weekend_open" type="checkbox" />
            <span>주말 운영</span>
          </label>
          <button
            v-for="option in HOLIDAY_STATUS_OPTIONS"
            :key="option.value"
            class="filter-chip"
            :class="{ active: filters.holiday_status === option.value }"
            type="button"
            :aria-pressed="filters.holiday_status === option.value"
            @click="toggleHolidayStatus(option.value)"
          >
            <span>{{ option.label }}</span>
          </button>
        </div>
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

    <div class="explore-results">
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
        description="검색어나 필터를 조정해 보세요."
      />

      <template v-else>
        <div class="result-toolbar mb-3">
          <div>
            <ResultCount :count="pagination.count" label="곳" />
            <p class="meta-text mb-0">{{ hasFilter ? '검색 필터 결과입니다.' : '전체 도서관 목록입니다.' }}</p>
          </div>
          <div class="result-sort-controls" aria-label="도서관 목록 정렬">
            <label class="result-sort-select">
              <span>정렬</span>
              <select v-model="filters.ordering" class="form-select form-select-sm" @change="applySort">
                <option
                  v-for="option in ORDERING_OPTIONS"
                  :key="option.value"
                  :value="option.value"
                  :disabled="option.value === 'purpose_score' && !filters.purpose"
                >
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>
        </div>
        <div class="library-result-grid">
          <LibraryCard v-for="library in libraries" :key="library.id" :library="library" />
        </div>
        <PaginationBar
          :current-page="page"
          :has-previous="Boolean(pagination.previous)"
          :has-next="Boolean(pagination.next)"
          @change="goToPage"
        />
      </template>
    </div>
    </div>
  </section>
</template>
