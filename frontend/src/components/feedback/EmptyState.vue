<script setup>
defineProps({
  title: {
    type: String,
    default: '표시할 내용이 없습니다.',
  },
  description: {
    type: String,
    default: '조건을 바꾸거나 잠시 후 다시 확인해주세요.',
  },
})
</script>

<template>
  <div class="content-panel p-4 text-center">
    <h2 class="h5 mb-2">{{ title }}</h2>
    <p class="mb-0 meta-text">{{ description }}</p>
  </div>
</template>
