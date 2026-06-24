import apiClient from '@/services/apiClient'
import { cleanParams } from '@/utils/query'

const LIBRARY_LIST_QUERY_KEYS = [
  'page',
  'page_size',
  'q',
  'sigungu',
  'library_type',
  'purpose',
  'lat',
  'lng',
  'has_reading_room',
  'has_children_room',
  'has_digital_room',
  'has_parking',
  'has_cafe',
  'has_wifi',
  'has_nursing_room',
  'has_accessible_facility',
  'has_elevator',
  'has_lounge',
  'has_outdoor_space',
  'min_book_count',
  'min_reading_seat_count',
  'ordering',
  'open_today',
  'open_now',
  'weekend_open',
  'holiday_status',
  'holiday_date',
]
const SIMILAR_LIBRARY_QUERY_KEYS = ['limit']

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

export async function fetchSimilarLibraries(libraryId, params = {}) {
  const { data } = await apiClient.get(`/libraries/${libraryId}/similar/`, {
    params: cleanParams(params, SIMILAR_LIBRARY_QUERY_KEYS),
  })
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
