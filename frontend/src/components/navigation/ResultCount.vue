<script setup>
defineProps({
  count: {
    type: Number,
    default: 0,
  },
  unit: {
    type: String,
    default: '건',
  },
  label: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <p class="meta-text mb-3">총 {{ count.toLocaleString() }}{{ label || unit }}</p>
</template>
