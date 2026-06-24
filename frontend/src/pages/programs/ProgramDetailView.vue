<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { fetchProgramDetail } from '@/services/programService'

const route = useRoute()

const program = ref(null)
const isLoading = ref(false)
const error = ref(null)

const libraryTo = computed(() =>
  program.value?.library?.id ? `/libraries/${program.value.library.id}` : null,
)
const regionText = computed(() =>
  [program.value?.source_sido, program.value?.source_sigungu || program.value?.library?.sigungu]
    .filter(Boolean)
    .join(' '),
)
const targetText = computed(() => {
  const targets = program.value?.target_display ?? []
  return targets.length ? targets.join(', ') : '정보 없음'
})

const errorTitle = computed(() => {
  if (error.value?.status === 404) {
    return '프로그램을 찾을 수 없어요.'
  }

  return '프로그램 정보를 불러오지 못했습니다.'
})

const errorMessage = computed(() => {
  if (error.value?.status === 404) {
    return '주소를 확인하거나 문화 프로그램 목록에서 다시 찾아보세요.'
  }

  return error.value?.message || '네트워크 상태를 확인한 뒤 다시 시도해주세요.'
})

function formatDate(value) {
  return value || '정보 없음'
}

function formatPeriod(startDate, endDate) {
  const startText = formatDate(startDate)
  const endText = formatDate(endDate)

  if (startText === '정보 없음' && endText === '정보 없음') {
    return '정보 없음'
  }

  return `${startText} ~ ${endText}`
}

function statusText(type, status) {
  if (!status) {
    return '정보 없음'
  }

  const labels = {
    application: {
      available: '신청 가능',
    },
    operation: {
      upcoming: '운영 예정',
    },
  }

  return labels[type]?.[status] || '상태 확인 필요'
}

function statusClass(type, status) {
  if (!status) {
    return 'status-badge status-badge-muted'
  }

  if (type === 'application' && status === 'available') {
    return 'status-badge status-badge-positive'
  }

  if (type === 'operation' && status === 'upcoming') {
    return 'status-badge status-badge-info'
  }

  return 'status-badge status-badge-muted'
}

async function loadProgram() {
  isLoading.value = true
  error.value = null

  try {
    program.value = await fetchProgramDetail(route.params.id)
  } catch (requestError) {
    program.value = null
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

watch(() => route.params.id, loadProgram)
onMounted(loadProgram)
</script>

<template>
  <section class="page-shell">
    <LoadingState v-if="isLoading" title="프로그램 정보를 불러오는 중입니다." />
    <ErrorState
      v-else-if="error"
      :title="errorTitle"
      :message="errorMessage"
      @retry="loadProgram"
    />
    <EmptyState v-else-if="!program" title="프로그램 정보가 없습니다." />

    <template v-else>
      <div class="content-panel p-4 mb-4">
        <p class="meta-text mb-1">{{ program.category_display || '분류 정보 없음' }}</p>
        <h1 class="page-title">{{ program.title || '프로그램명 정보 없음' }}</h1>
        <p class="page-subtitle mb-3">
          <RouterLink v-if="libraryTo" class="text-decoration-none" :to="libraryTo">
            {{ program.library.name }}
          </RouterLink>
          <span v-else>{{ program.source_library_name || program.library?.name || '운영 도서관 정보 없음' }}</span>
          <span v-if="regionText"> · {{ regionText }}</span>
        </p>

        <div class="d-flex flex-wrap gap-2 mb-3">
          <span class="book-chip">대상 {{ targetText }}</span>
          <span :class="statusClass('application', program.application_status)">
            {{ statusText('application', program.application_status) }}
          </span>
          <span :class="statusClass('operation', program.operation_status)">
            {{ statusText('operation', program.operation_status) }}
          </span>
        </div>

        <div class="d-flex flex-wrap gap-2">
          <a
            v-if="program.source_url"
            class="btn btn-outline-primary btn-sm"
            :href="program.source_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            원문에서 확인
          </a>
          <button class="btn btn-outline-secondary btn-sm" type="button" disabled>
            저장 준비 중
          </button>
        </div>
      </div>

      <div class="row g-4">
        <div class="col-lg-7">
          <section class="content-panel p-4">
            <h2 class="section-title">일정</h2>
            <dl class="row mb-0">
              <dt class="col-sm-4">신청 기간</dt>
              <dd class="col-sm-8">
                {{ formatPeriod(program.application_start_date, program.application_end_date) }}
              </dd>
              <dt class="col-sm-4">운영 기간</dt>
              <dd class="col-sm-8">
                {{ formatPeriod(program.operation_start_date, program.operation_end_date) }}
              </dd>
              <dt class="col-sm-4">신청 상태</dt>
              <dd class="col-sm-8">{{ statusText('application', program.application_status) }}</dd>
              <dt class="col-sm-4">운영 상태</dt>
              <dd class="col-sm-8">{{ statusText('operation', program.operation_status) }}</dd>
            </dl>
          </section>
        </div>

        <div class="col-lg-5">
          <section class="content-panel p-4">
            <h2 class="section-title">원천 정보</h2>
            <dl class="row mb-0">
              <dt class="col-sm-4">게시판</dt>
              <dd class="col-sm-8">{{ program.source_board || '정보 없음' }}</dd>
              <dt class="col-sm-4">게시일</dt>
              <dd class="col-sm-8">{{ formatDate(program.post_date) }}</dd>
              <dt class="col-sm-4">수집일</dt>
              <dd class="col-sm-8">{{ formatDate(program.collected_at) }}</dd>
              <dt class="col-sm-4">외부 키</dt>
              <dd class="col-sm-8">{{ program.external_program_key || '정보 없음' }}</dd>
            </dl>
          </section>
        </div>
      </div>
    </template>
  </section>
</template>
