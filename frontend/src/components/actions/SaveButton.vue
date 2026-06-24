<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useInteractionStore } from '@/stores/interaction'

const props = defineProps({
  resourceType: {
    type: String,
    required: true,
    validator: (value) => ['library', 'book', 'program'].includes(value),
  },
  resourceId: {
    type: [Number, String],
    required: true,
  },
})

const emit = defineEmits(['success', 'error'])

const authStore = useAuthStore()
const interactionStore = useInteractionStore()
const router = useRouter()
const isSubmitting = ref(false)
const errorMessage = ref('')

const isSaved = computed(() => {
  if (props.resourceType === 'library') return interactionStore.savedLibraryIds.has(props.resourceId)
  if (props.resourceType === 'book') return interactionStore.savedBookIsbns.has(props.resourceId)
  return interactionStore.savedProgramIds.has(props.resourceId)
})

const label = computed(() => {
  if (isSubmitting.value) return '처리 중'
  return isSaved.value ? '저장됨' : '저장'
})

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
    if (props.resourceType === 'library') {
      await interactionStore.toggleLibrarySave(props.resourceId)
    } else if (props.resourceType === 'book') {
      await interactionStore.toggleBookSave(props.resourceId)
    } else {
      await interactionStore.toggleProgramSave(props.resourceId)
    }
    emit('success', isSaved.value)
  } catch (error) {
    errorMessage.value = error.message || '저장 상태를 변경하지 못했습니다.'
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
      :aria-pressed="isSaved"
      :disabled="isSubmitting"
      @click="handleClick"
    >
      {{ label }}
    </button>
    <span v-if="errorMessage" class="field-error">{{ errorMessage }}</span>
  </span>
</template>
