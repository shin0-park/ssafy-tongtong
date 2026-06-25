<script setup>
defineProps({
  library: {
    type: Object,
    required: true,
  },
  holding: {
    type: Object,
    default: null,
  },
})
</script>

<template>
  <article class="holding-card">
    <div>
      <h3 class="h5 mb-2">{{ library.name || '도서관명 없음' }}</h3>
      <p class="meta-text mb-2">{{ library.address || '주소 정보 없음' }}</p>
      <span v-if="holding?.call_number" class="book-chip">청구기호 {{ holding.call_number }}</span>
    </div>
    <div class="holding-card-actions">
      <a
        v-if="library.homepage_url"
        class="btn btn-outline-secondary btn-sm"
        :href="library.homepage_url"
        target="_blank"
        rel="noopener noreferrer"
      >
        홈페이지
      </a>
      <span v-if="library.phone" class="meta-text">{{ library.phone }}</span>
    </div>
  </article>
</template>
