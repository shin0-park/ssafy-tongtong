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
import BackLink from '@/components/navigation/BackLink.vue'
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
const WEEKDAY_LABELS = ['월', '화', '수', '목', '금', '토', '일']

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
const todayOperationText = computed(() => {
  const statusText = boolText(library.value?.open_today, '운영', '휴관')
  const hoursText = formatHours(library.value?.today_hours, '')
  return [statusText, hoursText].filter(Boolean).join(' · ')
})
const displayOpeningHours = computed(() => {
  const seen = new Set()
  return (library.value?.opening_hours ?? [])
    .filter((hour) => !isClosedAllDayHour(hour))
    .map((hour) => ({
      key: hour.id || `${hour.day_type}-${hour.day_of_week ?? ''}-${hour.specific_date ?? ''}-${hour.sequence ?? ''}`,
      label: dayTypeLabel(hour),
      text: openingHourLabel(hour),
    }))
    .filter((item) => {
      const signature = `${item.label}-${item.text}`
      if (seen.has(signature)) return false
      seen.add(signature)
      return true
    })
})
const closureText = computed(() => formatClosureRules(library.value?.closure_rules ?? []))

function boolText(value, trueText, falseText, unknownText = '확인 필요') {
  if (value === true) return trueText
  if (value === false) return falseText
  return unknownText
}

function formatHours(hours, fallback = '정보 없음') {
  if (!hours) return fallback
  if (typeof hours === 'string') return hours
  if (hours.open && hours.close) return `${hours.open} ~ ${hours.close}${hours.closes_next_day ? ' 다음날' : ''}`
  return fallback
}

function openingHourLabel(hour) {
  if (hour.raw_text) return hour.raw_text
  if (hour.schedule_status && hour.schedule_status !== 'open') return hour.schedule_status
  if (hour.open_time && hour.close_time) {
    return `${hour.open_time} ~ ${hour.close_time}${hour.closes_next_day ? ' 다음날' : ''}`
  }
  return '정보 없음'
}

function isClosedAllDayHour(hour) {
  const rawText = String(hour.raw_text || '').replace(/\s/g, '')
  const openTime = String(hour.open_time || '').slice(0, 5)
  const closeTime = String(hour.close_time || '').slice(0, 5)
  return rawText === '00:00~00:00' || (openTime === '00:00' && closeTime === '00:00')
}

function dayTypeLabel(hour) {
  if (hour.day_type === 'weekday') return '평일'
  if (hour.day_type === 'saturday') return '토요일'
  if (hour.day_type === 'sunday') return '일요일'
  if (hour.day_type === 'holiday' || hour.day_type === 'public_holiday') return '주말/공휴일'
  if (hour.day_of_week !== null && hour.day_of_week !== undefined) return WEEKDAY_LABELS[Number(hour.day_of_week)] || '운영시간'
  return hour.day_type || '운영시간'
}

function addClosureLabel(labels, value) {
  if (!value) return
  labels.add(value)
}

function addClosureDay(labels, value) {
  const label = WEEKDAY_LABELS[Number(value)]
  addClosureLabel(labels, label)
}

function addClosureLabelsFromText(labels, text) {
  const normalized = String(text || '').replace(/\s/g, '')
  if (!normalized) return
  const tokens = normalized.split(/[,+/·ㆍ|]+/).filter(Boolean)

  tokens.forEach((token) => {
    if (token === '월' || token.includes('월요일')) addClosureLabel(labels, '월')
    if (token === '화' || token.includes('화요일')) addClosureLabel(labels, '화')
    if (token === '수' || token.includes('수요일')) addClosureLabel(labels, '수')
    if (token === '목' || token.includes('목요일')) addClosureLabel(labels, '목')
    if (token === '금' || token.includes('금요일')) addClosureLabel(labels, '금')
    if (token === '토' || token.includes('토요일')) addClosureLabel(labels, '토')
    if (token === '일' || token.includes('일요일')) addClosureLabel(labels, '일')
    if (token.includes('공휴일') || token === '휴일') addClosureLabel(labels, '공휴일')
  })
}

