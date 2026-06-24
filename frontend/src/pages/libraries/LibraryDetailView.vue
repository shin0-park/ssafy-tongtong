<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'
import LibraryCard from '@/components/cards/LibraryCard.vue'
import ProgramCard from '@/components/cards/ProgramCard.vue'
import ReviewCard from '@/components/cards/ReviewCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchLibraryDetail, fetchSimilarLibraries } from '@/services/libraryService'
import { fetchPrograms } from '@/services/programService'
import { fetchReviews } from '@/services/reviewService'

const route = useRoute()

const library = ref(null)
const relatedPrograms = ref([])
const relatedReviews = ref([])
const similarLibraries = ref([])
const isLoading = ref(false)
const error = ref(null)
const sectionErrors = ref({
  programs: '',
  reviews: '',
  similar: '',
})

const facilityItems = computed(() => {
  const profile = library.value?.facility_profile

  if (!profile) {
    return []
  }

  const labels = {
    has_reading_room: '열람실',
    has_children_room: '어린이실',
    has_digital_room: '디지털 자료실',
    has_parking: '주차장',
    has_cafe: '카페',
    has_wifi: '와이파이',
    has_nursing_room: '수유실',
    has_accessible_facility: '장애인 편의시설',
    has_elevator: '엘리베이터',
    has_lounge: '휴게 공간',
    has_outdoor_space: '야외 공간',
  }

  return Object.entries(labels)
    .filter(([key]) => profile[key] === true)
    .map(([key, label]) => ({ key, label }))
})

async function loadLibrary() {
  isLoading.value = true
  error.value = null
  sectionErrors.value = {
    programs: '',
    reviews: '',
    similar: '',
  }

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
      <div class="mb-4">
        <p class="meta-text mb-1">{{ library.sido }} {{ library.sigungu }}</p>
        <h1 class="page-title">{{ library.name }}</h1>
        <p class="page-subtitle">{{ library.short_description || library.road_address }}</p>
        <div class="mt-3">
          <SaveButton resource-type="library" :resource-id="library.id" />
        </div>
      </div>

      <div class="row g-4">
        <div class="col-lg-7">
          <div class="content-panel overflow-hidden">
            <div class="library-thumb">
              <img
                v-if="library.thumbnail?.url"
                :src="library.thumbnail.url"
                :alt="`${library.name} 대표 이미지`"
                loading="lazy"
                decoding="async"
              />
            </div>
            <div class="p-4">
              <h2 class="section-title">기본 정보</h2>
              <dl class="row mb-0">
                <dt class="col-sm-4">주소</dt>
                <dd class="col-sm-8">{{ library.road_address || '주소 정보 없음' }}</dd>
                <dt class="col-sm-4">전화</dt>
                <dd class="col-sm-8">{{ library.phone || '전화 정보 없음' }}</dd>
                <dt class="col-sm-4">운영 기관</dt>
                <dd class="col-sm-8">{{ library.operating_agency || '기관 정보 없음' }}</dd>
                <dt class="col-sm-4">홈페이지</dt>
                <dd class="col-sm-8">
                  <a v-if="library.homepage_url" :href="library.homepage_url" target="_blank" rel="noopener">
                    홈페이지 열기
                  </a>
                  <span v-else>홈페이지 정보 없음</span>
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div class="col-lg-5 d-grid gap-4">
          <section class="content-panel p-4">
            <h2 class="section-title">운영 상태</h2>
            <dl class="row mb-0">
              <dt class="col-6">오늘 운영</dt>
              <dd class="col-6 text-end">{{ library.open_today === null || library.open_today === undefined ? '정보 없음' : library.open_today ? '운영' : '미운영' }}</dd>
              <dt class="col-6">지금 운영</dt>
              <dd class="col-6 text-end">{{ library.open_now === null || library.open_now === undefined ? '정보 없음' : library.open_now ? '운영 중' : '운영 아님' }}</dd>
              <dt class="col-6">오늘 시간</dt>
              <dd class="col-6 text-end">{{ library.today_hours || '정보 없음' }}</dd>
              <dt class="col-6">공휴일 운영</dt>
              <dd class="col-6 text-end">{{ library.holiday_operation_status || '정보 없음' }}</dd>
            </dl>
          </section>

          <section class="content-panel p-4">
            <h2 class="section-title">통계</h2>
            <dl class="row mb-0">
              <dt class="col-6">장서 수</dt>
              <dd class="col-6 text-end">{{ library.statistics?.book_count ?? library.book_count ?? '-' }}</dd>
              <dt class="col-6">열람석</dt>
              <dd class="col-6 text-end">
                {{ library.statistics?.reading_seat_count ?? library.reading_seat_count ?? '-' }}
              </dd>
            </dl>
          </section>

          <section class="content-panel p-4">
            <h2 class="section-title">확인된 시설</h2>
            <p v-if="!library.facility_profile" class="meta-text mb-0">
              확인된 시설 정보가 아직 없습니다.
            </p>
            <p v-else-if="!facilityItems.length" class="meta-text mb-0">
              명시적으로 확인된 시설이 없습니다.
            </p>
            <div v-else class="d-flex flex-wrap gap-2">
              <span v-for="facility in facilityItems" :key="facility.key" class="badge text-bg-light">
                {{ facility.label }}
              </span>
            </div>
          </section>
        </div>
      </div>

      <section class="mt-5">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
          <h2 class="section-title mb-0">비슷한 도서관</h2>
        </div>
        <p v-if="sectionErrors.similar" class="meta-text">{{ sectionErrors.similar }}</p>
        <EmptyState
          v-else-if="!similarLibraries.length"
          title="비슷한 도서관 정보가 없어요."
          description="추천 데이터가 준비되면 이곳에 표시됩니다."
        />
        <div v-else class="responsive-card-grid">
          <LibraryCard v-for="item in similarLibraries" :key="item.id" :library="item" />
        </div>
      </section>

      <section class="mt-5">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
          <h2 class="section-title mb-0">관련 프로그램</h2>
          <RouterLink class="btn btn-outline-primary btn-sm" :to="`/programs?library_id=${library.id}`">
            더 보기
          </RouterLink>
        </div>
        <p v-if="sectionErrors.programs" class="meta-text">{{ sectionErrors.programs }}</p>
        <EmptyState
          v-else-if="!relatedPrograms.length"
          title="관련 프로그램이 없어요."
          description="프로그램 데이터가 들어오면 이곳에 표시됩니다."
        />
        <div v-else class="stack-list">
          <ProgramCard v-for="program in relatedPrograms" :key="program.id" :program="program" />
        </div>
      </section>

      <section class="mt-5">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
          <h2 class="section-title mb-0">관련 후기</h2>
          <RouterLink class="btn btn-outline-primary btn-sm" :to="`/community?library_id=${library.id}`">
            더 보기
          </RouterLink>
        </div>
        <p v-if="sectionErrors.reviews" class="meta-text">{{ sectionErrors.reviews }}</p>
        <EmptyState
          v-else-if="!relatedReviews.length"
          title="관련 후기가 없어요."
          description="후기가 등록되면 이곳에 표시됩니다."
        />
        <div v-else class="stack-list">
          <ReviewCard v-for="review in relatedReviews" :key="review.id" :review="review" />
        </div>
      </section>
    </template>
  </section>
</template>
