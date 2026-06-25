<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { searchBooks } from '@/services/bookService'
import { fetchLibraries } from '@/services/libraryService'
import { fetchPrograms } from '@/services/programService'
import { createReview, fetchReviewDetail, updateReview } from '@/services/reviewService'
import { useAuthStore } from '@/stores/auth'
import { extractErrorMessage, normalizeApiError } from '@/utils/apiError'
import { REVIEW_TAG_LABELS } from '@/utils/display'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const TAG_OPTIONS = [
  { code: 'review_quiet_study', label: REVIEW_TAG_LABELS.review_quiet_study },
  { code: 'review_seats_sufficient', label: REVIEW_TAG_LABELS.review_seats_sufficient },
  { code: 'review_comfortable_reading_space', label: REVIEW_TAG_LABELS.review_comfortable_reading_space },
  { code: 'review_comfortable_space', label: REVIEW_TAG_LABELS.review_comfortable_space },
  { code: 'review_clean_space', label: REVIEW_TAG_LABELS.review_clean_space },
  { code: 'review_books_diverse', label: REVIEW_TAG_LABELS.review_books_diverse },
  { code: 'review_easy_book_finding', label: REVIEW_TAG_LABELS.review_easy_book_finding },
  { code: 'review_good_programs', label: REVIEW_TAG_LABELS.review_good_programs },
  { code: 'review_children_friendly', label: REVIEW_TAG_LABELS.review_children_friendly },
  { code: 'review_parking_convenient', label: REVIEW_TAG_LABELS.review_parking_convenient },
  { code: 'review_wifi_reliable', label: REVIEW_TAG_LABELS.review_wifi_reliable },
  { code: 'review_kind_guidance', label: REVIEW_TAG_LABELS.review_kind_guidance },
  { code: 'review_well_managed', label: REVIEW_TAG_LABELS.review_well_managed },
]
const RELATED_BOOK_SEARCH_PAGE_SIZE = 100

const isEdit = computed(() => route.name === 'review-edit')
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const fieldErrors = ref({})
const validationMessage = ref('')
const librarySearchQuery = ref('')
const librarySearchResults = ref([])
const bookSearchQuery = ref('')
const bookSearchResults = ref([])
const bookSearchMessage = ref('')
const isBookSearching = ref(false)
const relatedPrograms = ref([])
const searchMessage = ref('')

const form = reactive({
  library_id: typeof route.query.library_id === 'string' ? route.query.library_id : '',
  library_name: '',
  content: '',
  tag_codes: [],
  book_ids: [],
  program_ids: [],
})

const selectedTagCount = computed(() => form.tag_codes.length)

function firstFieldError(fieldName) {
  const fieldError = fieldErrors.value?.[fieldName]
  if (Array.isArray(fieldError)) return fieldError[0]
  return fieldError || ''
}

function validate() {
  if (!form.library_id) return '도서관을 선택해주세요.'
  const contentLength = form.content.trim().length
  if (contentLength < 1 || contentLength > 200) return '후기는 1자 이상 200자 이하로 입력해주세요.'
  if (form.tag_codes.length < 1 || form.tag_codes.length > 5) return '태그는 1개 이상 5개 이하로 선택해주세요.'
  return ''
}

function buildPayload() {
  return {
    library_id: Number(form.library_id),
    content: form.content.trim(),
    tag_codes: [...form.tag_codes],
    book_ids: form.book_ids.map(Number).filter(Number.isFinite),
    program_ids: form.program_ids.map(Number).filter(Number.isFinite),
  }
}

async function searchLibraries() {
  searchMessage.value = ''
  librarySearchResults.value = []
  const query = librarySearchQuery.value.trim()
  if (!query) {
    searchMessage.value = '도서관명을 입력해주세요.'
    return
  }

  try {
    const data = await fetchLibraries({ q: query, page_size: 6 })
    librarySearchResults.value = data.results ?? []
    if (!librarySearchResults.value.length) searchMessage.value = '검색된 도서관이 없습니다.'
  } catch (error) {
    searchMessage.value = extractErrorMessage(error, '도서관을 검색하지 못했어요.')
  }
}

function selectLibrary(library) {
  form.library_id = String(library.id)
  form.library_name = library.name
  librarySearchQuery.value = library.name
  librarySearchResults.value = []
}

function normalizeBookSearchResults(data) {
  return (data.results ?? data.items ?? data.books ?? [])
    .map((item) => item.book ?? item)
    .filter(Boolean)
}