function formatClosureRules(rules) {
  const labels = new Set()

  rules.forEach((rule) => {
    const normalizedRule = rule.normalized_rule && typeof rule.normalized_rule === 'object' ? rule.normalized_rule : {}

    if (rule.rule_type === 'weekly' || rule.rule_type === 'nth_weekday') {
      if (Array.isArray(normalizedRule.day_of_week)) {
        normalizedRule.day_of_week.forEach((day) => addClosureDay(labels, day))
      } else {
        addClosureDay(labels, normalizedRule.day_of_week)
      }
    }

    if (rule.rule_type === 'public_holiday' || rule.rule_type === 'named_holiday') {
      addClosureLabel(labels, '공휴일')
    }

    addClosureLabelsFromText(labels, rule.raw_text)
  })

  const order = ['월', '화', '수', '목', '금', '토', '일', '공휴일']
  const orderedLabels = order.filter((label) => labels.has(label))
  return orderedLabels.length ? orderedLabels.join(', ') : ''
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
    <BackLink to="/libraries" label="도서관 찾기로 돌아가기" />

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

      <section class="content-panel p-4 mb-4">
        <h2 class="section-title">위치 정보</h2>
        <KakaoMapPanel
          :latitude="library.latitude"
          :longitude="library.longitude"
          :title="library.name"
          :address="library.road_address"
        />
      </section>

      <div class="library-detail-info-grid mb-5">
        <section class="content-panel p-4">
          <h2 class="section-title">기본 정보</h2>
          <dl class="library-detail-dl mb-0">
            <dt>도로명주소</dt>
            <dd>{{ library.road_address || '주소 정보 없음' }}</dd>
            <dt>전화번호</dt>
            <dd>{{ library.phone || '전화 정보 없음' }}</dd>
            <dt>홈페이지</dt>
            <dd>
              <a v-if="library.homepage_url" :href="library.homepage_url" target="_blank" rel="noopener">
                홈페이지 열기
              </a>
              <span v-else>홈페이지 정보 없음</span>
            </dd>
            <dt>운영기관</dt>
            <dd>{{ library.operating_agency || '운영기관 정보 없음' }}</dd>
          </dl>
        </section>

        <section class="content-panel p-4">
          <h2 class="section-title">운영 정보</h2>
          <dl class="library-detail-dl mb-0">
            <dt>오늘 운영</dt>
            <dd>{{ todayOperationText }}</dd>
            <template v-for="hour in displayOpeningHours" :key="hour.key">
              <dt>{{ hour.label }}</dt>
              <dd>{{ hour.text }}</dd>
            </template>
            <dt>휴관일</dt>
            <dd>
              <span v-if="closureText">{{ closureText }}</span>
              <span v-else>휴관 정보 없음</span>
            </dd>
          </dl>
        </section>

        <section class="content-panel p-4">
          <h2 class="section-title">장서/열람·공간 규모</h2>
          <dl class="library-detail-dl library-detail-dl-numeric mb-0">
            <dt>도서 자료 수</dt>
            <dd>{{ formatNumber(stat.book_count ?? library.book_count) }}</dd>
            <dt>비도서 수</dt>
            <dd>{{ formatNumber(stat.non_book_count) }}</dd>
            <dt>연속간행물 수</dt>
            <dd>{{ formatNumber(stat.serial_count) }}</dd>
            <dt>열람좌석 수</dt>
            <dd>{{ formatNumber(stat.reading_seat_count ?? library.reading_seat_count) }}</dd>
            <dt>부지면적</dt>
            <dd>{{ formatNumber(stat.site_area) }}</dd>
            <dt>건물면적</dt>
            <dd>{{ formatNumber(stat.building_area) }}</dd>
          </dl>
        </section>

        <section class="content-panel p-4">
          <h2 class="section-title">시설/공간 정보</h2>
          <p v-if="!library.facility_profile" class="meta-text mb-0">시설 데이터가 아직 수집되지 않았습니다.</p>
          <p v-else-if="!facilityItems.length" class="meta-text mb-0">명시적으로 확인된 시설이 없습니다.</p>
          <div v-else class="chip-row">
            <span v-for="facility in facilityItems" :key="facility.key" class="facility-chip">{{ facility.label }}</span>
          </div>
        </section>
      </div>

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
