<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

import LikeButton from '@/components/actions/LikeButton.vue'
import RelatedBookMiniCard from '@/components/cards/RelatedBookMiniCard.vue'
import RelatedProgramMiniCard from '@/components/cards/RelatedProgramMiniCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import { deleteReview, fetchReviewDetail } from '@/services/reviewService'
import { useAuthStore } from '@/stores/auth'
import { extractErrorMessage } from '@/utils/apiError'
import { REVIEW_TAG_LABELS, formatDate, labelFromMap } from '@/utils/display'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { user } = storeToRefs(authStore)

const review = ref(null)
const isLoading = ref(false)
const isDeleting = ref(false)
const errorMessage = ref('')
const notFound = ref(false)

const reviewId = computed(() => route.params.id)
const authorName = computed(() => review.value?.user?.nickname || review.value?.author?.nickname || '익명')
const library = computed(() => review.value?.library ?? null)
const images = computed(() => review.value?.images ?? [])
const tags = computed(() => review.value?.tags ?? [])
const books = computed(() => review.value?.books ?? review.value?.related_books ?? [])
const programs = computed(() => review.value?.programs ?? review.value?.related_programs ?? [])
const canEdit = computed(() => {
  const ownerId = review.value?.user?.id ?? review.value?.author?.id
  return Boolean(ownerId && user.value?.id && ownerId === user.value.id)
})

function tagLabel(tag) {
  return tag.review_label || tag.label || tag.name || labelFromMap(REVIEW_TAG_LABELS, tag.review_group || tag.code, tag.code)
}

async function loadReview() {
  isLoading.value = true
  errorMessage.value = ''
  notFound.value = false

  try {
    review.value = await fetchReviewDetail(reviewId.value)
  } catch (error) {
    review.value = null
    if (error?.status === 404) {
      notFound.value = true
    } else {
      errorMessage.value = extractErrorMessage(error, '후기를 불러오지 못했어요.')
    }
  } finally {
    isLoading.value = false
  }
}

async function handleDelete() {
  if (!review.value || !window.confirm('후기를 삭제할까요?')) {
    return
  }

  isDeleting.value = true

  try {
    await deleteReview(review.value.id)
    await router.push('/community')
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '후기를 삭제하지 못했어요.')
  } finally {
    isDeleting.value = false
  }
}

watch(reviewId, loadReview)
onMounted(loadReview)
</script>

<template>
  <section class="page-shell">
    <div class="page-header">
      <p class="eyebrow">커뮤니티</p>
      <div class="d-flex flex-wrap align-items-end justify-content-between gap-3">
        <div>
          <h1>후기 상세</h1>
          <p class="page-description mb-0">도서관 경험과 연결된 책, 프로그램 정보를 확인합니다.</p>
        </div>
        <RouterLink class="btn btn-outline-secondary" to="/community">목록으로</RouterLink>
      </div>
    </div>

    <LoadingState v-if="isLoading" title="후기를 불러오는 중입니다." />
    <EmptyState
      v-else-if="notFound"
      title="후기를 찾을 수 없어요."
      description="삭제되었거나 접근할 수 없는 후기입니다."
    />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadReview" />
    <template v-else-if="review">
      <article class="review-detail-shell">
        <header class="review-detail-header">
          <div>
            <p class="eyebrow mb-2">
              <RouterLink v-if="library?.id" class="text-decoration-none" :to="`/libraries/${library.id}`">
                {{ library.name }}
              </RouterLink>
              <span v-else>{{ library?.name || '도서관 정보 없음' }}</span>
            </p>
            <h2>{{ authorName }}님의 후기</h2>
            <div class="review-detail-meta">
              <span>작성 {{ formatDate(review.created_at) }}</span>
              <span v-if="review.updated_at && review.updated_at !== review.created_at">수정 {{ formatDate(review.updated_at) }}</span>
              <span>조회 {{ (review.view_count ?? 0).toLocaleString('ko-KR') }}</span>
            </div>
          </div>
          <LikeButton :review-id="review.id" :like-count="review.like_count ?? 0" />
        </header>

        <div class="review-detail-layout">
          <div class="review-detail-main">
            <p class="review-detail-content">{{ review.content || '후기 내용이 없습니다.' }}</p>

            <section v-if="tags.length" class="review-detail-section">
              <h3>경험 태그</h3>
              <div class="chip-row">
                <span v-for="tag in tags" :key="tag.code || tag.id || tag.name" class="book-chip">
                  {{ tagLabel(tag) }}
                </span>
              </div>
            </section>

            <section v-if="books.length || programs.length" class="review-detail-section">
              <h3>관련 책과 프로그램</h3>
              <div class="related-mini-grid">
                <RelatedBookMiniCard v-for="book in books" :key="book.isbn13 || book.id" :book="book" />
                <RelatedProgramMiniCard v-for="program in programs" :key="program.id" :program="program" />
              </div>
            </section>
          </div>

          <aside class="review-detail-aside">
            <section v-if="images.length" class="review-detail-section">
              <h3>사진</h3>
              <div class="review-detail-image-grid">
                <ResponsiveImage
                  v-for="image in images"
                  :key="image.id || image.image_url || image.url"
                  class="review-detail-image"
                  :src="image.image_url || image.url"
                  :alt="image.alt_text || `${authorName} 후기 이미지`"
                />
              </div>
            </section>
            <section class="review-detail-section review-detail-library-box">
              <h3>도서관</h3>
              <p class="mb-2">{{ library?.name || '도서관 정보 없음' }}</p>
              <p class="meta-text mb-3">{{ library?.road_address || library?.sigungu || '위치 정보 없음' }}</p>
              <RouterLink v-if="library?.id" class="btn btn-outline-primary btn-sm" :to="`/libraries/${library.id}`">
                도서관 상세 보기
              </RouterLink>
            </section>
          </aside>
        </div>
      </article>

      <div class="d-flex flex-wrap justify-content-between gap-2 mt-3">
        <RouterLink class="btn btn-outline-secondary" to="/community">목록으로</RouterLink>
        <div v-if="canEdit" class="d-flex flex-wrap gap-2">
          <RouterLink class="btn btn-outline-primary" :to="`/reviews/${review.id}/edit`">수정</RouterLink>
          <button class="btn btn-outline-danger" type="button" :disabled="isDeleting" @click="handleDelete">
            {{ isDeleting ? '삭제 중' : '삭제' }}
          </button>
        </div>
      </div>
    </template>
  </section>
</template>
