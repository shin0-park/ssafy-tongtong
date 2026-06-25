<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  book: {
    type: Object,
    required: true,
  },
})

const titleText = computed(() => props.book.title || props.book.name || props.book.isbn13 || '관련 책')
const detailTo = computed(() =>
  props.book.isbn13 ? `/books/${encodeURIComponent(props.book.isbn13)}` : '',
)
</script>

<template>
  <article class="mini-card">
    <strong>
      <RouterLink v-if="detailTo" class="text-decoration-none" :to="detailTo">
        {{ titleText }}
      </RouterLink>
      <span v-else>{{ titleText }}</span>
    </strong>
    <p class="meta-text mb-0">{{ book.authors_text || book.publisher || book.isbn13 || '책 정보' }}</p>
  </article>
</template>
