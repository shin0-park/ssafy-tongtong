<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import BackLink from '@/components/navigation/BackLink.vue'
import { fetchProgramDetail } from '@/services/programService'
import {
  APPLICATION_STATUS_LABELS,
  OPERATION_STATUS_LABELS,
  PROGRAM_CATEGORY_LABELS,
  PROGRAM_TARGET_LABELS,
  labelFromMap,
  normalizeList,
} from '@/utils/display'

const route = useRoute()

const program = ref(null)
const isLoading = ref(false)
const error = ref(null)

const libraryTo = computed(() => (program.value?.library?.id ? `/libraries/${program.value.library.id}` : null))
const regionText = computed(() =>
  [program.value?.source_sido, program.value?.source_sigungu || program.value?.library?.sigungu].filter(Boolean).join(' '),
)
const categoryText = computed(() =>
  program.value?.category_display || labelFromMap(PROGRAM_CATEGORY_LABELS, program.value?.category_code, '프로그램'),
)
const targetText = computed(() => {
  const targets = program.value?.target_display ?? program.value?.target
  if (Array.isArray(targets) && targets.length) return targets.join(', ')
  if (typeof targets === 'string' && targets) return targets
  const labels = normalizeList(program.value?.target_codes).map((code) => labelFromMap(PROGRAM_TARGET_LABELS, code, code))
  return labels.length ? labels.join(', ') : '대상 정보 없음'
})
const applicationText = computed(() =>
  program.value?.application_status_display ||
  labelFromMap(APPLICATION_STATUS_LABELS, program.value?.application_status, '신청 정보 없음'),
)
const operationText = computed(() =>
  program.value?.operation_status_display ||
  labelFromMap(OPERATION_STATUS_LABELS, program.value?.operation_status, '운영 정보 없음'),
)
const errorTitle = computed(() =>
  error.value?.status === 404 ? '프로그램을 찾을 수 없어요.' : '프로그램 정보를 불러오지 못했습니다.',
)
const errorMessage = computed(() =>
  error.value?.status === 404
    ? '주소를 확인하거나 문화 프로그램 목록에서 다시 찾아보세요.'
    : error.value?.message || '네트워크 상태를 확인한 뒤 다시 시도해주세요.',
)

function formatDate(value) {
  return value || '정보 없음'
}

function formatPeriod(startDate, endDate) {
  if (!startDate && !endDate) return '기간 정보 없음'
  return `${formatDate(startDate)} ~ ${formatDate(endDate)}`
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
    <BackLink to="/programs" label="문화 프로그램 목록으로 돌아가기" />

    <LoadingState v-if="isLoading" title="프로그램 정보를 불러오는 중입니다." />
    <ErrorState v-else-if="error" :title="errorTitle" :message="errorMessage" @retry="loadProgram" />
    <EmptyState v-else-if="!program" title="프로그램 정보가 없습니다." />

    <template v-else>
      <section class="content-panel p-4 mb-4">
        <p class="meta-text mb-1">{{ categoryText }}</p>
        <h1 class="page-title">{{ program.title || '프로그램명 정보 없음' }}</h1>
        <p class="page-subtitle mb-3">
          <RouterLink v-if="libraryTo" class="text-decoration-none" :to="libraryTo">
            {{ program.library.name }}
          </RouterLink>
          <span v-else>{{ program.source_library_name || program.library?.name || '운영 도서관 정보 없음' }}</span>
          <span v-if="regionText"> · {{ regionText }}</span>
        </p>

        <div class="chip-row mb-3">
          <span class="status-badge status-badge-info">{{ categoryText }}</span>
          <span class="status-badge status-badge-positive">{{ applicationText }}</span>
          <span class="status-badge status-badge-muted">{{ operationText }}</span>
          <span class="book-chip">대상 {{ targetText }}</span>
        </div>

        <div class="d-flex flex-wrap gap-2">
          <a
            v-if="program.source_url"
            class="btn btn-outline-primary btn-sm"
            :href="program.source_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            원문 게시글 보기
          </a>
          <SaveButton resource-type="program" :resource-id="program.id" />
        </div>
      </section>

      <section class="content-panel p-4">
        <h2 class="section-title">운영/신청 정보</h2>
        <dl class="row mb-0">
          <dt class="col-sm-3">신청 기간</dt>
          <dd class="col-sm-9">{{ formatPeriod(program.application_start_date, program.application_end_date) }}</dd>
          <dt class="col-sm-3">운영 기간</dt>
          <dd class="col-sm-9">{{ formatPeriod(program.operation_start_date, program.operation_end_date) }}</dd>
          <dt class="col-sm-3">신청 상태</dt>
          <dd class="col-sm-9">{{ applicationText }}</dd>
          <dt class="col-sm-3">운영 상태</dt>
          <dd class="col-sm-9">{{ operationText }}</dd>
          <dt class="col-sm-3">신청 필요</dt>
          <dd class="col-sm-9">
            {{
              program.application_required === null || program.application_required === undefined
                ? '정보 없음'
                : program.application_required
                  ? '필요'
                  : '불필요'
            }}
          </dd>
          <dt class="col-sm-3">게시일</dt>
          <dd class="col-sm-9">{{ formatDate(program.post_date) }}</dd>
        </dl>
      </section>
    </template>
  </section>
</template>
