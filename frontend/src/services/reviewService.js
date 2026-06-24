import apiClient from '@/services/apiClient'
import { cleanParams } from '@/utils/query'

const REVIEW_LIST_QUERY_KEYS = ['page', 'page_size', 'q', 'library_id', 'tag', 'user_id', 'ordering']

export async function fetchReviews(params = {}) {
  const { data } = await apiClient.get('/reviews/', {
    params: cleanParams(params, REVIEW_LIST_QUERY_KEYS),
  })
  return data
}

export async function fetchReviewDetail(reviewId) {
  const { data } = await apiClient.get(`/reviews/${reviewId}/`)
  return data
}

export async function createReview(payload, config = {}) {
  const { data } = await apiClient.post('/reviews/', payload, config)
  return data
}

export async function updateReview(reviewId, payload, config = {}) {
  const { data } = await apiClient.patch(`/reviews/${reviewId}/`, payload, config)
  return data
}

export async function deleteReview(reviewId) {
  await apiClient.delete(`/reviews/${reviewId}/`)
}

export async function likeReview(reviewId) {
  const { data } = await apiClient.post(`/reviews/${reviewId}/like/`)
  return data
}

export async function unlikeReview(reviewId) {
  const { data } = await apiClient.delete(`/reviews/${reviewId}/like/`)
  return data
}
