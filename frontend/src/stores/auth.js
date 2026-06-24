import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as accountService from '@/services/accountService'
import * as authService from '@/services/authService'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(null)
  const user = ref(null)
  const isBootstrapping = ref(false)
  const authError = ref(null)

  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value))

  function setSession(payload) {
    accessToken.value = payload.access
    user.value = payload.user ?? user.value
    authError.value = null
  }

  function clearSession() {
    accessToken.value = null
    user.value = null
    authError.value = null
    import('@/stores/interaction').then(({ useInteractionStore }) => {
      useInteractionStore().reset()
    })
  }

  async function signup(payload) {
    const data = await authService.signup(payload)
    setSession(data)
    return data
  }

  async function login(payload) {
    const data = await authService.login(payload)
    setSession(data)
    import('@/stores/interaction').then(({ useInteractionStore }) => {
      useInteractionStore().hydrate()
    })
    return data
  }

  async function refreshAccessToken() {
    const data = await authService.refreshToken()
    accessToken.value = data.access
    return data
  }

  async function bootstrapSession() {
    if (accessToken.value || isBootstrapping.value) {
      return
    }

    isBootstrapping.value = true

    try {
      await refreshAccessToken()
      user.value = await accountService.fetchCurrentUser()
      import('@/stores/interaction').then(({ useInteractionStore }) => {
        useInteractionStore().hydrate()
      })
      authError.value = null
    } catch (error) {
      clearSession()
      authError.value = error
    } finally {
      isBootstrapping.value = false
    }
  }

  async function fetchCurrentUser() {
    user.value = await accountService.fetchCurrentUser()
    return user.value
  }

  async function updateCurrentUser(payload) {
    user.value = await accountService.updateCurrentUser(payload)
    return user.value
  }

  async function updateCurrentUserProfile(payload, config = {}) {
    user.value = await accountService.updateCurrentUserProfile(payload, config)
    return user.value
  }

  async function logout() {
    try {
      await authService.logout()
    } finally {
      clearSession()
    }
  }

  return {
    accessToken,
    user,
    isAuthenticated,
    isBootstrapping,
    authError,
    signup,
    login,
    logout,
    bootstrapSession,
    refreshAccessToken,
    fetchCurrentUser,
    updateCurrentUser,
    updateCurrentUserProfile,
    clearSession,
    setSession,
  }
})
