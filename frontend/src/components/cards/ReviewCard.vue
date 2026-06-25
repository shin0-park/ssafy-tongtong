<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import LikeButton from '@/components/actions/LikeButton.vue'
import RelatedBookMiniCard from '@/components/cards/RelatedBookMiniCard.vue'
import RelatedProgramMiniCard from '@/components/cards/RelatedProgramMiniCard.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import { REVIEW_TAG_LABELS, formatDate, labelFromMap } from '@/utils/display'

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
const previewImages = computed(() => images.value.slice(0, 3))
const hiddenImageCount = computed(() => Math.max(images.value.length - previewImages.value.length, 0))
const tags = computed(() => props.review.tags ?? [])
const books = computed(() => props.review.books ?? props.review.related_books ?? [])
const programs = computed(() => props.review.programs ?? props.review.related_programs ?? [])
const updatedDateText = computed(() => {
  if (!props.detail || !props.review.updated_at || props.review.updated_at === props.review.created_at) {
    return ''
  }

  return formatDate(props.review.updated_at)
})
const contentPreview = computed(() => {
  const content = (props.review.content || '후기 내용이 없습니다.').replace(/\s+/g, ' ').trim()
  return content.length > 96 ? `${content.slice(0, 96)}...` : content
})

function tagLabel(tag) {
  return tag.review_label || tag.label || tag.name || labelFromMap(REVIEW_TAG_LABELS, tag.review_group || tag.code, tag.code)
}
</script>

<template>
  <article class="review-card">
    <div class="review-card-header">
      <div>
        <p class="review-card-context mb-1">
          <RouterLink v-if="libraryTo" class="text-decoration-none" :to="libraryTo">
            {{ review.library.name }}
          </RouterLink>
          <span v-else>{{ review.library?.name || '도서관 정보 없음' }}</span>
          <span>{{ authorName }}</span>
          <span>작성 {{ formatDate(review.created_at) }}</span>
        </p>
        <h3 class="review-card-title">
          <RouterLink v-if="!detail" class="text-decoration-none" :to="`/reviews/${review.id}`">
            {{ contentPreview }}
          </RouterLink>
          <span v-else>{{ contentPreview }}</span>
        </h3>
      </div>
    </div>

    <p v-if="detail" class="review-content">
      {{ review.content || '후기 내용이 없습니다.' }}
    </p>

    <div v-if="previewImages.length" class="review-image-strip">
      <ResponsiveImage
        v-for="image in previewImages"
        :key="image.id || image.image_url || image.url"
        class="review-image-thumb"
        :src="image.image_url || image.url"
        :alt="image.alt_text || `${authorName} 후기 이미지`"
      />
      <span v-if="hiddenImageCount" class="review-image-more">+{{ hiddenImageCount }}</span>
    </div>

    <div v-if="tags.length" class="chip-row">
      <span v-for="tag in tags" :key="tag.code || tag.id || tag.name" class="book-chip">
        {{ tagLabel(tag) }}
      </span>
    </div>

    <div v-if="books.length || programs.length" class="review-card-related">
      <RelatedBookMiniCard v-for="book in books" :key="book.isbn13 || book.id" :book="book" />
      <RelatedProgramMiniCard v-for="program in programs" :key="program.id" :program="program" />
    </div>

    <footer class="review-card-footer">
      <div class="review-card-stats">
        <span>조회 {{ (review.view_count ?? 0).toLocaleString('ko-KR') }}</span>
        <span>댓글 {{ (review.comment_count ?? 0).toLocaleString('ko-KR') }}</span>
        <span v-if="updatedDateText">수정 {{ updatedDateText }}</span>
      </div>
      <LikeButton
        v-if="review.id"
        :review-id="review.id"
        :like-count="review.like_count ?? 0"
        @updated="emit('liked', $event)"
      />
    </footer>
  </article>
</template>
