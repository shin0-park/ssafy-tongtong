import apiClient from '@/services/apiClient'
import { cleanParams } from '@/utils/query'

const HOME_QUERY_KEYS = ['lat', 'lng']

export async function fetchHome(params = {}) {
  const { data } = await apiClient.get('/home/', {
    params: cleanParams(params, HOME_QUERY_KEYS),
  })
  return data
}

export async function fetchPersonalHomeRecommendations() {
  const { data } = await apiClient.get('/home/personal-recommendations/')
  return data
}
