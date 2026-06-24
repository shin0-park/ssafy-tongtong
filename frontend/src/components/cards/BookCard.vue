<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
})

const detailTo = computed(() => `/books/${encodeURIComponent(props.book.isbn13)}`)
const metaText = computed(() =>
  [props.book.publisher, props.book.publication_year].filter(Boolean).join(' · '),
)
const kdcText = computed(() =>
  [props.book.kdc_class_name, props.book.kdc_class_no].filter(Boolean).join(' '),
)
</script>

<template>
  <article class="book-card">
    <RouterLink class="book-cover-link" :to="detailTo" :aria-label="`${book.title} 상세 보기`">
      <div class="book-cover">
        <img
          v-if="book.cover_image_url"
          :src="book.cover_image_url"
          :alt="`${book.title} 표지`"
          loading="lazy"
          decoding="async"
        />
        <div v-else class="book-cover-fallback" aria-hidden="true">
          <span>표지 없음</span>
        </div>
      </div>
    </RouterLink>

    <div class="book-card-body">
      <h3 class="book-card-title">
        <RouterLink class="text-decoration-none" :to="detailTo">
          {{ book.title || '제목 정보 없음' }}
        </RouterLink>
      </h3>
      <p class="meta-text mb-2">{{ book.authors_text || '저자 정보 없음' }}</p>
      <p class="meta-text mb-2">{{ metaText || '출판 정보 없음' }}</p>
      <p v-if="kdcText" class="book-chip mb-2">{{ kdcText }}</p>
      <p v-if="book.loan_count !== null && book.loan_count !== undefined" class="meta-text mb-3">
        대출 {{ book.loan_count.toLocaleString() }}회
      </p>
      <button class="btn btn-outline-secondary btn-sm" type="button" disabled>
        저장 준비 중
      </button>
    </div>
  </article>
</template>
