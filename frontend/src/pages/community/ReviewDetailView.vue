<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import ReviewCard from '@/components/cards/ReviewCard.vue'
import { deleteReview, fetchReviewDetail } from '@/services/reviewService'
import { useAuthStore } from '@/stores/auth'
import { extractErrorMessage } from '@/utils/apiError'

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
const canEdit = computed(() => {
  const ownerId = review.value?.user?.id ?? review.value?.author?.id
  return Boolean(ownerId && user.value?.id && ownerId === user.value.id)
})

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
      <ReviewCard :review="review" detail />
      <div v-if="canEdit" class="d-flex flex-wrap justify-content-end gap-2 mt-3">
        <RouterLink class="btn btn-outline-primary" :to="`/reviews/${review.id}/edit`">수정</RouterLink>
        <button class="btn btn-outline-danger" type="button" :disabled="isDeleting" @click="handleDelete">
          {{ isDeleting ? '삭제 중' : '삭제' }}
        </button>
      </div>
    </template>
  </section>
</template>
