<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'
import AttributionOverlay from '@/components/media/AttributionOverlay.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'

const props = defineProps({
  library: {
    type: Object,
    required: true,
  },
})

const thumbnailUrl = computed(() => props.library.thumbnail?.url || '')
const locationText = computed(() =>
  [props.library.sido, props.library.sigungu].filter(Boolean).join(' '),
)
const operationText = computed(() => {
  if (props.library.open_now === true) {
    return '지금 운영 중'
  }

  if (props.library.open_today === true) {
    return '오늘 운영'
  }

  if (props.library.open_today === false || props.library.open_now === false) {
    return '운영 확인 필요'
  }

  return '운영 정보 없음'
})

function formatHours(hours) {
  if (!hours) {
    return ''
  }

  if (typeof hours === 'string') {
    return hours
  }

  if (hours.open && hours.close) {
    return `${hours.open} ~ ${hours.close}${hours.closes_next_day ? ' 다음날' : ''}`
  }

  return ''
}

function formatHolidayStatus(status) {
  if (!status) {
    return ''
  }

  if (typeof status === 'string') {
    return status
  }

  const labels = {
    open: '운영',
    closed: '휴관',
    unknown: '확인 필요',
  }

  return [status.date, labels[status.status] || status.status].filter(Boolean).join(' · ')
}
</script>

<template>
  <article class="library-card">
    <div class="library-thumb">
      <ResponsiveImage
        :src="thumbnailUrl"
        :alt="`${library.name} 대표 이미지`"
        fallback-label="이미지 없음"
      />
    </div>
    <div class="p-3">
      <AttributionOverlay class="mb-2" :text="library.thumbnail?.attribution_text" />
      <h3 class="h5 mb-2">
        <RouterLink class="stretched-link text-decoration-none" :to="`/libraries/${library.id}`">
          {{ library.name }}
        </RouterLink>
      </h3>
      <p class="meta-text mb-2">{{ locationText || '지역 정보 없음' }}</p>
      <p class="meta-text mb-0 text-truncate">{{ library.road_address || '주소 정보 없음' }}</p>
      <div class="d-flex flex-wrap align-items-center gap-2 mt-3">
        <span class="status-badge status-badge-muted">{{ operationText }}</span>
        <span v-if="library.distance_km !== null && library.distance_km !== undefined" class="meta-text">
          {{ Number(library.distance_km).toFixed(1) }}km
        </span>
      </div>
      <p v-if="formatHours(library.today_hours)" class="meta-text mb-0 mt-2">
        오늘 {{ formatHours(library.today_hours) }}
      </p>
      <p v-if="library.holiday_operation_status" class="meta-text mb-0 mt-2">
        공휴일 {{ formatHolidayStatus(library.holiday_operation_status) }}
      </p>
      <p v-if="library.recommendation_reason" class="recommendation-reason mt-3 mb-0">
        {{ library.recommendation_reason }}
      </p>
      <div class="mt-3">
        <SaveButton resource-type="library" :resource-id="library.id" />
      </div>
    </div>
  </article>
</template>
