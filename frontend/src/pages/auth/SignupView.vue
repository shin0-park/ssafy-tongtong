<script setup>
import { computed, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import ErrorState from '@/components/feedback/ErrorState.vue'
import { useAuthStore } from '@/stores/auth'
import { sanitizeInternalRedirect } from '@/utils/query'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  email: '',
  nickname: '',
  password: '',
})
const isSubmitting = ref(false)
const error = ref(null)

const fieldErrors = computed(() => error.value?.fields ?? {})
const redirectTarget = computed(() => sanitizeInternalRedirect(route.query.redirect, '/'))

function firstFieldError(fieldName) {
  const fieldError = fieldErrors.value[fieldName]
  return Array.isArray(fieldError) ? fieldError[0] : fieldError
}

async function submitSignup() {
  isSubmitting.value = true
  error.value = null

  try {
    await authStore.signup({
      email: form.email,
      nickname: form.nickname,
      password: form.password,
    })
    await router.replace(redirectTarget.value)
  } catch (requestError) {
    error.value = requestError
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="page-shell auth-page">
    <div class="auth-card content-panel p-4">
      <img class="auth-brand-mark" src="/brand/logo-wordmark-clean.png" alt="도서관 나들이" />
      <div class="mb-4">
        <h1 class="page-title">회원가입</h1>
        <p class="page-subtitle">이메일, 닉네임, 비밀번호로 계정을 만듭니다.</p>
      </div>

      <ErrorState
        v-if="error"
        class="mb-3"
        title="회원가입하지 못했습니다."
        :message="error.message"
        retry-label="다시 입력"
        @retry="error = null"
      />

      <form class="d-grid gap-3" @submit.prevent="submitSignup">
        <div>
          <label class="form-label" for="signup-email">이메일</label>
          <input
            id="signup-email"
            v-model.trim="form.email"
            class="form-control"
            type="email"
            autocomplete="email"
            required
          />
          <p v-if="firstFieldError('email')" class="field-error">{{ firstFieldError('email') }}</p>
        </div>

        <div>
          <label class="form-label" for="signup-nickname">닉네임</label>
          <input
            id="signup-nickname"
            v-model.trim="form.nickname"
            class="form-control"
            type="text"
            autocomplete="nickname"
            required
          />
          <p v-if="firstFieldError('nickname')" class="field-error">{{ firstFieldError('nickname') }}</p>
        </div>

        <div>
          <label class="form-label" for="signup-password">비밀번호</label>
          <input
            id="signup-password"
            v-model="form.password"
            class="form-control"
            type="password"
            autocomplete="new-password"
            required
          />
          <p v-if="firstFieldError('password')" class="field-error">{{ firstFieldError('password') }}</p>
        </div>

        <button class="btn btn-primary" type="submit" :disabled="isSubmitting">
          <span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>
          회원가입
        </button>
      </form>

      <p class="meta-text mt-4 mb-0">
        이미 계정이 있다면
        <RouterLink :to="{ name: 'login', query: { redirect: redirectTarget } }">로그인</RouterLink>
      </p>
    </div>
  </section>
</template>
