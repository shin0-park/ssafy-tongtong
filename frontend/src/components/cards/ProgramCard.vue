<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

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
const categoryText = computed(() => props.program.category_display || '분류 정보 없음')
const targetText = computed(() => {
  const targets = props.program.target_display ?? []
  return targets.length ? targets.join(', ') : '대상 정보 없음'
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
</script>

<template>
  <article class="program-card">
    <div class="program-card-main">
      <p class="meta-text mb-1">{{ categoryText }}</p>
      <h3 class="program-card-title">
        <RouterLink class="text-decoration-none" :to="detailTo">
          {{ program.title || '프로그램명 정보 없음' }}
        </RouterLink>
      </h3>

      <p class="meta-text mb-2">
        <RouterLink v-if="libraryTo" class="text-decoration-none" :to="libraryTo">
          {{ program.library.name }}
        </RouterLink>
        <span v-else>{{ program.library?.name || '운영 도서관 정보 없음' }}</span>
        <span v-if="program.library?.sigungu"> · {{ program.library.sigungu }}</span>
      </p>

      <div class="d-flex flex-wrap gap-2 mb-3">
        <span class="book-chip">{{ targetText }}</span>
        <span :class="statusClass('application', program.application_status)">
          {{ statusText('application', program.application_status) }}
        </span>
        <span :class="statusClass('operation', program.operation_status)">
          {{ statusText('operation', program.operation_status) }}
        </span>
      </div>

      <dl class="program-card-meta mb-0">
        <dt>신청 기간</dt>
        <dd>{{ formatPeriod(program.application_start_date, program.application_end_date) }}</dd>
        <dt>운영 기간</dt>
        <dd>{{ formatPeriod(program.operation_start_date, program.operation_end_date) }}</dd>
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
        원문 확인
      </a>
      <button class="btn btn-outline-secondary btn-sm" type="button" disabled>
        저장 준비 중
      </button>
    </div>
  </article>
</template>
