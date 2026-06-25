<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import { formatNumber } from '@/utils/display'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
  rank: {
    type: [Number, String],
    default: null,
  },
})

const detailTo = computed(() => `/books/${encodeURIComponent(props.book.isbn13)}`)
const metaText = computed(() =>
  [props.book.authors_text, props.book.publisher, props.book.publication_year || props.book.publication_date]
    .filter(Boolean)
    .join(' · '),
)
const kdcText = computed(() =>
  [props.book.kdc_class_name, props.book.kdc_class_no].filter(Boolean).join(' '),
)
</script>

<template>
  <article class="book-card">
    <RouterLink class="book-cover-link" :to="detailTo" :aria-label="`${book.title} 상세 보기`">
      <div class="book-cover">
        <ResponsiveImage
          :src="book.cover_image_url"
          :alt="`${book.title} 표지`"
          fallback-label="표지 없음"
        />
        <span v-if="rank" class="rank-badge">TOP {{ rank }}</span>
      </div>
    </RouterLink>

    <div class="book-card-body">
      <h3 class="book-card-title">
        <RouterLink class="text-decoration-none" :to="detailTo">
          {{ book.title || '제목 정보 없음' }}
        </RouterLink>
      </h3>
      <p class="meta-text mb-2">{{ metaText || '저자/출판 정보 없음' }}</p>
      <p v-if="book.description" class="meta-text mb-2 book-description-clamp">
        {{ book.description }}
      </p>
      <div class="chip-row mb-3">
        <span v-if="kdcText" class="book-chip">{{ kdcText }}</span>
        <span v-if="book.loan_count !== null && book.loan_count !== undefined" class="book-chip">
          대출 {{ formatNumber(book.loan_count) }}회
        </span>
      </div>
      <SaveButton v-if="book.isbn13" resource-type="book" :resource-id="book.isbn13" />
    </div>
  </article>
</template>
