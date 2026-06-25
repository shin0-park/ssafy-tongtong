<script setup>
defineProps({
  title: {
    type: String,
    default: '문제가 발생했습니다.',
  },
  message: {
    type: String,
    default: '요청을 처리하지 못했어요.',
  },
  retryLabel: {
    type: String,
    default: '다시 시도',
  },
})

defineEmits(['retry'])
</script>

<template>
  <div class="content-panel p-4" role="alert">
    <h2 class="h5 mb-2">{{ title }}</h2>
    <p class="mb-3 meta-text">{{ message }}</p>
    <button class="btn btn-outline-primary btn-sm" type="button" @click="$emit('retry')">
      {{ retryLabel }}
    </button>
  </div>
</template>
