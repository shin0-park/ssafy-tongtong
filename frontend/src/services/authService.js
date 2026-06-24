import apiClient from '@/services/apiClient'

export async function signup(payload) {
  const { data } = await apiClient.post('/auth/signup/', payload, { _skipAuth: true })
  return data
}

export async function login(payload) {
  const { data } = await apiClient.post('/auth/login/', payload, { _skipAuth: true })
  return data
}

export async function refreshToken() {
  const { data } = await apiClient.post('/auth/token/refresh/', null, { _skipAuth: true })
  return data
}

export async function logout() {
  const { data } = await apiClient.post('/auth/logout/')
  return data
}
