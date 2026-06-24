import apiClient from '@/services/apiClient'
import { cleanParams } from '@/utils/query'

const BOOK_LIST_QUERY_KEYS = ['page', 'page_size', 'q']
const BOOK_SEARCH_QUERY_KEYS = [
  'search_type',
  'q',
  'title',
  'author',
  'isbn13',
  'keyword',
  'publisher',
  'page',
  'page_size',
  'sort',
  'order',
]
const BOOK_HOLDING_QUERY_KEYS = ['page', 'page_size']
const BOOK_POPULAR_QUERY_KEYS = ['limit', 'region']

export async function fetchBooks(params = {}) {
  const { data } = await apiClient.get('/books/', {
    params: cleanParams(params, BOOK_LIST_QUERY_KEYS),
  })
  return data
}

export async function fetchPopularBooks(params = {}) {
  const { data } = await apiClient.get('/books/popular/', {
    params: cleanParams(params, BOOK_POPULAR_QUERY_KEYS),
  })
  return data
}

export async function fetchBookDetail(isbn13) {
  const { data } = await apiClient.get(`/books/${isbn13}/`)
  return data
}

export async function searchBooks(params = {}) {
  const { data } = await apiClient.get('/books/search/', {
    params: cleanParams(params, BOOK_SEARCH_QUERY_KEYS),
  })
  return data
}

export async function fetchBookLibraries(isbn13, params = {}) {
  const { data } = await apiClient.get(`/books/${isbn13}/libraries/`, {
    params: cleanParams(params, BOOK_HOLDING_QUERY_KEYS),
  })
  return data
}

export async function saveBook(isbn13) {
  const { data } = await apiClient.post(`/books/${isbn13}/save/`)
  return data
}

export async function unsaveBook(isbn13) {
  const { data } = await apiClient.delete(`/books/${isbn13}/save/`)
  return data
}
