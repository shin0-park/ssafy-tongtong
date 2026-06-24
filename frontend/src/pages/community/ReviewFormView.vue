<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { createReview, fetchReviewDetail, updateReview } from '@/services/reviewService'
import { extractErrorMessage } from '@/utils/apiError'
import { buildMultipartPayload, hasFiles } from '@/utils/formData'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => route.name === 'review-edit')
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const validationMessage = ref('')
const selectedImages = ref([])

const form = reactive({
  library_id: '',
  content: '',
  tag_codes: '',
  book_ids: '',
  program_ids: '',
  replace_images: false,
})

function splitValues(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function buildPayload() {
  const payload = {
    library_id: form.library_id ? Number(form.library_id) : null,
    content: form.content.trim(),
    tag_codes: splitValues(form.tag_codes),
    book_ids: splitValues(form.book_ids),
    program_ids: splitValues(form.program_ids),
  }

  if (isEdit.value) {
    payload.replace_images = form.replace_images
  }

  return payload
}

function validate() {
  if (!form.library_id) {
    return '도서관을 선택해주세요.'
  }

  const contentLength = form.content.trim().length
  if (contentLength < 1 || contentLength > 200) {
    return '후기는 1자 이상 200자 이하로 입력해주세요.'
  }

  const tagCount = splitValues(form.tag_codes).length
  if (tagCount < 1 || tagCount > 5) {
    return '태그는 1개 이상 5개 이하로 입력해주세요.'
  }

  if (selectedImages.value.length > 5) {
    return '이미지는 최대 5장까지 선택할 수 있어요.'
  }

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (selectedImages.value.some((file) => !allowedTypes.includes(file.type))) {
    return '이미지는 jpg, png, webp 형식만 사용할 수 있어요.'
  }

  return ''
}

function handleImageChange(event) {
  selectedImages.value = Array.from(event.target.files ?? [])
}

async function loadReview() {
  if (!isEdit.value) {
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const review = await fetchReviewDetail(route.params.id)
    form.library_id = review.library?.id ? String(review.library.id) : ''
    form.content = review.content || ''
    form.tag_codes = (review.tags ?? []).map((tag) => tag.code || tag.name).filter(Boolean).join(', ')
    form.book_ids = (review.books ?? review.related_books ?? [])
      .map((book) => book.id || book.isbn13)
      .filter(Boolean)
      .join(', ')
    form.program_ids = (review.programs ?? review.related_programs ?? [])
      .map((program) => program.id)
      .filter(Boolean)
      .join(', ')
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '후기 정보를 불러오지 못했어요.')
  } finally {
    isLoading.value = false
  }
}

async function handleSubmit() {
  validationMessage.value = validate()
  if (validationMessage.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    const payload = buildPayload()
    const hasSelectedImages = hasFiles(selectedImages.value)
    const requestBody = hasSelectedImages
      ? buildMultipartPayload(payload, { images: selectedImages.value })
      : payload

    const review = isEdit.value
      ? await updateReview(route.params.id, requestBody)
      : await createReview(requestBody)

    await router.push(`/reviews/${review.id ?? route.params.id}`)
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '후기를 저장하지 못했어요.')
  } finally {
    isSaving.value = false
  }
}

onMounted(loadReview)
</script>

<template>
  <section class="page-shell page-shell-narrow">
    <div class="page-header">
      <p class="eyebrow">커뮤니티</p>
      <h1>{{ isEdit ? '후기 수정' : '후기 작성' }}</h1>
      <p class="page-description mb-0">
        후기 본문, 태그, 관련 책과 프로그램을 API 계약 형식에 맞춰 저장합니다.
      </p>
    </div>

    <LoadingState v-if="isLoading" title="후기 정보를 불러오는 중입니다." />
    <ErrorState v-else-if="errorMessage && !isSaving" :message="errorMessage" @retry="loadReview" />

    <form v-else class="content-panel p-4" @submit.prevent="handleSubmit">
      <div v-if="validationMessage" class="alert alert-warning" role="alert">
        {{ validationMessage }}
      </div>
      <div v-if="errorMessage" class="alert alert-danger" role="alert">
        {{ errorMessage }}
      </div>

      <label class="form-field mb-3">
        <span>도서관 ID</span>
        <input v-model.trim="form.library_id" class="form-control" type="number" min="1" required />
      </label>

      <label class="form-field mb-3">
        <span>후기</span>
        <textarea v-model="form.content" class="form-control" rows="5" maxlength="200" required />
      </label>

      <label class="form-field mb-3">
        <span>태그 코드</span>
        <input v-model.trim="form.tag_codes" class="form-control" placeholder="review_quiet, review_kids" />
      </label>

      <label class="form-field mb-3">
        <span>관련 책 ID</span>
        <input v-model.trim="form.book_ids" class="form-control" />
      </label>

      <label class="form-field mb-3">
        <span>관련 프로그램 ID</span>
        <input v-model.trim="form.program_ids" class="form-control" />
      </label>

      <label class="form-field mb-3">
        <span>이미지</span>
        <input
          class="form-control"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          @change="handleImageChange"
        />
      </label>

      <label v-if="isEdit" class="form-check mb-4">
        <input v-model="form.replace_images" class="form-check-input" type="checkbox" />
        <span class="form-check-label">선택한 이미지로 기존 이미지를 교체</span>
      </label>

      <div class="d-flex flex-wrap justify-content-end gap-2">
        <RouterLink class="btn btn-outline-secondary" to="/community">취소</RouterLink>
        <button class="btn btn-primary" type="submit" :disabled="isSaving">
          {{ isSaving ? '저장 중' : '저장' }}
        </button>
      </div>
    </form>
  </section>
</template>
