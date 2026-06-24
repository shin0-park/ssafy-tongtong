<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchLibraryDetail } from '@/services/libraryService'

const route = useRoute()

const library = ref(null)
const isLoading = ref(false)
const error = ref(null)

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

  try {
    library.value = await fetchLibraryDetail(route.params.id)
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
    </template>
  </section>
</template>
