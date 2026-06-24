<script setup>
import { computed } from 'vue'

import { resolveMediaUrl } from '@/utils/media'

const props = defineProps({
  src: {
    type: String,
    default: '',
  },
  alt: {
    type: String,
    default: '',
  },
  fallbackLabel: {
    type: String,
    default: '이미지 없음',
  },
})

const imageUrl = computed(() => resolveMediaUrl(props.src))
</script>

<template>
  <img v-if="imageUrl" :src="imageUrl" :alt="alt" loading="lazy" decoding="async" />
  <div v-else class="book-cover-fallback" aria-hidden="true">
    <span>{{ fallbackLabel }}</span>
  </div>
</template>
