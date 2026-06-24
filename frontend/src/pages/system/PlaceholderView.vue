<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '이 화면은 API 기반 구조 연결 후 확장할 예정입니다.',
  },
})
</script>

<template>
  <section class="page-shell">
    <h1 class="page-title">{{ title }}</h1>
    <p class="page-subtitle">{{ description }}</p>
  </section>
</template>
