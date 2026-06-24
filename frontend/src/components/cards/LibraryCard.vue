<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

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
    </div>
  </article>
</template>
