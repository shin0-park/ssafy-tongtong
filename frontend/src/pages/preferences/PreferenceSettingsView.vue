<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import EmptyState from '@/components/feedback/EmptyState.vue'
import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
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
  purposes: [],
  regions: [],
  facility_tags: [],
})

const purposeOptions = computed(() => normalizeOptions(options.value?.purposes ?? options.value?.purpose_options))
const regionOptions = computed(() => normalizeOptions(options.value?.regions ?? options.value?.region_options))
const facilityOptions = computed(() =>
  normalizeOptions(options.value?.facility_tags ?? options.value?.facility_options),
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
    }
  }).filter((item) => item.value)
}

function syncPreferences(preferences) {
  form.purposes = [...(preferences.purposes ?? preferences.purpose_codes ?? [])]
  form.regions = [...(preferences.regions ?? preferences.sigungu_codes ?? [])]
  form.facility_tags = [...(preferences.facility_tags ?? preferences.facility_tag_codes ?? [])]
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
      purposes: form.purposes,
      regions: form.regions,
      facility_tags: form.facility_tags,
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
      v-else-if="!purposeOptions.length && !regionOptions.length && !facilityOptions.length"
      title="선호 옵션이 아직 준비되지 않았어요."
      description="옵션 API가 준비되면 이 화면에서 선호를 설정할 수 있습니다."
    />
    <form v-else class="content-panel p-4" @submit.prevent="handleSubmit">
      <div v-if="errorMessage" class="alert alert-danger" role="alert">{{ errorMessage }}</div>
      <div v-if="savedMessage" class="alert alert-success" role="status">{{ savedMessage }}</div>

      <fieldset v-if="purposeOptions.length" class="preference-fieldset">
        <legend>방문 목적</legend>
        <label v-for="item in purposeOptions" :key="item.value" class="preference-option">
          <input v-model="form.purposes" class="form-check-input" type="checkbox" :value="item.value" />
          <span>{{ item.label }}</span>
        </label>
      </fieldset>

      <fieldset v-if="regionOptions.length" class="preference-fieldset">
        <legend>선호 지역</legend>
        <label v-for="item in regionOptions" :key="item.value" class="preference-option">
          <input v-model="form.regions" class="form-check-input" type="checkbox" :value="item.value" />
          <span>{{ item.label }}</span>
        </label>
      </fieldset>

      <fieldset v-if="facilityOptions.length" class="preference-fieldset">
        <legend>선호 시설</legend>
        <label v-for="item in facilityOptions" :key="item.value" class="preference-option">
          <input v-model="form.facility_tags" class="form-check-input" type="checkbox" :value="item.value" />
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
