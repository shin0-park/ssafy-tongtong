<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import SaveButton from '@/components/actions/SaveButton.vue'
import {
  APPLICATION_STATUS_LABELS,
  OPERATION_STATUS_LABELS,
  PROGRAM_CATEGORY_LABELS,
  PROGRAM_TARGET_LABELS,
  labelFromMap,
  normalizeList,
} from '@/utils/display'

const props = defineProps({
  program: {
    type: Object,
    required: true,
  },
})

const detailTo = computed(() => `/programs/${props.program.id}`)
const libraryTo = computed(() =>
  props.program.library?.id ? `/libraries/${props.program.library.id}` : null,
)
const categoryText = computed(() =>
  props.program.category_display ||
  labelFromMap(PROGRAM_CATEGORY_LABELS, props.program.category_code, '프로그램'),
)
const targetText = computed(() => {
  const display = props.program.target_display ?? props.program.target
  if (Array.isArray(display) && display.length) return display.join(', ')
  if (typeof display === 'string' && display) return display
  const labels = normalizeList(props.program.target_codes).map((code) =>
    labelFromMap(PROGRAM_TARGET_LABELS, code, code),
  )
  return labels.length ? labels.join(', ') : '대상 정보 없음'
})
const applicationText = computed(() =>
  props.program.application_status_display ||
  labelFromMap(APPLICATION_STATUS_LABELS, props.program.application_status, '신청 정보 없음'),
)
const operationText = computed(() =>
  props.program.operation_status_display ||
  labelFromMap(OPERATION_STATUS_LABELS, props.program.operation_status, '운영 정보 없음'),
)
const libraryName = computed(
  () => props.program.library?.name || props.program.source_library_name || '운영 도서관 정보 없음',
)

function formatDate(value) {
  return value || '정보 없음'
}

function formatPeriod(startDate, endDate) {
  if (!startDate && !endDate) return '기간 정보 없음'
  return [formatDate(startDate), formatDate(endDate)].join(' ~ ')
}
</script>

<template>
  <article class="program-card">
    <div class="program-card-main">
      <div class="d-flex flex-wrap gap-2 mb-2">
        <span class="status-badge status-badge-info">{{ categoryText }}</span>
        <span class="status-badge status-badge-positive">{{ applicationText }}</span>
        <span class="status-badge status-badge-muted">{{ operationText }}</span>
      </div>

      <h3 class="program-card-title">
        <RouterLink class="text-decoration-none" :to="detailTo">
          {{ program.title || '프로그램명 정보 없음' }}
        </RouterLink>
      </h3>

      <p class="meta-text mb-2">
        <RouterLink v-if="libraryTo" class="text-decoration-none" :to="libraryTo">
          {{ libraryName }}
        </RouterLink>
        <span v-else>{{ libraryName }}</span>
        <span v-if="program.library?.sigungu"> · {{ program.library.sigungu }}</span>
      </p>

      <dl class="program-card-meta mb-0">
        <dt>운영 기간</dt>
        <dd>{{ formatPeriod(program.operation_start_date, program.operation_end_date) }}</dd>
        <dt>대상</dt>
        <dd>{{ targetText }}</dd>
      </dl>
    </div>

    <div class="program-card-actions">
      <a
        v-if="program.source_url"
        class="btn btn-outline-primary btn-sm"
        :href="program.source_url"
        target="_blank"
        rel="noopener noreferrer"
      >
        원문 보기
      </a>
      <RouterLink v-if="libraryTo" class="btn btn-outline-secondary btn-sm" :to="libraryTo">
        도서관 보기
      </RouterLink>
      <SaveButton v-if="program.id" resource-type="program" :resource-id="program.id" />
    </div>
  </article>
</template>
