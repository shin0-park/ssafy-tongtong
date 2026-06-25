<script setup>
defineProps({
  to: {
    type: [String, Object],
    required: true,
  },
  label: {
    type: String,
    default: '뒤로가기',
  },
})
</script>

<template>
  <div class="page-back-row">
    <RouterLink class="page-back-button text-decoration-none" :to="to" :aria-label="label" :title="label">
      <span aria-hidden="true">‹</span>
      <span class="visually-hidden">{{ label }}</span>
    </RouterLink>
  </div>
</template>
