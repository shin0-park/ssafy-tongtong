<script setup>
defineProps({
  message: {
    type: String,
    default: '가까운 도서관을 찾으려면 현재 위치가 필요해요.',
  },
  detail: {
    type: String,
    default: '위치는 가까운 도서관 검색에만 사용됩니다.',
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
  errorMessage: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['confirm', 'dismiss'])
</script>

<template>
  <aside class="location-permission-panel" role="status" aria-live="polite">
    <div class="location-permission-copy">
      <strong>{{ message }}</strong>
      <span>{{ detail }}</span>
      <span v-if="errorMessage" class="field-error">{{ errorMessage }}</span>
    </div>
    <div class="location-permission-actions">
      <button class="btn btn-primary btn-sm" type="button" :disabled="isLoading" @click="emit('confirm')">
        {{ isLoading ? '위치 확인 중' : '현재 위치 적용' }}
      </button>
      <button class="btn btn-outline-secondary btn-sm" type="button" :disabled="isLoading" @click="emit('dismiss')">
        나중에
      </button>
    </div>
  </aside>
</template>
