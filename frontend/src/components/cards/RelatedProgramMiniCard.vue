<script setup>
defineProps({
  program: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <article class="mini-card">
    <strong>{{ program.title || program.name || '관련 프로그램' }}</strong>
    <p class="meta-text mb-0">{{ program.category_display || program.operation_status_display || '프로그램 정보' }}</p>
  </article>
</template>
