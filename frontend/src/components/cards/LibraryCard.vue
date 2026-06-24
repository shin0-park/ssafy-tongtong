<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'

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
</script>

<template>
  <article class="library-card">
    <div class="library-thumb">
      <img
        v-if="thumbnailUrl"
        :src="thumbnailUrl"
        :alt="`${library.name} 대표 이미지`"
        loading="lazy"
        decoding="async"
      />
    </div>
    <div class="p-3">
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
      <p v-if="library.today_hours" class="meta-text mb-0 mt-2">오늘 {{ library.today_hours }}</p>
      <p v-if="library.holiday_operation_status" class="meta-text mb-0 mt-2">
        공휴일 {{ library.holiday_operation_status }}
      </p>
      <div class="mt-3">
        <SaveButton resource-type="library" :resource-id="library.id" />
      </div>
    </div>
  </article>
</template>
