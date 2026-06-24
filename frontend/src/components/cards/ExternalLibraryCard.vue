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
      <p class="meta-text mb-1">외부 도서관 정보</p>
      <h3 class="h5 mb-2">{{ library.name || '도서관명 없음' }}</h3>
      <p class="meta-text mb-2">{{ library.address || '주소 정보 없음' }}</p>
      <p class="meta-text mb-2">서비스 도서관 정보와 아직 연결되지 않았습니다.</p>
      <span class="book-chip">
        {{
          holding?.loan_available === true
            ? '대출 가능'
            : holding?.loan_available === false
              ? '대출 불가'
              : '대출 상태 미제공'
        }}
      </span>
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
