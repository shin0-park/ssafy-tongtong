<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import ErrorState from '@/components/feedback/ErrorState.vue'
import LoadingState from '@/components/feedback/LoadingState.vue'
import ResponsiveImage from '@/components/media/ResponsiveImage.vue'
import { useAuthStore } from '@/stores/auth'
import {
  DEFAULT_MAX_IMAGE_SIZE_MB,
  buildMultipartPayload,
  findInvalidImage,
  hasFiles,
} from '@/utils/formData'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  nickname: '',
  bio: '',
  profile_image_alt: '',
  remove_profile_image: false,
})
const selectedImage = ref(null)
const selectedImagePreview = ref('')
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
    form.bio = user.bio || ''
    form.profile_image_alt = user.profile_image_alt || ''
  } catch (requestError) {
    error.value = requestError
  } finally {
    isLoading.value = false
  }
}

function handleImageChange(event) {
  selectedImage.value = event.target.files?.[0] ?? null
}

function revokeSelectedImagePreview() {
  if (selectedImagePreview.value) {
    URL.revokeObjectURL(selectedImagePreview.value)
    selectedImagePreview.value = ''
  }
}

function validateImage() {
  if (!selectedImage.value) {
    return ''
  }

  const invalidImage = findInvalidImage(selectedImage.value)

  if (invalidImage && invalidImage.size > DEFAULT_MAX_IMAGE_SIZE_MB * 1024 * 1024) {
    return `프로필 이미지는 ${DEFAULT_MAX_IMAGE_SIZE_MB}MB 이하로 선택할 수 있어요.`
  }

  return invalidImage ? '프로필 이미지는 jpg, png, webp 형식만 사용할 수 있어요.' : ''
}

async function submitProfile() {
  isSubmitting.value = true
  error.value = null

  try {
    const imageError = validateImage()
    if (imageError) {
      throw {
        message: imageError,
        fields: {
          profile_image: imageError,
        },
      }
    }

    const payload = {
      nickname: form.nickname,
      bio: form.bio,
      profile_image_alt: form.profile_image_alt,
      remove_profile_image: form.remove_profile_image,
    }

    const requestBody = hasFiles([selectedImage.value])
      ? buildMultipartPayload(payload, { profile_image: selectedImage.value })
      : payload

    await authStore.updateCurrentUserProfile(requestBody)
    await router.replace('/profile')
  } catch (requestError) {
    error.value = requestError
  } finally {
    isSubmitting.value = false
  }
}

watch(selectedImage, (file) => {
  revokeSelectedImagePreview()

  if (file) {
    selectedImagePreview.value = URL.createObjectURL(file)
  }
})

onMounted(loadProfile)
onBeforeUnmount(revokeSelectedImagePreview)
</script>

<template>
  <section class="page-shell auth-page">
    <LoadingState v-if="isLoading" title="프로필을 불러오는 중입니다." />

    <div v-else class="auth-card content-panel p-4">
      <div class="mb-4">
        <h1 class="page-title">프로필 수정</h1>
        <p class="page-subtitle">닉네임, 소개, 프로필 이미지를 관리합니다.</p>
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

        <div>
          <label class="form-label" for="profile-bio">소개</label>
          <textarea id="profile-bio" v-model="form.bio" class="form-control" rows="4" />
          <p v-if="firstFieldError('bio')" class="field-error">{{ firstFieldError('bio') }}</p>
        </div>

        <div>
          <label class="form-label" for="profile-image-alt">이미지 대체 텍스트</label>
          <input
            id="profile-image-alt"
            v-model.trim="form.profile_image_alt"
            class="form-control"
            type="text"
          />
          <p v-if="firstFieldError('profile_image_alt')" class="field-error">
            {{ firstFieldError('profile_image_alt') }}
          </p>
        </div>

        <div>
          <label class="form-label" for="profile-image">프로필 이미지</label>
          <input
            id="profile-image"
            class="form-control"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            @change="handleImageChange"
          />
          <p v-if="firstFieldError('profile_image')" class="field-error">
            {{ firstFieldError('profile_image') }}
          </p>
        </div>

        <ResponsiveImage
          v-if="selectedImagePreview || authStore.user?.profile_image_url"
          class="profile-avatar profile-avatar-preview"
          :src="selectedImagePreview || authStore.user?.profile_image_url"
          :alt="form.profile_image_alt || '프로필 이미지 미리보기'"
          fallback-label="이미지 없음"
        />

        <label class="form-check">
          <input v-model="form.remove_profile_image" class="form-check-input" type="checkbox" />
          <span class="form-check-label">현재 프로필 이미지 삭제</span>
        </label>

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
