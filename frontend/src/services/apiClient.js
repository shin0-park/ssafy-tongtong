import axios from 'axios'

import { normalizeApiError } from '@/utils/apiError'

const apiBaseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const timeout = Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS || 15000)

export const apiClient = axios.create({
  baseURL: apiBaseURL,
  timeout,
  withCredentials: true,
})

let refreshRequest = null

async function getAuthStore() {
  const { useAuthStore } = await import('@/stores/auth')
  return useAuthStore()
}

apiClient.interceptors.request.use(async (config) => {
  const authStore = await getAuthStore()

  if (!config._skipAuth && authStore.accessToken) {
    config.headers.Authorization = `Bearer ${authStore.accessToken}`
  }

  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    const isRefreshRequest = originalRequest?.url?.includes('/auth/token/refresh/')
    const isAuthPageRequest =
      originalRequest?.url?.includes('/auth/login/') ||
      originalRequest?.url?.includes('/auth/signup/') ||
      originalRequest?.url?.includes('/auth/logout/')

    if (
      error.response?.status !== 401 ||
      originalRequest?._retry ||
      isRefreshRequest ||
      isAuthPageRequest
    ) {
      return Promise.reject(normalizeApiError(error))
    }

    originalRequest._retry = true

    try {
      const authStore = await getAuthStore()

      if (!refreshRequest) {
        refreshRequest = authStore.refreshAccessToken().finally(() => {
          refreshRequest = null
        })
      }

      await refreshRequest
      return apiClient(originalRequest)
    } catch (refreshError) {
      const authStore = await getAuthStore()
      authStore.clearSession()
      return Promise.reject(normalizeApiError(refreshError))
    }
  },
)

export default apiClient
