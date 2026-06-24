<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  nickname: '',
})
const isLoading = ref(false)
const isSubmitting = ref(false)
const error = ref(null)

const fieldErrors = computed(() => error.value?.fields ?? {})

function firstFieldError(fieldName) {
  const fieldError = fieldErrors.value[fieldName]
  return Array.isArray(fieldError) ? fieldError[0] : fieldError
}

async function loadProfile() {
  isLoading.value = true
  error.value = null

  try {
    const user = await authStore.fetchCurrentUser()
    form.nickname = user.nickname || ''
  } catch (requestError) {
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

async function submitProfile() {
  isSubmitting.value = true
  error.value = null

  try {
    await authStore.updateCurrentUser({
      nickname: form.nickname,
    })
    await router.replace('/profile')
  } catch (requestError) {
    error.value = requestError
  } finally {
    isSubmitting.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <section class="page-shell auth-page">
    <LoadingState v-if="isLoading" title="프로필을 불러오는 중입니다." />

    <div v-else class="auth-card content-panel p-4">
      <div class="mb-4">
        <h1 class="page-title">닉네임 수정</h1>
        <p class="page-subtitle">프로필에는 이메일과 닉네임만 사용합니다.</p>
      </div>

      <ErrorState
        v-if="error"
        class="mb-3"
        title="프로필을 저장하지 못했습니다."
        :message="error.message"
        retry-label="다시 입력"
        @retry="error = null"
      />

      <form class="d-grid gap-3" @submit.prevent="submitProfile">
        <div>
          <label class="form-label" for="profile-nickname">닉네임</label>
          <input
            id="profile-nickname"
            v-model.trim="form.nickname"
            class="form-control"
            type="text"
            autocomplete="nickname"
            required
          />
          <p v-if="firstFieldError('nickname')" class="field-error">{{ firstFieldError('nickname') }}</p>
        </div>

        <div class="d-flex gap-2">
          <button class="btn btn-primary" type="submit" :disabled="isSubmitting">
            <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>
            저장
          </button>
          <button class="btn btn-outline-secondary" type="button" @click="router.push('/profile')">
            취소
          </button>
        </div>
      </form>
    </div>
  </section>
</template>
