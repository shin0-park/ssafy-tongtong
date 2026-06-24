<script setup>
defineProps({
  title: {
    type: String,
    default: '불러오는 중입니다.',
  },
  description: {
    type: String,
    default: '잠시만 기다려주세요.',
  },
})
</script>

<template>
  <div class="content-panel p-4 text-center" aria-live="polite" aria-busy="true">
    <div class="spinner-border text-primary mb-3" role="status" aria-hidden="true"></div>
    <h2 class="h5 mb-2">{{ title }}</h2>
    <p class="mb-0 meta-text">{{ description }}</p>
  </div>
</template>
