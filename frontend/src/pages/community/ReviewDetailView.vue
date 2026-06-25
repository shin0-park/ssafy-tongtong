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
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import {
  createReviewComment,
  deleteReview,
  deleteReviewComment,
  fetchReviewComments,
  fetchReviewDetail,
  updateReviewComment,
} from '@/services/reviewService'
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
const comments = ref([])
const commentCount = ref(0)
const commentPage = ref(1)
const commentPageSize = 20
const areCommentsLoading = ref(false)
const commentErrorMessage = ref('')
const newCommentContent = ref('')
const editingCommentId = ref(null)
const editingCommentContent = ref('')
const commentActionId = ref(null)
const isCommentSubmitting = ref(false)

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
const canSubmitComment = computed(() => Boolean(newCommentContent.value.trim()) && !isCommentSubmitting.value)

function tagLabel(tag) {
  return tag.review_label || tag.label || tag.name || labelFromMap(REVIEW_TAG_LABELS, tag.review_group || tag.code, tag.code)
}

function canEditComment(comment) {
  return Boolean(comment?.user?.id && user.value?.id && comment.user.id === user.value.id)
}

function syncReviewCommentCount(nextCount) {
  if (review.value) {
    review.value = {
      ...review.value,
      comment_count: nextCount,
    }
  }
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

async function loadComments(nextPage = commentPage.value) {
  if (!reviewId.value) return

  commentPage.value = nextPage
  areCommentsLoading.value = true
  commentErrorMessage.value = ''

  try {
    const data = await fetchReviewComments(reviewId.value, {
      page: commentPage.value,
      page_size: commentPageSize,
    })
    comments.value = data.results ?? []
    commentCount.value = data.count ?? comments.value.length
    syncReviewCommentCount(commentCount.value)
  } catch (error) {
    comments.value = []
    commentCount.value = 0
    commentErrorMessage.value = extractErrorMessage(error, '댓글을 불러오지 못했어요.')
  } finally {
    areCommentsLoading.value = false
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

async function handleCreateComment() {
  const content = newCommentContent.value.trim()
  if (!content) return

  isCommentSubmitting.value = true
  commentErrorMessage.value = ''

  try {
    await createReviewComment(reviewId.value, { content })
    newCommentContent.value = ''
    await loadComments(1)
  } catch (error) {
    commentErrorMessage.value = extractErrorMessage(error, '댓글을 등록하지 못했어요.')
  } finally {
    isCommentSubmitting.value = false
  }
}

function startEditComment(comment) {
  editingCommentId.value = comment.id
  editingCommentContent.value = comment.content ?? ''
}

function cancelEditComment() {
  editingCommentId.value = null
  editingCommentContent.value = ''
}

async function handleUpdateComment(comment) {
  const content = editingCommentContent.value.trim()
  if (!content) return

  commentActionId.value = comment.id
  commentErrorMessage.value = ''

  try {
    await updateReviewComment(reviewId.value, comment.id, { content })
    cancelEditComment()
    await loadComments(commentPage.value)
  } catch (error) {
    commentErrorMessage.value = extractErrorMessage(error, '댓글을 수정하지 못했어요.')
  } finally {
    commentActionId.value = null
  }
}

async function handleDeleteComment(comment) {
  if (!window.confirm('댓글을 삭제할까요?')) return

  commentActionId.value = comment.id
  commentErrorMessage.value = ''

  try {
    await deleteReviewComment(reviewId.value, comment.id)
    const nextPage = comments.value.length === 1 && commentPage.value > 1 ? commentPage.value - 1 : commentPage.value
    await loadComments(nextPage)
  } catch (error) {
    commentErrorMessage.value = extractErrorMessage(error, '댓글을 삭제하지 못했어요.')
  } finally {
    commentActionId.value = null
  }
}

async function loadPageData() {
  await loadReview()
  if (!notFound.value) {
    await loadComments(1)
  }
}

watch(reviewId, loadPageData)
onMounted(loadPageData)
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
            <p class="review-detail-library-line mb-2">
              <RouterLink v-if="library?.id" class="text-decoration-none" :to="`/libraries/${library.id}`">
                {{ library.name }}
              </RouterLink>
              <span v-else>{{ library?.name || '도서관 정보 없음' }}</span>
              <span class="meta-text">{{ library?.sigungu || library?.road_address || '위치 정보 없음' }}</span>
              <RouterLink v-if="library?.id" class="btn btn-outline-primary btn-sm" :to="`/libraries/${library.id}`">
                상세 보기
              </RouterLink>
            </p>
            <h2>{{ authorName }}님의 후기</h2>
            <div class="review-detail-meta">
              <span>작성 {{ formatDate(review.created_at) }}</span>
              <span v-if="review.updated_at && review.updated_at !== review.created_at">수정 {{ formatDate(review.updated_at) }}</span>
              <span>조회 {{ (review.view_count ?? 0).toLocaleString('ko-KR') }}</span>
              <span>댓글 {{ (review.comment_count ?? commentCount).toLocaleString('ko-KR') }}</span>
              <span
                v-for="tag in tags"
                :key="tag.code || tag.id || tag.name"
                class="review-detail-meta-chip"
              >
                {{ tagLabel(tag) }}
              </span>
            </div>
          </div>
          <LikeButton :review-id="review.id" :like-count="review.like_count ?? 0" />
        </header>

        <div class="review-detail-layout">
          <div class="review-detail-main">
            <p class="review-detail-content">{{ review.content || '후기 내용이 없습니다.' }}</p>

            <section v-if="books.length || programs.length" class="review-detail-section review-detail-related-section">
              <h3>관련 책과 프로그램</h3>
              <div class="related-mini-list">
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

      <section class="content-panel p-4 mt-4 review-comments-section">
        <div class="review-comments-header">
          <div>
            <h3>댓글</h3>
            <p class="meta-text mb-0">{{ commentCount.toLocaleString('ko-KR') }}개</p>
          </div>
          <button
            class="btn btn-outline-secondary btn-sm"
            type="button"
            :disabled="areCommentsLoading"
            @click="loadComments(commentPage)"
          >
            새로고침
          </button>
        </div>

        <form v-if="authStore.isAuthenticated" class="review-comment-form" @submit.prevent="handleCreateComment">
          <label class="form-field">
            <span>댓글 작성</span>
            <textarea
              v-model="newCommentContent"
              class="form-control"
              rows="3"
              maxlength="200"
              placeholder="후기에 댓글을 남겨보세요."
            />
          </label>
          <div class="review-comment-form-footer">
            <span class="meta-text">{{ newCommentContent.trim().length }}/200</span>
            <button class="btn btn-primary btn-sm" type="submit" :disabled="!canSubmitComment">
              {{ isCommentSubmitting ? '등록 중' : '등록' }}
            </button>
          </div>
        </form>
        <div v-else class="review-comment-login">
          <p class="mb-0">로그인하면 댓글을 남길 수 있어요.</p>
          <RouterLink
            class="btn btn-outline-primary btn-sm"
            :to="{ name: 'login', query: { redirect: route.fullPath } }"
          >
            로그인
          </RouterLink>
        </div>

        <div v-if="areCommentsLoading" class="review-comment-state" aria-live="polite" aria-busy="true">
          댓글을 불러오는 중입니다.
        </div>
        <div v-else-if="commentErrorMessage" class="review-comment-state" role="alert">
          <p class="mb-2">{{ commentErrorMessage }}</p>
          <button class="btn btn-outline-secondary btn-sm" type="button" @click="loadComments(commentPage)">
            다시 시도
          </button>
        </div>
        <div v-else-if="!comments.length" class="review-comment-state">
          아직 댓글이 없어요.
        </div>
        <div v-else class="review-comment-list">
          <article v-for="comment in comments" :key="comment.id" class="review-comment-item">
            <div class="review-comment-item-header">
              <div>
                <strong>{{ comment.user?.nickname || '익명' }}</strong>
                <span class="meta-text">작성 {{ formatDate(comment.created_at) }}</span>
                <span v-if="comment.updated_at && comment.updated_at !== comment.created_at" class="meta-text">
                  수정 {{ formatDate(comment.updated_at) }}
                </span>
              </div>
              <div v-if="canEditComment(comment)" class="review-comment-actions">
                <button
                  class="btn btn-outline-secondary btn-sm"
                  type="button"
                  :disabled="commentActionId === comment.id"
                  @click="startEditComment(comment)"
                >
                  수정
                </button>
                <button
                  class="btn btn-outline-danger btn-sm"
                  type="button"
                  :disabled="commentActionId === comment.id"
                  @click="handleDeleteComment(comment)"
                >
                  삭제
                </button>
              </div>
            </div>
            <form
              v-if="editingCommentId === comment.id"
              class="review-comment-edit-form"
              @submit.prevent="handleUpdateComment(comment)"
            >
              <textarea
                v-model="editingCommentContent"
                class="form-control"
                rows="3"
                maxlength="200"
              />
              <div class="review-comment-form-footer">
                <span class="meta-text">{{ editingCommentContent.trim().length }}/200</span>
                <div class="d-flex gap-2">
                  <button class="btn btn-outline-secondary btn-sm" type="button" @click="cancelEditComment">
                    취소
                  </button>
                  <button
                    class="btn btn-primary btn-sm"
                    type="submit"
                    :disabled="!editingCommentContent.trim() || commentActionId === comment.id"
                  >
                    저장
                  </button>
                </div>
              </div>
            </form>
            <p v-else class="review-comment-content">{{ comment.content }}</p>
          </article>
        </div>
        <PaginationBar
          v-if="commentCount > commentPageSize"
          class="mt-3"
          :page="commentPage"
          :page-size="commentPageSize"
          :total-count="commentCount"
          @change="loadComments"
        />
      </section>
    </template>
  </section>
</template>
