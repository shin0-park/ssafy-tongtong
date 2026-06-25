<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'
import LibraryCard from '@/components/cards/LibraryCard.vue'
import ProgramCard from '@/components/cards/ProgramCard.vue'
import ReviewCard from '@/components/cards/ReviewCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import AttributionOverlay from '@/components/media/AttributionOverlay.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import KakaoMapPanel from '@/components/maps/KakaoMapPanel.vue'
import { fetchLibraryDetail, fetchSimilarLibraries } from '@/services/libraryService'
import { fetchPrograms } from '@/services/programService'
import { fetchReviews } from '@/services/reviewService'
import { FACILITY_LABELS, LIBRARY_TYPE_LABELS, formatNumber } from '@/utils/display'

const route = useRoute()

const library = ref(null)
const relatedPrograms = ref([])
const relatedReviews = ref([])
const similarLibraries = ref([])
const isLoading = ref(false)
const error = ref(null)
const sectionErrors = ref({ programs: '', reviews: '', similar: '' })

const locationText = computed(() => [library.value?.sido, library.value?.sigungu].filter(Boolean).join(' '))
const typeText = computed(() => LIBRARY_TYPE_LABELS[library.value?.library_type] || library.value?.library_type || '도서관')
const facilityItems = computed(() => {
  const profile = library.value?.facility_profile
  if (!profile) return []
  const confirmed = Array.isArray(profile.confirmed_facilities)
    ? profile.confirmed_facilities
    : Object.keys(FACILITY_LABELS).filter((key) => profile[key] === true)
  return confirmed.map((key) => ({ key, label: FACILITY_LABELS[key] || key }))
})
const stat = computed(() => library.value?.statistics ?? {})
const topTags = computed(() => {
  const chips = facilityItems.value.map((item) => item.label)
  if (library.value?.reading_seat_count) chips.push('열람좌석')
  if (library.value?.book_count) chips.push('장서 풍부')
  return chips.slice(0, 5)
})

function boolText(value, trueText, falseText, unknownText = '확인 필요') {
  if (value === true) return trueText
  if (value === false) return falseText
  return unknownText
}

function formatHours(hours) {
  if (!hours) return '정보 없음'
  if (typeof hours === 'string') return hours
  if (hours.open && hours.close) return `${hours.open} ~ ${hours.close}${hours.closes_next_day ? ' 다음날' : ''}`
  return '정보 없음'
}

function openingHourLabel(hour) {
  if (hour.raw_text) return hour.raw_text
  if (hour.schedule_status && hour.schedule_status !== 'open') return hour.schedule_status
  if (hour.open_time && hour.close_time) {
    return `${hour.open_time} ~ ${hour.close_time}${hour.closes_next_day ? ' 다음날' : ''}`
  }
  return '정보 없음'
}

function dayTypeLabel(hour) {
  if (hour.day_type === 'weekday') return '평일'
  if (hour.day_type === 'saturday') return '토요일'
  if (hour.day_type === 'sunday') return '일요일'
  if (hour.day_type === 'holiday') return '공휴일'
  if (hour.day_of_week !== null && hour.day_of_week !== undefined) return `요일 ${hour.day_of_week}`
  return hour.day_type || '운영시간'
}