function mergeBookSearchResults(...resultGroups) {
  const seen = new Set()

  return resultGroups.flat().filter((book) => {
    const key = getBookSelectionValue(book) || book.title
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

async function searchRelatedBooks() {
  bookSearchMessage.value = ''
  bookSearchResults.value = []
  const query = bookSearchQuery.value.trim()
  if (!query) {
    bookSearchMessage.value = '책 검색어를 입력해주세요.'
    return
  }

  isBookSearching.value = true
  try {
    const titleData = await searchBooks({ search_type: 'title', q: query, page_size: RELATED_BOOK_SEARCH_PAGE_SIZE })
    const titleResults = normalizeBookSearchResults(titleData)
    let keywordResults = []

    if (!titleResults.length) {
      const keywordData = await searchBooks({ search_type: 'keyword', q: query, page_size: RELATED_BOOK_SEARCH_PAGE_SIZE })
      keywordResults = normalizeBookSearchResults(keywordData)
    }

    bookSearchResults.value = mergeBookSearchResults(titleResults, keywordResults)
    if (!bookSearchResults.value.length) bookSearchMessage.value = '검색된 책이 없습니다.'
  } catch (error) {
    bookSearchMessage.value = extractErrorMessage(error, '책을 검색하지 못했어요.')
  } finally {
    isBookSearching.value = false
  }
}

function toggleSelection(target, id, checked) {
  const value = Number(id)
  if (!Number.isFinite(value)) return
  const set = new Set(form[target])
  if (checked) set.add(value)
  else set.delete(value)
  form[target] = Array.from(set)
}

function getBookSelectionValue(book) {
  const value = Number(book?.local_book_id ?? book?.id)
  return Number.isFinite(value) ? value : null
}

function toggleBookSelection(book, checked) {
  const value = getBookSelectionValue(book)
  if (!value) return

  const set = new Set(form.book_ids)
  if (checked) set.add(value)
  else set.delete(value)
  form.book_ids = Array.from(set)
}

async function loadRelatedPrograms() {
  if (!form.library_id) {
    relatedPrograms.value = []
    return
  }
  try {
    const data = await fetchPrograms({ library_id: form.library_id, page_size: 8 })
    relatedPrograms.value = data.results ?? []
  } catch {
    relatedPrograms.value = []
  }
}

async function loadReview() {
  if (!isEdit.value) return

  isLoading.value = true
  errorMessage.value = ''

  try {
    const review = await fetchReviewDetail(route.params.id)
    if (review.user?.id && authStore.user?.id && review.user.id !== authStore.user.id) {
      await router.replace('/403')
      return
    }

    form.library_id = review.library?.id ? String(review.library.id) : ''
    form.library_name = review.library?.name || ''
    librarySearchQuery.value = form.library_name
    form.content = review.content || ''
    form.tag_codes = (review.tags ?? []).map((tag) => tag.code || tag.review_group).filter(Boolean).slice(0, 5)
    form.book_ids = (review.books ?? review.related_books ?? []).map(getBookSelectionValue).filter(Boolean)
    form.program_ids = (review.programs ?? review.related_programs ?? []).map((program) => Number(program.id)).filter(Number.isFinite)
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '후기 정보를 불러오지 못했어요.')
    fieldErrors.value = normalizeApiError(error).fields ?? {}
  } finally {
    isLoading.value = false
  }
}

async function handleSubmit() {
  validationMessage.value = validate()
  if (validationMessage.value) return

  isSaving.value = true
  errorMessage.value = ''
  fieldErrors.value = {}

  try {
    const review = isEdit.value
      ? await updateReview(route.params.id, buildPayload())
      : await createReview(buildPayload())
    await router.push(`/reviews/${review.id ?? route.params.id}`)
  } catch (error) {
    const normalizedError = normalizeApiError(error)
    errorMessage.value = normalizedError.message || '후기를 저장하지 못했어요.'
    fieldErrors.value = normalizedError.fields ?? {}
  } finally {
    isSaving.value = false
  }
}

watch(() => form.library_id, loadRelatedPrograms)
onMounted(async () => {
  await loadReview()
  await loadRelatedPrograms()
})
</script>

<template>
  <section class="page-shell page-shell-narrow">
    <div class="page-header">
      <p class="eyebrow">커뮤니티</p>
      <h1 class="page-title">{{ isEdit ? '후기 수정' : '후기 작성' }}</h1>
      <p class="page-description mb-0">
        도서관을 선택하고 200자 이내의 짧은 후기와 태그를 남겨주세요.
      </p>
    </div>

    <LoadingState v-if="isLoading" title="후기 정보를 불러오는 중입니다." />
    <ErrorState v-else-if="errorMessage && !isSaving && isEdit && !form.content" :message="errorMessage" @retry="loadReview" />

    <div v-else class="content-panel p-4">
      <div v-if="validationMessage" class="alert alert-warning" role="alert">{{ validationMessage }}</div>
      <div v-if="errorMessage" class="alert alert-danger" role="alert">{{ errorMessage }}</div>

      <section class="content-panel-soft mb-3">
        <label class="form-field mb-2">
          <span>도서관 선택</span>
          <div class="d-flex gap-2">
            <input
              v-model.trim="librarySearchQuery"
              class="form-control"
              type="search"
              placeholder="도서관명 검색"
              @keyup.enter="searchLibraries"
            />
            <button class="btn btn-outline-primary" type="button" @click="searchLibraries">검색</button>
          </div>
        </label>
        <p v-if="form.library_name" class="meta-text mb-2">선택됨: {{ form.library_name }}</p>
        <p v-if="firstFieldError('library_id')" class="field-error">{{ firstFieldError('library_id') }}</p>
        <div v-if="librarySearchResults.length" class="selection-list mt-3">
          <button
            v-for="library in librarySearchResults"
            :key="library.id"
            class="selection-row text-start"
            type="button"
            @click="selectLibrary(library)"
          >
            <span></span>
            <span>
              <strong>{{ library.name }}</strong>
              <span class="meta-text d-block">{{ library.sigungu }} · {{ library.road_address }}</span>
            </span>
          </button>
        </div>
      </section>

      <label class="form-field mb-3">
        <span>후기 본문</span>
        <textarea v-model="form.content" class="form-control" rows="5" maxlength="200" required />
        <span class="meta-text">{{ form.content.trim().length }}/200</span>
        <p v-if="firstFieldError('content')" class="field-error">{{ firstFieldError('content') }}</p>
      </label>

      <section class="mb-3">
        <p class="filter-group-title mb-2">후기 태그 {{ selectedTagCount }}/5</p>
        <div class="filter-chip-grid">
          <label v-for="tag in TAG_OPTIONS" :key="tag.code" class="filter-chip">
            <input v-model="form.tag_codes" type="checkbox" :value="tag.code" :disabled="!form.tag_codes.includes(tag.code) && selectedTagCount >= 5" />
            <span>{{ tag.label }}</span>
          </label>
        </div>
        <p v-if="firstFieldError('tag_codes')" class="field-error">{{ firstFieldError('tag_codes') }}</p>
      </section>

      <section class="content-panel-soft mb-3">
        <div class="d-flex gap-2">
          <input
            v-model.trim="bookSearchQuery"
            class="form-control"
            type="search"
            placeholder="관련 책 검색"
            @keydown.enter.prevent="searchRelatedBooks"
          />
          <button class="btn btn-outline-primary" type="button" :disabled="isBookSearching" @click="searchRelatedBooks">
            {{ isBookSearching ? '검색 중' : '검색' }}
          </button>
        </div>
        <p v-if="bookSearchMessage" class="meta-text mt-2 mb-0">{{ bookSearchMessage }}</p>
        <div v-if="bookSearchResults.length" class="selection-list selection-list-scroll mt-3">
          <label v-for="book in bookSearchResults" :key="book.local_book_id || book.id || book.isbn13" class="selection-row">
            <input
              class="form-check-input"
              type="checkbox"
              :disabled="getBookSelectionValue(book) === null"
              :checked="form.book_ids.includes(getBookSelectionValue(book))"
              @change="toggleBookSelection(book, $event.target.checked)"
            />
            <span>
              <strong>{{ book.title || '제목 정보 없음' }}</strong>
              <span class="meta-text d-block">{{ book.authors_text || '저자 정보 없음' }}</span>
            </span>
          </label>
        </div>
        <p v-if="firstFieldError('book_ids')" class="field-error">{{ firstFieldError('book_ids') }}</p>
      </section>

      <section class="content-panel-soft mb-4">
        <p class="filter-group-title mb-2">관련 프로그램</p>
        <p v-if="!form.library_id" class="meta-text mb-0">도서관을 선택하면 관련 프로그램을 고를 수 있어요.</p>
        <p v-else-if="!relatedPrograms.length" class="meta-text mb-0">선택 가능한 관련 프로그램이 없어요.</p>
        <div v-else class="selection-list">
          <label v-for="program in relatedPrograms" :key="program.id" class="selection-row">
            <input
              class="form-check-input"
              type="checkbox"
              :checked="form.program_ids.includes(Number(program.id))"
              @change="toggleSelection('program_ids', program.id, $event.target.checked)"
            />
            <span>
              <strong>{{ program.title || '프로그램명 정보 없음' }}</strong>
              <span class="meta-text d-block">{{ program.category_display || '분류 정보 없음' }}</span>
            </span>
          </label>
        </div>
      </section>

      <div class="d-flex flex-wrap justify-content-end gap-2">
        <RouterLink class="btn btn-outline-secondary" to="/community">취소</RouterLink>
        <button class="btn btn-primary" type="button" :disabled="isSaving" @click="handleSubmit">
          {{ isSaving ? '저장 중' : '저장' }}
        </button>
      </div>
    </div>
  </section>
</template>
