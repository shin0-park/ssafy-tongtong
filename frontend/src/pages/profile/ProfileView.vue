<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const DEFAULT_PROFILE_IMAGE_URL = '/static/media_assets/placeholders/default_profile.png'

const isLoading = ref(false)
const error = ref(null)

async function loadProfile() {
  isLoading.value = true
  error.value = null

  try {
    await authStore.fetchCurrentUser()
  } catch (requestError) {
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <section class="page-shell">
    <LoadingState v-if="isLoading" title="프로필을 불러오는 중입니다." />
    <ErrorState
      v-else-if="error"
      title="프로필을 불러오지 못했습니다."
      :message="error.message"
      @retry="loadProfile"
    />

    <div v-else class="content-panel p-4">
      <div class="d-flex flex-wrap justify-content-between gap-3 mb-4">
        <div class="d-flex align-items-center gap-3">
          <ResponsiveImage
            class="profile-avatar"
            :src="authStore.user?.profile_image_url || DEFAULT_PROFILE_IMAGE_URL"
            :alt="authStore.user?.profile_image_alt || `${authStore.user?.nickname || '사용자'} 프로필 이미지`"
            fallback-label="기본 프로필 이미지"
          />
          <div>
          <h1 class="page-title">프로필</h1>
            <p class="page-subtitle">계정 정보와 공개 프로필을 확인합니다.</p>
          </div>
        </div>
        <div class="d-flex flex-wrap gap-2 align-self-start">
          <RouterLink class="btn btn-outline-primary" to="/preferences">선호 설정</RouterLink>
          <RouterLink class="btn btn-outline-primary" to="/profile/edit">수정</RouterLink>
        </div>
      </div>

      <dl class="row mb-0">
        <dt class="col-sm-3">이메일</dt>
        <dd class="col-sm-9">{{ authStore.user?.email || '-' }}</dd>
        <dt class="col-sm-3">닉네임</dt>
        <dd class="col-sm-9">{{ authStore.user?.nickname || '-' }}</dd>
        <dt class="col-sm-3">소개</dt>
        <dd class="col-sm-9">{{ authStore.user?.bio || '소개가 없습니다.' }}</dd>
        <dt class="col-sm-3">이미지 대체 텍스트</dt>
        <dd class="col-sm-9">{{ authStore.user?.profile_image_alt || '-' }}</dd>
      </dl>
    </div>
  </section>
</template>
