<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'
import ExternalLibraryCard from '@/components/cards/ExternalLibraryCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import { fetchBookDetail, fetchBookLibraries } from '@/services/bookService'
import { formatNumber } from '@/utils/display'
import { readPageQuery } from '@/utils/query'

const route = useRoute()
const router = useRouter()
const DEFAULT_PAGE_SIZE = 20

const book = ref(null)
const holdings = ref([])
const holdingsMeta = ref({ count: 0, page: 1, page_size: DEFAULT_PAGE_SIZE })
const isBookLoading = ref(false)
const isHoldingsLoading = ref(false)
const bookError = ref(null)
const holdingsError = ref(null)

const isbn13 = computed(() => route.params.isbn13)
const publicationText = computed(() =>
  [book.value?.publisher, book.value?.publication_year || book.value?.publication_date].filter(Boolean).join(' · '),
)
const kdcText = computed(() => [book.value?.kdc_class_name, book.value?.kdc_class_no].filter(Boolean).join(' '))
const hasHoldings = computed(() => holdings.value.length > 0)
const matchedHoldings = computed(() => holdings.value.filter((holding) => holding.matched))
const unmatchedHoldings = computed(() => holdings.value.filter((holding) => !holding.matched))
const holdingsPage = computed(() => holdingsMeta.value.page || 1)
const holdingsPageSize = computed(() => holdingsMeta.value.page_size || DEFAULT_PAGE_SIZE)
const hasPreviousHoldingsPage = computed(() => holdingsPage.value > 1)
const hasNextHoldingsPage = computed(() => holdingsPage.value * holdingsPageSize.value < holdingsMeta.value.count)
const bookErrorTitle = computed(() =>
  bookError.value?.status === 404 ? '상세 정보가 아직 등록되지 않았습니다.' : '책 상세 정보를 불러오지 못했습니다.',
)
const bookErrorMessage = computed(() =>
  bookError.value?.status === 404
    ? '검색 결과로 돌아가 다른 책을 확인해보세요.'
    : bookError.value?.message || '네트워크 상태를 확인한 뒤 다시 시도해주세요.',
)

function isData4LibraryConfigError(requestError) {
  return requestError?.status === 503 && typeof requestError.message === 'string' && requestError.message.includes('Data4Library API key')
}

function holdingStatusText(holding) {
  if (holding?.loan_available === true) return '대출 가능'
  if (holding?.loan_available === false) return '대출 불가'
  return '대출 상태 미제공'
}

async function loadBook() {
  isBookLoading.value = true
  bookError.value = null

  try {
    book.value = await fetchBookDetail(isbn13.value)
  } catch (requestError) {
    book.value = null
    bookError.value = requestError
  } finally {
    isBookLoading.value = false
  }
}

async function loadHoldings() {
  isHoldingsLoading.value = true
  holdingsError.value = null

  try {
    const pageQuery = readPageQuery(route)
    const data = await fetchBookLibraries(isbn13.value, {
      page: pageQuery.page,
      page_size: pageQuery.page_size || DEFAULT_PAGE_SIZE,
    })
    holdings.value = data.results ?? []
    holdingsMeta.value = {
      count: data.count ?? 0,
      page: data.page ?? pageQuery.page,
      page_size: data.page_size ?? DEFAULT_PAGE_SIZE,
    }
  } catch (requestError) {
    holdings.value = []
    holdingsError.value = requestError
  } finally {
    isHoldingsLoading.value = false
  }
}

function loadPage() {
  loadBook()
  loadHoldings()
}

function goToHoldingsPage(page) {
  router.push({
    name: 'book-detail',
    params: { isbn13: isbn13.value },
    query: { ...route.query, page },
  })
}

watch(() => route.params.isbn13, loadPage)
watch(() => route.query, loadHoldings)
onMounted(loadPage)
</script>

