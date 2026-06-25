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
import BackLink from '@/components/navigation/BackLink.vue'
import PaginationBar from '@/components/navigation/PaginationBar.vue'
import ResultCount from '@/components/navigation/ResultCount.vue'
import {
  fetchLikedReviews,
  fetchMyComments,
  fetchMyReviews,
  fetchSavedBooks,
  fetchSavedLibraries,
  fetchSavedPrograms,
} from '@/services/myOutingsService'
import { extractErrorMessage } from '@/utils/apiError'
import { formatDate } from '@/utils/display'
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

const pageQuery = computed(() => readPageQuery(route))
const page = computed(() => pageQuery.value.page)
const pageSize = computed(() => pageQuery.value.page_size || 12)
const reviewActivityTab = computed(() => (route.query.tab === 'comments' ? 'comments' : 'reviews'))

const meta = computed(() => {
  const map = {
    libraries: {
      title: '저장한 도서관',
      label: '곳',
      fetcher: fetchSavedLibraries,
      empty: '저장한 도서관이 없어요.',
      description: '마음에 드는 도서관을 저장하면 이곳에서 다시 볼 수 있어요.',
    },
    books: {
      title: '저장한 책',
      label: '권',
      fetcher: fetchSavedBooks,
      empty: '저장한 책이 없어요.',
      description: '관심 있는 책을 저장하면 이곳에서 다시 볼 수 있어요.',
    },
    programs: {
      title: '저장한 문화 프로그램',
      label: '개',
      fetcher: fetchSavedPrograms,
      empty: '저장한 문화 프로그램이 없어요.',
      description: '관심 있는 프로그램을 저장하면 이곳에서 다시 볼 수 있어요.',
    },
    reviews: {
      title: '내가 쓴 후기/댓글',
      label: '개',
      fetcher: reviewActivityTab.value === 'comments' ? fetchMyComments : fetchMyReviews,
      empty: reviewActivityTab.value === 'comments' ? '작성한 댓글이 없어요.' : '작성한 후기가 없어요.',
      description: '내가 남긴 후기와 댓글을 한곳에서 확인합니다.',
    },
    'liked-reviews': {
      title: '좋아요한 후기',
      label: '개',
      fetcher: fetchLikedReviews,
      empty: '좋아요한 후기가 없어요.',
      description: '공감한 후기를 다시 볼 수 있어요.',
    },
  }

  return map[props.kind] ?? map.libraries
})

function targetItem(item) {
  return item.library ?? item.book ?? item.program ?? item.review ?? item
}

function isCommentItem(item) {
  return props.kind === 'reviews' && reviewActivityTab.value === 'comments' && Boolean(item.review)
}

function itemKey(item, index) {
  const target = targetItem(item)
  return item.id || target.id || target.isbn13 || index
}

function itemMetaText(item) {
  const dateValue = item.saved_at || item.liked_at || item.created_at
  const parts = []

  if (item.memo) parts.push(item.memo)
  if (dateValue) parts.push(formatDate(dateValue))
  return parts.join(' · ')
}

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
    <BackLink to="/my-outings/dashboard" label="나의 나들이 요약으로 돌아가기" />

    <div class="page-header">
      <p class="eyebrow">나의 나들이</p>
      <h1 class="page-title">{{ meta.title }}</h1>
      <p class="page-description mb-0">{{ meta.description }}</p>
    </div>

    <div v-if="kind === 'reviews'" class="myoutings-nav mb-4" aria-label="내가 쓴 후기와 댓글 보기">
      <RouterLink
        class="btn btn-outline-primary btn-sm"
        :class="{ active: reviewActivityTab === 'reviews' }"
        :to="{ path: '/my-outings/reviews', query: { page: 1, page_size: pageSize !== 12 ? pageSize : undefined } }"
      >
        후기
      </RouterLink>
      <RouterLink
        class="btn btn-outline-primary btn-sm"
        :class="{ active: reviewActivityTab === 'comments' }"
        :to="{ path: '/my-outings/reviews', query: { tab: 'comments', page: 1, page_size: pageSize !== 12 ? pageSize : undefined } }"
      >
        댓글
      </RouterLink>
    </div>

    <LoadingState v-if="isLoading" :title="`${meta.title}을 불러오는 중입니다.`" />
    <ErrorState v-else-if="errorMessage" :message="errorMessage" @retry="loadItems" />
    <EmptyState v-else-if="!items.length" :title="meta.empty" :description="meta.description" />
    <template v-else>
      <ResultCount class="mb-3" :count="count" :label="meta.label" />
      <div v-if="kind === 'libraries'" class="responsive-card-grid">
        <div v-for="(item, index) in items" :key="itemKey(item, index)" class="saved-item-shell">
          <p v-if="itemMetaText(item)" class="meta-text mb-2">{{ itemMetaText(item) }}</p>
          <LibraryCard :library="targetItem(item)" />
        </div>
      </div>
      <div v-else-if="kind === 'books'" class="responsive-card-grid">
        <div v-for="(item, index) in items" :key="itemKey(item, index)" class="saved-item-shell">
          <p v-if="itemMetaText(item)" class="meta-text mb-2">{{ itemMetaText(item) }}</p>
          <BookCard :book="targetItem(item)" />
        </div>
      </div>
      <div v-else-if="kind === 'programs'" class="responsive-card-grid">
        <div v-for="(item, index) in items" :key="itemKey(item, index)" class="saved-item-shell">
          <p v-if="itemMetaText(item)" class="meta-text mb-2">{{ itemMetaText(item) }}</p>
          <ProgramCard :program="targetItem(item)" />
        </div>
      </div>
      <div v-else class="stack-list">
        <div v-for="(item, index) in items" :key="itemKey(item, index)" class="saved-item-shell">
          <p v-if="itemMetaText(item)" class="meta-text mb-2">{{ itemMetaText(item) }}</p>
          <div v-if="isCommentItem(item)" class="content-panel-soft p-3 mb-3">
            <p class="mb-2">{{ item.content }}</p>
            <p class="meta-text mb-0">댓글 작성 {{ formatDate(item.created_at) }}</p>
          </div>
          <ReviewCard :review="targetItem(item)" />
        </div>
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
