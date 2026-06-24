import apiClient from '@/services/apiClient'
import { cleanParams } from '@/utils/query'

const LIBRARY_LIST_QUERY_KEYS = ['page', 'page_size', 'q', 'sigungu', 'library_type']

export async function fetchLibraries(params = {}) {
  const { data } = await apiClient.get('/libraries/', {
    params: cleanParams(params, LIBRARY_LIST_QUERY_KEYS),
  })
  return data
}

export async function fetchLibraryDetail(libraryId) {
  const { data } = await apiClient.get(`/libraries/${libraryId}/`)
  return data
}

export async function saveLibrary(libraryId) {
  const { data } = await apiClient.post(`/libraries/${libraryId}/save/`)
  return data
}

export async function unsaveLibrary(libraryId) {
  const { data } = await apiClient.delete(`/libraries/${libraryId}/save/`)
  return data
}
