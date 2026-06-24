import apiClient from '@/services/apiClient'

export async function fetchPreferenceOptions() {
  const { data } = await apiClient.get('/preferences/options/')
  return data
}

export async function fetchMyPreferences() {
  const { data } = await apiClient.get('/users/me/preferences/')
  return data
}

export async function updateMyPreferences(payload) {
  const { data } = await apiClient.put('/users/me/preferences/', payload)
  return data
}
