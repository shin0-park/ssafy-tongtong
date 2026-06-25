import apiClient from '@/services/apiClient'
import { cleanParams } from '@/utils/query'

const PROGRAM_LIST_QUERY_KEYS = [
  'page',
  'page_size',
  'q',
  'library_id',
  'sigungu',
  'category',
  'target',
  'application_status',
  'operation_status',
  'ordering',
]

export async function fetchPrograms(params = {}) {
  const { data } = await apiClient.get('/programs/', {
    params: cleanParams(params, PROGRAM_LIST_QUERY_KEYS),
  })
  return data
}

export async function fetchProgramDetail(programId) {
  const { data } = await apiClient.get(`/programs/${programId}/`)
  return data
}

export async function saveProgram(programId) {
  const { data } = await apiClient.post(`/programs/${programId}/save/`)
  return data
}

export async function unsaveProgram(programId) {
  const { data } = await apiClient.delete(`/programs/${programId}/save/`)
  return data
}
