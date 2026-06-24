<script setup>
defineProps({
  book: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <article class="mini-card">
    <strong>{{ book.title || book.name || book.isbn13 || '관련 책' }}</strong>
    <p class="meta-text mb-0">{{ book.authors_text || book.publisher || book.isbn13 || '책 정보' }}</p>
  </article>
</template>
