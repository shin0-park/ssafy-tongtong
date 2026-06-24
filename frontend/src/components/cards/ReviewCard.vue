<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import LikeButton from '@/components/actions/LikeButton.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import RelatedBookMiniCard from '@/components/cards/RelatedBookMiniCard.vue'
import RelatedProgramMiniCard from '@/components/cards/RelatedProgramMiniCard.vue'

const props = defineProps({
  review: {
    type: Object,
    required: true,
  },
  detail: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['liked'])

const libraryTo = computed(() =>
  props.review.library?.id ? `/libraries/${props.review.library.id}` : null,
)
const authorName = computed(() => props.review.user?.nickname || props.review.author?.nickname || '익명')
const images = computed(() => props.review.images ?? [])
const tags = computed(() => props.review.tags ?? [])
const books = computed(() => props.review.books ?? props.review.related_books ?? [])
const programs = computed(() => props.review.programs ?? props.review.related_programs ?? [])

function formatDate(value) {
  if (!value) {
    return '정보 없음'
  }

  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value))
}
</script>

<template>
  <article class="review-card">
    <div class="review-card-header">
      <div>
        <p class="meta-text mb-1">
          <RouterLink v-if="libraryTo" class="text-decoration-none" :to="libraryTo">
            {{ review.library.name }}
          </RouterLink>
          <span v-else>{{ review.library?.name || '도서관 정보 없음' }}</span>
        </p>
        <h3 class="review-card-title">
          <RouterLink v-if="!detail" class="text-decoration-none" :to="`/reviews/${review.id}`">
            {{ authorName }}님의 후기
          </RouterLink>
          <span v-else>{{ authorName }}님의 후기</span>
        </h3>
      </div>
      <LikeButton
        v-if="review.id"
        :review-id="review.id"
        :like-count="review.like_count ?? 0"
        @updated="emit('liked', $event)"
      />
    </div>

    <p :class="detail ? 'review-content' : 'review-content review-content-clamp'">
      {{ review.content || '후기 내용이 없습니다.' }}
    </p>

    <div v-if="images.length" class="review-image-grid">
      <ResponsiveImage
        v-for="image in images"
        :key="image.id || image.image_url || image.url"
        class="review-image-thumb"
        :src="image.image_url || image.url"
        :alt="image.alt_text || `${authorName} 후기 이미지`"
      />
    </div>

    <div v-if="tags.length" class="d-flex flex-wrap gap-2">
      <span v-for="tag in tags" :key="tag.code || tag.id || tag.name" class="book-chip">
        {{ tag.label || tag.name || tag.code }}
      </span>
    </div>

    <div v-if="books.length || programs.length" class="related-mini-grid">
      <RelatedBookMiniCard v-for="book in books" :key="book.isbn13 || book.id" :book="book" />
      <RelatedProgramMiniCard v-for="program in programs" :key="program.id" :program="program" />
    </div>

    <footer class="review-card-footer">
      <span>조회 {{ (review.view_count ?? 0).toLocaleString() }}</span>
      <span>작성 {{ formatDate(review.created_at) }}</span>
    </footer>
  </article>
</template>
