<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { searchBooks } from '@/services/bookService'
import { fetchPrograms } from '@/services/programService'
import { createReview, fetchReviewDetail, updateReview } from '@/services/reviewService'
import { extractErrorMessage, normalizeApiError } from '@/utils/apiError'
import {
  DEFAULT_MAX_IMAGE_SIZE_MB,
  buildMultipartPayload,
  findInvalidImage,
  hasFiles,
} from '@/utils/formData'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => route.name === 'review-edit')
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const fieldErrors = ref({})
const validationMessage = ref('')
const selectedImages = ref([])
const imagePreviews = ref([])
const relatedPrograms = ref([])
const isLoadingPrograms = ref(false)
const programErrorMessage = ref('')
const bookSearchQuery = ref('')
const bookSearchResults = ref([])
const isSearchingBooks = ref(false)
const bookSearchMessage = ref('')

const form = reactive({
  library_id: typeof route.query.library_id === 'string' ? route.query.library_id : '',
  content: '',
  tag_codes: '',
  book_ids: '',
  program_ids: '',
  replace_images: false,
})

const selectedProgramIds = computed(() => splitNumericValues(form.program_ids))
const selectedBookIds = computed(() => splitNumericValues(form.book_ids))

function splitValues(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function splitNumericValues(value) {
  return splitValues(value)
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item))
}

function buildPayload() {
  return {
    library_id: form.library_id ? Number(form.library_id) : null,
    content: form.content.trim(),
    tag_codes: splitValues(form.tag_codes),
    book_ids: splitNumericValues(form.book_ids),
    program_ids: splitNumericValues(form.program_ids),
  }
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

  const invalidImage = findInvalidImage(selectedImages.value)

  if (invalidImage && invalidImage.size > DEFAULT_MAX_IMAGE_SIZE_MB * 1024 * 1024) {
    return `이미지는 1장당 ${DEFAULT_MAX_IMAGE_SIZE_MB}MB 이하로 선택할 수 있어요.`
  }

  if (invalidImage) {
    return '이미지는 jpg, png, webp 형식만 사용할 수 있어요.'
  }

  return ''
}

function handleImageChange(event) {
  selectedImages.value = Array.from(event.target.files ?? [])
}

function setNumericSelection(fieldName, id, checked) {
  const values = new Set(splitNumericValues(form[fieldName]))

  if (checked) {
    values.add(Number(id))
  } else {
    values.delete(Number(id))
  }

  form[fieldName] = Array.from(values).join(', ')
}

function syncImagePreviews(files) {
  imagePreviews.value.forEach((item) => URL.revokeObjectURL(item.url))
  imagePreviews.value = files.map((file) => ({
    name: file.name,
    url: URL.createObjectURL(file),
  }))
}

function firstFieldError(fieldName) {
  const fieldError = fieldErrors.value?.[fieldName]

  if (Array.isArray(fieldError)) {
    return fieldError[0]
  }

  return fieldError || ''
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
    fieldErrors.value = normalizeApiError(error).fields ?? {}
  } finally {
    isLoading.value = false
  }
}

async function loadRelatedPrograms() {
  if (!form.library_id) {
    relatedPrograms.value = []
    return
  }

  isLoadingPrograms.value = true
  programErrorMessage.value = ''

  try {
    const data = await fetchPrograms({
      library_id: form.library_id,
      page_size: 6,
    })
    relatedPrograms.value = data.results ?? []
  } catch {
    relatedPrograms.value = []
    programErrorMessage.value = '관련 프로그램을 불러오지 못했어요.'
  } finally {
    isLoadingPrograms.value = false
  }
}

async function searchRelatedBooks() {
  const query = bookSearchQuery.value.trim()
  bookSearchMessage.value = ''
  bookSearchResults.value = []

  if (!query) {
    bookSearchMessage.value = '검색어를 입력해주세요.'
    return
  }

  isSearchingBooks.value = true

  try {
    const data = await searchBooks({
      search_type: 'keyword',
      q: query,
      page_size: 6,
    })
    bookSearchResults.value = data.results ?? []
    if (!bookSearchResults.value.length) {
      bookSearchMessage.value = '검색 결과가 없어요.'
    }
  } catch (error) {
    bookSearchMessage.value = extractErrorMessage(error, '책을 검색하지 못했어요.')
  } finally {
    isSearchingBooks.value = false
  }
}

