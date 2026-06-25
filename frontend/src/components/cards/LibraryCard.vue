<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'
import AttributionOverlay from '@/components/media/AttributionOverlay.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import { FACILITY_LABELS, LIBRARY_TYPE_LABELS, formatNumber } from '@/utils/display'

const props = defineProps({
  library: {
    type: Object,
    required: true,
  },
  compact: {
    type: Boolean,
    default: false,
  },
  showRecommendationReason: {
    type: Boolean,
    default: true,
  },
})

const thumbnailUrl = computed(() => props.library.thumbnail?.url || '')
const locationText = computed(() =>
  [props.library.sido, props.library.sigungu].filter(Boolean).join(' '),
)
const typeText = computed(() => LIBRARY_TYPE_LABELS[props.library.library_type] || props.library.library_type || '도서관')
const operationText = computed(() => {
  if (props.library.open_today === true) return '오늘 운영'
  if (props.library.open_today === false) return '오늘 휴관'
  if (props.library.open_now === true) return '오늘 운영'
  return '운영 확인 필요'
})
const statisticChips = computed(() => {
  const chips = []
  if (props.library.book_count !== null && props.library.book_count !== undefined) {
    chips.push(`장서 ${formatNumber(props.library.book_count)}권`)
  }
  if (props.library.reading_seat_count !== null && props.library.reading_seat_count !== undefined) {
    chips.push(`좌석 ${formatNumber(props.library.reading_seat_count)}석`)
  }
  if (props.library.distance_km !== null && props.library.distance_km !== undefined) {
    chips.push(`${Number(props.library.distance_km).toFixed(1)}km`)
  }
  return chips
})
const facilityChips = computed(() => {
  const profile = props.library.facility_profile
  if (!profile) return []
  const confirmed = Array.isArray(profile.confirmed_facilities)
    ? profile.confirmed_facilities
    : Object.keys(FACILITY_LABELS).filter((key) => profile[key] === true)
  return confirmed.slice(0, 4).map((key) => FACILITY_LABELS[key] || key)
})

function formatHours(hours) {
  if (!hours || typeof hours !== 'object' || !hours.open || !hours.close) return ''
  return `${hours.open}~${hours.close}${hours.closes_next_day ? ' 다음날' : ''}`
}
</script>

<template>
  <article class="library-card" :class="{ 'library-card-compact': compact }">
    <div class="library-thumb">
      <ResponsiveImage
        :src="thumbnailUrl"
        :alt="`${library.name} 대표 이미지`"
        fallback-label="도서관 이미지"
      />
      <AttributionOverlay class="library-attribution" :text="library.thumbnail?.attribution_text" />
    </div>
    <div class="library-card-body">
      <div class="library-card-title-row">
        <div>
          <p class="meta-text mb-1">{{ locationText || typeText }} · {{ typeText }}</p>
          <h3 class="library-card-title">
            <RouterLink class="text-decoration-none" :to="`/libraries/${library.id}`">
              {{ library.name }}
            </RouterLink>
          </h3>
        </div>
        <SaveButton v-if="library.id" compact resource-type="library" :resource-id="library.id" />
      </div>

      <p class="meta-text mb-2 text-truncate">{{ library.road_address || '주소 정보 없음' }}</p>

      <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
        <span class="status-badge status-badge-positive">{{ operationText }}</span>
        <span v-if="formatHours(library.today_hours)" class="meta-text">
          {{ formatHours(library.today_hours) }}
        </span>
      </div>

      <p v-if="library.short_description && !compact" class="meta-text mb-2 text-truncate">
        {{ library.short_description }}
      </p>

      <div v-if="statisticChips.length || facilityChips.length" class="chip-row">
        <span v-for="chip in [...facilityChips, ...statisticChips].slice(0, 5)" :key="chip" class="book-chip">
          {{ chip }}
        </span>
      </div>

      <p v-if="showRecommendationReason && library.recommendation_reason && !compact" class="recommendation-reason mt-3 mb-0">
        {{ library.recommendation_reason }}
      </p>
    </div>
  </article>
</template>
