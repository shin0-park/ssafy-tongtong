<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useInteractionStore } from '@/stores/interaction'

const props = defineProps({
  reviewId: {
    type: Number,
    required: true,
  },
  likeCount: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits(['updated', 'error'])

const authStore = useAuthStore()
const interactionStore = useInteractionStore()
const router = useRouter()
const localLikeCount = ref(props.likeCount)
const isSubmitting = ref(false)
const errorMessage = ref('')

const isLiked = computed(() => interactionStore.likedReviewIds.has(props.reviewId))

async function handleClick() {
  errorMessage.value = ''

  if (!authStore.isAuthenticated) {
    await router.push({
      name: 'login',
      query: { redirect: router.currentRoute.value.fullPath },
    })
    return
  }

  isSubmitting.value = true

  try {
    const data = await interactionStore.toggleReviewLike(props.reviewId)
    localLikeCount.value = data.like_count ?? localLikeCount.value
    emit('updated', data)
  } catch (error) {
    errorMessage.value = error.message || '좋아요 상태를 변경하지 못했습니다.'
    emit('error', error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <span class="d-inline-flex flex-column gap-1">
    <button
      class="btn btn-outline-primary btn-sm"
      type="button"
      :aria-pressed="isLiked"
      :disabled="isSubmitting"
      @click="handleClick"
    >
      {{ isLiked ? '좋아요함' : '좋아요' }} {{ localLikeCount }}
    </button>
    <span v-if="errorMessage" class="field-error">{{ errorMessage }}</span>
  </span>
</template>
