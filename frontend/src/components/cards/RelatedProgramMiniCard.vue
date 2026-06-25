<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  program: {
    type: Object,
    required: true,
  },
})

const titleText = computed(() => props.program.title || props.program.name || '관련 프로그램')
const detailTo = computed(() => (props.program.id ? `/programs/${props.program.id}` : ''))
</script>

<template>
  <article class="mini-card">
    <strong>
      <RouterLink v-if="detailTo" class="text-decoration-none" :to="detailTo">
        {{ titleText }}
      </RouterLink>
      <span v-else>{{ titleText }}</span>
    </strong>
    <p class="meta-text mb-0">{{ program.category_display || program.operation_status_display || '프로그램 정보' }}</p>
  </article>
</template>