<template>
  <section class="page-shell">
    <LoadingState v-if="isBookLoading" title="책 상세 정보를 불러오는 중입니다." />
    <ErrorState
      v-else-if="bookError"
      :title="bookErrorTitle"
      :message="bookErrorMessage"
      retry-label="다시 시도"
      @retry="loadPage"
    />
    <EmptyState v-else-if="!book" title="책 정보가 없습니다." />

    <template v-else>
      <div class="book-detail-layout mb-4">
        <div class="book-detail-cover">
          <ResponsiveImage :src="book.cover_image_url" :alt="`${book.title} 표지`" fallback-label="표지 없음" />
        </div>

        <div class="book-detail-main">
          <p class="meta-text mb-1">ISBN {{ book.isbn13 }}</p>
          <h1 class="page-title">{{ book.title || '제목 정보 없음' }}</h1>
          <p class="page-subtitle mb-3">{{ book.authors_text || '저자 정보 없음' }}</p>

          <dl class="row mb-3">
            <dt class="col-sm-3">출판 정보</dt>
            <dd class="col-sm-9">{{ publicationText || '출판 정보 없음' }}</dd>
            <dt class="col-sm-3">KDC</dt>
            <dd class="col-sm-9">{{ kdcText || '분류 정보 없음' }}</dd>
            <dt v-if="book.loan_count !== null && book.loan_count !== undefined" class="col-sm-3">대출 수</dt>
            <dd v-if="book.loan_count !== null && book.loan_count !== undefined" class="col-sm-9">
              {{ formatNumber(book.loan_count) }}회
            </dd>
          </dl>

          <p v-if="book.description" class="mb-3">{{ book.description }}</p>

          <div v-if="book.tags?.length" class="chip-row mb-3">
            <span v-for="tag in book.tags" :key="tag.code || tag.id || tag.name" class="book-chip">
              {{ tag.label || tag.name || tag.code }}
            </span>
          </div>

          <div class="d-flex flex-wrap gap-2">
            <a
              v-if="book.source_detail_url"
              class="btn btn-outline-primary btn-sm"
              :href="book.source_detail_url"
              target="_blank"
              rel="noopener"
            >
              원천 상세 보기
            </a>
            <SaveButton resource-type="book" :resource-id="book.isbn13" />
          </div>
        </div>
      </div>

      <section class="content-panel p-4">
        <div class="section-header-row">
          <div>
            <h2 class="section-title mb-1">이 책을 보유한 도서관</h2>
            <p class="meta-text mb-0">정보나루 기준 소장 도서관과 서비스 매칭 상태를 표시합니다.</p>
          </div>
          <p v-if="holdingsMeta.count" class="meta-text mb-0">총 {{ holdingsMeta.count.toLocaleString('ko-KR') }}곳</p>
        </div>

        <LoadingState v-if="isHoldingsLoading" title="소장 도서관을 불러오는 중입니다." />
        <ErrorState
          v-else-if="holdingsError"
          :title="isData4LibraryConfigError(holdingsError) ? '정보나루 설정이 필요합니다.' : '소장 도서관을 불러오지 못했습니다.'"
          :message="isData4LibraryConfigError(holdingsError) ? 'API Key 설정이 완료되면 소장 도서관 조회를 사용할 수 있습니다.' : holdingsError.message"
          @retry="loadHoldings"
        />
        <EmptyState v-else-if="!hasHoldings" title="소장 도서관이 없습니다." />

        <template v-else>
          <div class="d-grid gap-3">
            <article
              v-for="(item, index) in matchedHoldings"
              :key="item.library?.id || item.external_library?.external_library_key || index"
              class="holding-card"
            >
              <div>
                <p class="meta-text mb-1">서비스 도서관과 연결됨</p>
                <h3 class="h5 mb-2">
                  <RouterLink v-if="item.library?.id" class="text-decoration-none" :to="`/libraries/${item.library.id}`">
                    {{ item.library.name }}
                  </RouterLink>
                  <span v-else>{{ item.external_library?.name || '도서관명 없음' }}</span>
                </h3>
                <p class="meta-text mb-2">{{ item.library?.road_address || item.external_library?.address || '주소 정보 없음' }}</p>
                <div class="chip-row">
                  <span class="book-chip">{{ holdingStatusText(item.holding) }}</span>
                  <span v-if="item.holding?.call_number" class="book-chip">청구기호 {{ item.holding.call_number }}</span>
                  <span v-if="item.holding?.loan_status" class="book-chip">{{ item.holding.loan_status }}</span>
                </div>
              </div>
            </article>
            <ExternalLibraryCard
              v-for="(item, index) in unmatchedHoldings"
              :key="item.external_library?.external_library_key || `external-${index}`"
              :library="item.external_library ?? {}"
              :holding="item.holding"
            />
          </div>

          <PaginationBar
            :current-page="holdingsPage"
            :has-previous="hasPreviousHoldingsPage"
            :has-next="hasNextHoldingsPage"
            @change="goToHoldingsPage"
          />
        </template>
      </section>
    </template>
  </section>
</template>
