<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import BookCard from '@/components/cards/BookCard.vue'
import LibraryCard from '@/components/cards/LibraryCard.vue'
import ProgramCard from '@/components/cards/ProgramCard.vue'
import ReviewCard from '@/components/cards/ReviewCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import ResultCount from '@/components/navigation/ResultCount.vue'
import {
  fetchLikedReviews,
  fetchMyReviews,
  fetchSavedBooks,
  fetchSavedLibraries,
  fetchSavedPrograms,
} from '@/services/myOutingsService'
import { extractErrorMessage } from '@/utils/apiError'
import { readPageQuery } from '@/utils/query'

const props = defineProps({
  kind: {
    type: String,
    required: true,
  },
})

const route = useRoute()
const router = useRouter()

const items = ref([])
const count = ref(0)
const isLoading = ref(false)
const errorMessage = ref('')

const page = computed(() => readPageQuery(route))
const pageSize = computed(() => Number(route.query.page_size) || 12)

const meta = computed(() => {
  const map = {
    libraries: {
      title: '저장한 도서관',
      label: '도서관',
      fetcher: fetchSavedLibraries,
      empty: '저장한 도서관이 없어요.',
    },
    books: {
      title: '저장한 책',
      label: '책',
      fetcher: fetchSavedBooks,
      empty: '저장한 책이 없어요.',
    },
    programs: {
      title: '저장한 프로그램',
      label: '프로그램',
      fetcher: fetchSavedPrograms,
      empty: '저장한 프로그램이 없어요.',
    },
    reviews: {
      title: '내가 쓴 후기',
      label: '후기',
      fetcher: fetchMyReviews,
      empty: '작성한 후기가 없어요.',
    },
    'liked-reviews': {
      title: '좋아요한 후기',
      label: '후기',
      fetcher: fetchLikedReviews,
      empty: '좋아요한 후기가 없어요.',
    },
  }

  return map[props.kind] ?? map.libraries
})

async function loadItems() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const data = await meta.value.fetcher({
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = data.results ?? []
    count.value = data.count ?? items.value.length
  } catch (error) {
    items.value = []
    count.value = 0
    errorMessage.value = extractErrorMessage(error, `${meta.value.title} 목록을 불러오지 못했어요.`)
  } finally {
    isLoading.value = false
  }
}

function goToPage(nextPage) {
  router.push({
    path: route.path,
    query: {
      ...route.query,
      page: nextPage,
    },
  })
}

watch(
  () => [props.kind, route.query],
  loadItems,
)

onMounted(loadItems)
</script>

<template>
  <section class="page-shell">
    <div class="page-header">
      <p class="eyebrow">나의 나들이</p>
      <h1>{{ meta.title }}</h1>
      <p class="page-description mb-0">저장과 활동 내역을 한곳에서 확인합니다.</p>
    </div>

    <div class="myoutings-nav mb-4">
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/dashboard">Dashboard</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/libraries">도서관</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/books">책</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/programs">프로그램</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/reviews">내 후기</RouterLink>
      <RouterLink class="btn btn-outline-primary btn-sm" to="/my-outings/liked-reviews">좋아요한 후기</RouterLink>
    </div>

    <LoadingState v-if="isLoading" :title="`${meta.title}을 불러오는 중입니다.`" />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadItems" />
    <EmptyState v-else-if="!items.length" :title="meta.empty" description="저장하거나 활동한 항목이 생기면 표시됩니다." />
    <template v-else>
      <ResultCount class="mb-3" :count="count" :label="meta.label" />
      <div v-if="kind === 'libraries'" class="responsive-card-grid">
        <LibraryCard v-for="item in items" :key="item.id" :library="item.library ?? item" />
      </div>
      <div v-else-if="kind === 'books'" class="responsive-card-grid">
        <BookCard v-for="item in items" :key="item.isbn13 || item.book?.isbn13" :book="item.book ?? item" />
      </div>
      <div v-else-if="kind === 'programs'" class="stack-list">
        <ProgramCard v-for="item in items" :key="item.id || item.program?.id" :program="item.program ?? item" />
      </div>
      <div v-else class="stack-list">
        <ReviewCard v-for="item in items" :key="item.id || item.review?.id" :review="item.review ?? item" />
      </div>
      <PaginationBar
        class="mt-4"
        :page="page"
        :page-size="pageSize"
        :total-count="count"
        @change="goToPage"
      />
    </template>
  </section>
</template>
