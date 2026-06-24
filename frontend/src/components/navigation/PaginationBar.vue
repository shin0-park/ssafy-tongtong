<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentPage: {
    type: Number,
    default: 1,
  },
  page: {
    type: Number,
    default: null,
  },
  pageSize: {
    type: Number,
    default: 12,
  },
  totalCount: {
    type: Number,
    default: null,
  },
  hasPrevious: {
    type: Boolean,
    default: false,
  },
  hasNext: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['change'])

const resolvedPage = computed(() => props.page ?? props.currentPage)
const resolvedHasPrevious = computed(() => props.hasPrevious || resolvedPage.value > 1)
const resolvedHasNext = computed(() => {
  if (props.totalCount === null || props.totalCount === undefined) {
    return props.hasNext
  }

  return resolvedPage.value * props.pageSize < props.totalCount
})
</script>

<template>
  <nav class="d-flex justify-content-center gap-2 mt-4" aria-label="페이지 이동">
    <button
      class="btn btn-outline-secondary"
      type="button"
      :disabled="!resolvedHasPrevious"
      @click="$emit('change', resolvedPage - 1)"
    >
      이전
    </button>
    <span class="meta-text align-self-center">{{ resolvedPage }}페이지</span>
    <button
      class="btn btn-outline-secondary"
      type="button"
      :disabled="!resolvedHasNext"
      @click="$emit('change', resolvedPage + 1)"
    >
      다음
    </button>
  </nav>
</template>
