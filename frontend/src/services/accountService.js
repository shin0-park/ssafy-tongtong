import apiClient from '@/services/apiClient'

export async function fetchCurrentUser() {
  const { data } = await apiClient.get('/users/me/')
  return data
}

export async function updateCurrentUser(payload) {
  const { data } = await apiClient.patch('/users/me/', payload)
  return data
}

export async function updateCurrentUserProfile(payload) {
  const { data } = await apiClient.patch('/users/me/', payload)
  return data
}