async function handleSubmit() {
  validationMessage.value = validate()
  if (validationMessage.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''
  fieldErrors.value = {}

  try {
    const payload = buildPayload()
    const hasSelectedImages = hasFiles(selectedImages.value)
    const shouldSendMultipart = hasSelectedImages || (isEdit.value && form.replace_images)
    const requestBody = shouldSendMultipart
      ? buildMultipartPayload(
          {
            ...payload,
            replace_images: isEdit.value ? form.replace_images : undefined,
          },
          { images: selectedImages.value },
        )
      : payload

    const review = isEdit.value
      ? await updateReview(route.params.id, requestBody)
      : await createReview(requestBody)

    await router.push(`/reviews/${review.id ?? route.params.id}`)
  } catch (error) {
    const normalizedError = normalizeApiError(error)
    errorMessage.value = normalizedError.message || '후기를 저장하지 못했어요.'
    fieldErrors.value = normalizedError.fields ?? {}
  } finally {
    isSaving.value = false
  }
}

watch(selectedImages, syncImagePreviews)
watch(() => form.library_id, loadRelatedPrograms)

onMounted(async () => {
  await loadReview()
  await loadRelatedPrograms()
})

onBeforeUnmount(() => {
  imagePreviews.value.forEach((item) => URL.revokeObjectURL(item.url))
})
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
        <p v-if="firstFieldError('library_id')" class="field-error">
          {{ firstFieldError('library_id') }}
        </p>
      </label>

      <label class="form-field mb-3">
        <span>후기</span>
        <textarea v-model="form.content" class="form-control" rows="5" maxlength="200" required />
        <span class="meta-text">{{ form.content.trim().length }}/200</span>
        <p v-if="firstFieldError('content')" class="field-error">
          {{ firstFieldError('content') }}
        </p>
      </label>

      <label class="form-field mb-3">
        <span>태그 코드</span>
        <input v-model.trim="form.tag_codes" class="form-control" placeholder="review_quiet, review_kids" />
        <p v-if="firstFieldError('tag_codes')" class="field-error">
          {{ firstFieldError('tag_codes') }}
        </p>
      </label>

      <label class="form-field mb-3">
        <span>관련 책 ID</span>
        <input v-model.trim="form.book_ids" class="form-control" />
        <span class="meta-text">책 검색 결과에 내부 numeric id가 있을 때만 선택할 수 있어요.</span>
        <p v-if="firstFieldError('book_ids')" class="field-error">
          {{ firstFieldError('book_ids') }}
        </p>
      </label>

      <section class="content-panel-soft mb-3">
        <div class="d-flex gap-2">
          <input
            v-model.trim="bookSearchQuery"
            class="form-control"
            type="search"
            placeholder="관련 책 검색"
          />
          <button class="btn btn-outline-primary" type="button" :disabled="isSearchingBooks" @click="searchRelatedBooks">
            검색
          </button>
        </div>
        <p v-if="bookSearchMessage" class="meta-text mt-2 mb-0">{{ bookSearchMessage }}</p>
        <div v-if="bookSearchResults.length" class="selection-list mt-3">
          <label v-for="book in bookSearchResults" :key="book.id || book.isbn13" class="selection-row">
            <input
              class="form-check-input"
              type="checkbox"
              :disabled="!book.id"
              :checked="book.id ? selectedBookIds.includes(Number(book.id)) : false"
              @change="setNumericSelection('book_ids', book.id, $event.target.checked)"
            />
            <span>
              <strong>{{ book.title || '제목 정보 없음' }}</strong>
              <span class="meta-text d-block">
                {{ book.authors_text || '저자 정보 없음' }}
                <template v-if="!book.id"> · 내부 ID 없음</template>
              </span>
            </span>
          </label>
        </div>
      </section>

      <label class="form-field mb-3">
        <span>관련 프로그램 ID</span>
        <input v-model.trim="form.program_ids" class="form-control" />
        <p v-if="firstFieldError('program_ids')" class="field-error">
          {{ firstFieldError('program_ids') }}
        </p>
      </label>

      <section class="content-panel-soft mb-3">
        <p v-if="isLoadingPrograms" class="meta-text mb-0">관련 프로그램을 불러오는 중입니다.</p>
        <p v-else-if="programErrorMessage" class="meta-text mb-0">{{ programErrorMessage }}</p>
        <p v-else-if="!form.library_id" class="meta-text mb-0">도서관 ID를 입력하면 관련 프로그램을 선택할 수 있어요.</p>
        <p v-else-if="!relatedPrograms.length" class="meta-text mb-0">선택할 수 있는 관련 프로그램이 없어요.</p>
        <div v-else class="selection-list">
          <label v-for="program in relatedPrograms" :key="program.id" class="selection-row">
            <input
              class="form-check-input"
              type="checkbox"
              :checked="selectedProgramIds.includes(Number(program.id))"
              @change="setNumericSelection('program_ids', program.id, $event.target.checked)"
            />
            <span>
              <strong>{{ program.title || '프로그램명 정보 없음' }}</strong>
              <span class="meta-text d-block">
                {{ program.category_display || '분류 정보 없음' }}
              </span>
            </span>
          </label>
        </div>
      </section>

      <label class="form-field mb-3">
        <span>이미지</span>
        <input
          class="form-control"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          @change="handleImageChange"
        />
        <span class="meta-text">선택 {{ selectedImages.length }}장 / 최대 5장</span>
        <p v-if="firstFieldError('images')" class="field-error">
          {{ firstFieldError('images') }}
        </p>
      </label>

      <div v-if="imagePreviews.length" class="review-image-grid mb-3">
        <img
          v-for="image in imagePreviews"
          :key="image.url"
          class="review-image-preview"
          :src="image.url"
          :alt="`${image.name} 미리보기`"
        />
      </div>

      <label v-if="isEdit" class="form-check mb-4">
        <input v-model="form.replace_images" class="form-check-input" type="checkbox" />
        <span class="form-check-label">
          선택한 이미지로 기존 이미지를 교체
          <span v-if="form.replace_images && !selectedImages.length" class="meta-text d-block">
            새 이미지를 선택하지 않으면 기존 이미지가 모두 삭제됩니다.
          </span>
        </span>
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
