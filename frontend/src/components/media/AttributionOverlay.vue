<script setup>
defineProps({
  text: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <span v-if="text" class="image-attribution">
    <button class="btn btn-outline-secondary btn-sm" type="button">ⓘ 출처</button>
    <span class="image-attribution-text">{{ text }}</span>
  </span>
</template>
