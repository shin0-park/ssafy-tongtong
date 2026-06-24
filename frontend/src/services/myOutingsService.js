import apiClient from '@/services/apiClient'
import { cleanParams } from '@/utils/query'

const PAGINATION_QUERY_KEYS = ['page', 'page_size']

export async function fetchMyOutingsDashboard() {
  const { data } = await apiClient.get('/my-outings/dashboard/')
  return data
}

export async function fetchSavedLibraries(params = {}) {
  const { data } = await apiClient.get('/my-outings/libraries/', {
    params: cleanParams(params, PAGINATION_QUERY_KEYS),
  })
  return data
}

export async function fetchSavedBooks(params = {}) {
  const { data } = await apiClient.get('/my-outings/books/', {
    params: cleanParams(params, PAGINATION_QUERY_KEYS),
  })
  return data
}

export async function fetchSavedPrograms(params = {}) {
  const { data } = await apiClient.get('/my-outings/programs/', {
    params: cleanParams(params, PAGINATION_QUERY_KEYS),
  })
  return data
}

export async function fetchMyReviews(params = {}) {
  const { data } = await apiClient.get('/my-outings/reviews/', {
    params: cleanParams(params, PAGINATION_QUERY_KEYS),
  })
  return data
}

export async function fetchLikedReviews(params = {}) {
  const { data } = await apiClient.get('/my-outings/liked-reviews/', {
    params: cleanParams(params, PAGINATION_QUERY_KEYS),
  })
  return data
}
