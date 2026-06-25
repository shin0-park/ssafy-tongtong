<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import BackLink from '@/components/navigation/BackLink.vue'
import {
  fetchMyPreferences,
  fetchPreferenceOptions,
  updateMyPreferences,
} from '@/services/preferenceService'
import { extractErrorMessage } from '@/utils/apiError'

const router = useRouter()

const options = ref(null)
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const savedMessage = ref('')

const form = reactive({
  purpose_codes: [],
  region_keys: [],
  tag_codes: [],
})

const purposeOptions = computed(() => normalizeOptions(options.value?.purposes ?? options.value?.purpose_options))
const regionOptions = computed(() => normalizeRegionOptions(options.value?.regions ?? options.value?.region_options))
const tagOptions = computed(() =>
  normalizeOptions(options.value?.tags ?? options.value?.facility_tags ?? options.value?.facility_options).filter(
    (item) => !item.group || item.group === 'facility',
  ),
)

function normalizeOptions(values) {
  if (!Array.isArray(values)) {
    return []
  }

  return values.map((item) => {
    if (typeof item === 'string') {
      return {
        value: item,
        label: item,
      }
    }

    return {
      value: item.code ?? item.value ?? item.id,
      label: item.label ?? item.name ?? item.code ?? item.value ?? item.id,
      group: item.tag_group,
    }
  }).filter((item) => item.value)
}

function normalizeRegionOptions(values) {
  if (!Array.isArray(values)) {
    return []
  }

  return values.map((item) => {
    if (typeof item === 'string') {
      return {
        value: item,
        label: item,
        payload: {
          sido: '부산광역시',
          sigungu: item,
        },
      }
    }

    const sido = item.sido || '부산광역시'
    const sigungu = item.sigungu || item.name || item.value

    return {
      value: item.region_key || `${sido}:${sigungu}`,
      label: [sido, sigungu].filter(Boolean).join(' '),
      payload: {
        sido,
        sigungu,
      },
    }
  }).filter((item) => item.value && item.payload.sigungu)
}

function syncPreferences(preferences) {
  form.purpose_codes = (preferences.purposes ?? preferences.purpose_codes ?? [])
    .map((purpose) => purpose.code ?? purpose)
    .filter(Boolean)
  form.region_keys = (preferences.regions ?? preferences.sigungu_codes ?? [])
    .map((region) => {
      if (typeof region === 'string') {
        return region
      }

      return region.region_key || `${region.sido || '부산광역시'}:${region.sigungu}`
    })
    .filter(Boolean)
  form.tag_codes = (preferences.tags ?? preferences.tag_codes ?? preferences.facility_tags ?? [])
    .map((tag) => tag.code ?? tag)
    .filter(Boolean)
}

function selectedRegionsPayload() {
  const optionMap = new Map(regionOptions.value.map((item) => [item.value, item.payload]))

  return form.region_keys
    .map((key) => optionMap.get(key))
    .filter(Boolean)
}

async function loadPreferences() {
  isLoading.value = true
  errorMessage.value = ''
  savedMessage.value = ''

  try {
    const [optionData, preferenceData] = await Promise.all([
      fetchPreferenceOptions(),
      fetchMyPreferences(),
    ])
    options.value = optionData
    syncPreferences(preferenceData)
  } catch (error) {
    options.value = null
    errorMessage.value = extractErrorMessage(error, '선호 설정을 불러오지 못했어요.')
  } finally {
    isLoading.value = false
  }
}

async function handleSubmit() {
  isSaving.value = true
  errorMessage.value = ''
  savedMessage.value = ''

  try {
    const data = await updateMyPreferences({
      purpose_codes: form.purpose_codes,
      regions: selectedRegionsPayload(),
      tag_codes: form.tag_codes,
    })
    syncPreferences(data)
    savedMessage.value = '선호 설정을 저장했어요.'
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '선호 설정을 저장하지 못했어요.')
  } finally {
    isSaving.value = false
  }
}

onMounted(loadPreferences)
</script>

<template>
  <section class="page-shell page-shell-narrow">
    <BackLink to="/my-outings/dashboard" label="나의 나들이 요약으로 돌아가기" />

    <div class="page-header">
      <p class="eyebrow">선호 설정</p>
      <h1>나에게 맞는 도서관 찾기</h1>
      <p class="page-description mb-0">
        직접 선택한 선호는 추천 조건으로 저장되고, 행동 기반 성향은 저장과 후기 활동을 바탕으로 따로 분석됩니다.
      </p>
    </div>

    <LoadingState v-if="isLoading" title="선호 설정을 불러오는 중입니다." />
    <ErrorState v-else-if="errorMessage && !options" :message="errorMessage" @retry="loadPreferences" />
    <EmptyState
      v-else-if="!purposeOptions.length && !regionOptions.length && !tagOptions.length"
      title="선호 옵션이 아직 준비되지 않았어요."
      description="옵션 API가 준비되면 이 화면에서 선호를 설정할 수 있습니다."
    />
    <form v-else class="content-panel p-4" @submit.prevent="handleSubmit">
      <div v-if="errorMessage" class="alert alert-danger" role="alert">{{ errorMessage }}</div>
      <div v-if="savedMessage" class="alert alert-success" role="status">{{ savedMessage }}</div>

      <fieldset v-if="purposeOptions.length" class="preference-fieldset">
        <legend>방문 목적</legend>
        <label v-for="item in purposeOptions" :key="item.value" class="preference-option">
          <input v-model="form.purpose_codes" class="form-check-input" type="checkbox" :value="item.value" />
          <span>{{ item.label }}</span>
        </label>
      </fieldset>

      <fieldset v-if="regionOptions.length" class="preference-fieldset">
        <legend>선호 지역</legend>
        <label v-for="item in regionOptions" :key="item.value" class="preference-option">
          <input v-model="form.region_keys" class="form-check-input" type="checkbox" :value="item.value" />
          <span>{{ item.label }}</span>
        </label>
      </fieldset>

      <fieldset v-if="tagOptions.length" class="preference-fieldset">
        <legend>선호 시설</legend>
        <label v-for="item in tagOptions" :key="item.value" class="preference-option">
          <input v-model="form.tag_codes" class="form-check-input" type="checkbox" :value="item.value" />
          <span>{{ item.label }}</span>
        </label>
      </fieldset>

      <div class="d-flex flex-wrap justify-content-end gap-2">
        <button class="btn btn-outline-secondary" type="button" @click="router.push('/my-outings/dashboard')">
          나중에
        </button>
        <button class="btn btn-primary" type="submit" :disabled="isSaving">
          {{ isSaving ? '저장 중' : '저장' }}
        </button>
      </div>
    </form>
  </section>
</template>