async function loadLibrary() {
  isLoading.value = true
  error.value = null
  sectionErrors.value = { programs: '', reviews: '', similar: '' }

  try {
    library.value = await fetchLibraryDetail(route.params.id)
    const [programsResult, reviewsResult, similarResult] = await Promise.allSettled([
      fetchPrograms({ library_id: route.params.id, page_size: 3 }),
      fetchReviews({ library_id: route.params.id, page_size: 3 }),
      fetchSimilarLibraries(route.params.id, { limit: 3 }),
    ])

    if (programsResult.status === 'fulfilled') {
      relatedPrograms.value = programsResult.value.results ?? []
    } else {
      relatedPrograms.value = []
      sectionErrors.value.programs = '관련 프로그램을 불러오지 못했어요.'
    }

    if (reviewsResult.status === 'fulfilled') {
      relatedReviews.value = reviewsResult.value.results ?? []
    } else {
      relatedReviews.value = []
      sectionErrors.value.reviews = '관련 후기를 불러오지 못했어요.'
    }

    if (similarResult.status === 'fulfilled') {
      similarLibraries.value = similarResult.value.results ?? similarResult.value ?? []
    } else {
      similarLibraries.value = []
      sectionErrors.value.similar = '비슷한 도서관을 불러오지 못했어요.'
    }
  } catch (requestError) {
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

watch(() => route.params.id, loadLibrary)
onMounted(loadLibrary)
</script>

<template>
  <section class="page-shell">
    <LoadingState v-if="isLoading" title="도서관 정보를 불러오는 중입니다." />
    <ErrorState
      v-else-if="error"
      title="도서관 정보를 불러오지 못했습니다."
      :message="error.message"
      @retry="loadLibrary"
    />
    <EmptyState v-else-if="!library" title="도서관 정보가 없습니다." />

    <template v-else>
      <section class="content-panel overflow-hidden mb-4">
        <div class="library-detail-hero">
          <ResponsiveImage
            :src="library.thumbnail?.url"
            :alt="`${library.name} 대표 이미지`"
            fallback-label="도서관 이미지"
          />
          <AttributionOverlay class="library-attribution" :text="library.thumbnail?.attribution_text" />
        </div>
        <div class="p-4">
          <p class="meta-text mb-1">{{ locationText }} · {{ typeText }}</p>
          <div class="d-flex flex-wrap align-items-start justify-content-between gap-3">
            <div>
              <h1 class="page-title">{{ library.name }}</h1>
              <p class="page-subtitle">{{ library.short_description || library.road_address }}</p>
            </div>
            <SaveButton resource-type="library" :resource-id="library.id" />
          </div>
          <div class="chip-row mt-3">
            <span class="status-badge status-badge-positive">
              {{ boolText(library.open_today, '오늘 운영', '오늘 휴관') }}
            </span>
            <span v-for="tag in topTags" :key="tag" class="book-chip">{{ tag }}</span>
          </div>
        </div>
      </section>

      <div class="row g-4 mb-4">
        <div class="col-lg-6">
          <section class="content-panel p-4 h-100">
            <h2 class="section-title">기본 정보</h2>
            <dl class="row mb-0">
              <dt class="col-sm-4">도로명주소</dt>
              <dd class="col-sm-8">{{ library.road_address || '주소 정보 없음' }}</dd>
              <dt class="col-sm-4">전화번호</dt>
              <dd class="col-sm-8">{{ library.phone || '전화 정보 없음' }}</dd>
              <dt class="col-sm-4">홈페이지</dt>
              <dd class="col-sm-8">
                <a v-if="library.homepage_url" :href="library.homepage_url" target="_blank" rel="noopener">
                  홈페이지 열기
                </a>
                <span v-else>홈페이지 정보 없음</span>
              </dd>
              <dt class="col-sm-4">운영기관</dt>
              <dd class="col-sm-8">{{ library.operating_agency || '운영기관 정보 없음' }}</dd>
            </dl>
          </section>
        </div>
        <div class="col-lg-6">
          <section class="content-panel p-4 h-100">
            <h2 class="section-title">운영 정보</h2>
            <dl class="row mb-0">
              <dt class="col-sm-4">오늘 운영</dt>
              <dd class="col-sm-8">{{ boolText(library.open_today, '운영', '휴관') }}</dd>
              <dt class="col-sm-4">현재 운영</dt>
              <dd class="col-sm-8">{{ boolText(library.open_now, '운영 중', '운영 중 아님') }}</dd>
              <dt class="col-sm-4">오늘 시간</dt>
              <dd class="col-sm-8">{{ formatHours(library.today_hours) }}</dd>
              <template v-for="hour in (library.opening_hours ?? []).slice(0, 4)" :key="hour.id || `${hour.day_type}-${hour.sequence}`">
                <dt class="col-sm-4">{{ dayTypeLabel(hour) }}</dt>
                <dd class="col-sm-8">{{ openingHourLabel(hour) }}</dd>
              </template>
              <dt class="col-sm-4">휴관일</dt>
              <dd class="col-sm-8">
                <span v-if="library.closure_rules?.length">
                  {{ library.closure_rules.map((rule) => rule.raw_text || rule.normalized_rule).filter(Boolean).join(', ') }}
                </span>
                <span v-else>휴관 정보 없음</span>
              </dd>
            </dl>
          </section>
        </div>
      </div>

      <div class="row g-4 mb-4">
        <div class="col-lg-6">
          <section class="content-panel p-4 h-100">
            <h2 class="section-title">장서/열람·공간 규모</h2>
            <dl class="row mb-0">
              <dt class="col-6">도서 자료 수</dt>
              <dd class="col-6 text-end">{{ formatNumber(stat.book_count ?? library.book_count) }}</dd>
              <dt class="col-6">비도서 수</dt>
              <dd class="col-6 text-end">{{ formatNumber(stat.non_book_count) }}</dd>
              <dt class="col-6">연속간행물 수</dt>
              <dd class="col-6 text-end">{{ formatNumber(stat.serial_count) }}</dd>
              <dt class="col-6">열람좌석 수</dt>
              <dd class="col-6 text-end">{{ formatNumber(stat.reading_seat_count ?? library.reading_seat_count) }}</dd>
              <dt class="col-6">부지면적</dt>
              <dd class="col-6 text-end">{{ formatNumber(stat.site_area) }}</dd>
              <dt class="col-6">건물면적</dt>
              <dd class="col-6 text-end">{{ formatNumber(stat.building_area) }}</dd>
            </dl>
          </section>
        </div>
        <div class="col-lg-6">
          <section class="content-panel p-4 h-100">
            <h2 class="section-title">시설/공간 정보</h2>
            <p v-if="!library.facility_profile" class="meta-text mb-0">시설 데이터가 아직 수집되지 않았습니다.</p>
            <p v-else-if="!facilityItems.length" class="meta-text mb-0">명시적으로 확인된 시설이 없습니다.</p>
            <div v-else class="chip-row">
              <span v-for="facility in facilityItems" :key="facility.key" class="facility-chip">{{ facility.label }}</span>
            </div>
          </section>
        </div>
      </div>

      <section class="content-panel p-4 mb-5">
        <h2 class="section-title">위치 정보</h2>
        <KakaoMapPanel
          :latitude="library.latitude"
          :longitude="library.longitude"
          :title="library.name"
          :address="library.road_address"
        />
      </section>

      <section class="mb-5">
        <div class="section-header-row">
          <h2 class="section-title mb-0">관련 문화 프로그램</h2>
          <RouterLink class="btn btn-outline-primary btn-sm" :to="`/programs?library_id=${library.id}`">더보기</RouterLink>
        </div>
        <p v-if="sectionErrors.programs" class="meta-text">{{ sectionErrors.programs }}</p>
        <EmptyState v-else-if="!relatedPrograms.length" title="관련 프로그램이 없어요." />
        <div v-else class="responsive-card-grid">
          <ProgramCard v-for="program in relatedPrograms" :key="program.id" :program="program" />
        </div>
      </section>

      <section class="mb-5">
        <div class="section-header-row">
          <h2 class="section-title mb-0">관련 후기</h2>
          <RouterLink class="btn btn-outline-primary btn-sm" :to="`/community?library_id=${library.id}`">더보기</RouterLink>
        </div>
        <p v-if="sectionErrors.reviews" class="meta-text">{{ sectionErrors.reviews }}</p>
        <EmptyState v-else-if="!relatedReviews.length" title="관련 후기가 없어요." />
        <div v-else class="stack-list">
          <ReviewCard v-for="review in relatedReviews" :key="review.id" :review="review" />
        </div>
      </section>

      <section>
        <div class="section-header-row">
          <h2 class="section-title mb-0">비슷한 도서관 추천</h2>
        </div>
        <p v-if="sectionErrors.similar" class="meta-text">{{ sectionErrors.similar }}</p>
        <EmptyState v-else-if="!similarLibraries.length" title="비슷한 도서관 정보가 없어요." />
        <div v-else class="responsive-card-grid-three">
          <LibraryCard v-for="item in similarLibraries.slice(0, 3)" :key="item.id" :library="item" />
        </div>
      </section>
    </template>
  </section>
</template>
