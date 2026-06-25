import { reactive, ref } from 'vue'
import { defineStore } from 'pinia'

import * as bookService from '@/services/bookService'
import * as libraryService from '@/services/libraryService'
import * as myOutingsService from '@/services/myOutingsService'
import * as programService from '@/services/programService'
import * as reviewService from '@/services/reviewService'

export const useInteractionStore = defineStore('interaction', () => {
  const savedLibraryIds = reactive(new Set())
  const savedBookIsbns = reactive(new Set())
  const savedProgramIds = reactive(new Set())
  const likedReviewIds = reactive(new Set())
  const isHydrating = ref(false)
  const hasHydrated = ref(false)
  const hydrateError = ref(null)

  function reset() {
    savedLibraryIds.clear()
    savedBookIsbns.clear()
    savedProgramIds.clear()
    likedReviewIds.clear()
    hydrateError.value = null
    hasHydrated.value = false
  }

  async function hydrate() {
    if (isHydrating.value) return

    isHydrating.value = true
    hydrateError.value = null

    try {
      const [libraries, books, programs, likedReviews] = await Promise.all([
        myOutingsService.fetchSavedLibraries(),
        myOutingsService.fetchSavedBooks(),
        myOutingsService.fetchSavedPrograms(),
        myOutingsService.fetchLikedReviews(),
      ])

      savedLibraryIds.clear()
      ;(libraries.results ?? []).forEach((item) => {
        if (item.library?.id) savedLibraryIds.add(item.library.id)
      })

      savedBookIsbns.clear()
      ;(books.results ?? []).forEach((item) => {
        if (item.book?.isbn13) savedBookIsbns.add(item.book.isbn13)
      })

      savedProgramIds.clear()
      ;(programs.results ?? []).forEach((item) => {
        if (item.program?.id) savedProgramIds.add(item.program.id)
      })

      likedReviewIds.clear()
      ;(likedReviews.results ?? []).forEach((item) => {
        if (item.review?.id) likedReviewIds.add(item.review.id)
      })
      hasHydrated.value = true
    } catch (error) {
      hydrateError.value = error
    } finally {
      isHydrating.value = false
    }
  }

  async function ensureHydrated(message) {
    if (!hasHydrated.value) await hydrate()
    if (!hasHydrated.value) throw hydrateError.value || new Error(message)
  }

  async function toggleLibrarySave(libraryId) {
    await ensureHydrated('저장 상태를 확인하지 못했습니다.')

    if (savedLibraryIds.has(libraryId)) {
      await libraryService.unsaveLibrary(libraryId)
      savedLibraryIds.delete(libraryId)
      return false
    }

    await libraryService.saveLibrary(libraryId)
    savedLibraryIds.add(libraryId)
    return true
  }

  async function toggleBookSave(isbn13) {
    await ensureHydrated('저장 상태를 확인하지 못했습니다.')

    if (savedBookIsbns.has(isbn13)) {
      await bookService.unsaveBook(isbn13)
      savedBookIsbns.delete(isbn13)
      return false
    }

    await bookService.saveBook(isbn13)
    savedBookIsbns.add(isbn13)
    return true
  }

  async function toggleProgramSave(programId) {
    await ensureHydrated('저장 상태를 확인하지 못했습니다.')

    if (savedProgramIds.has(programId)) {
      await programService.unsaveProgram(programId)
      savedProgramIds.delete(programId)
      return false
    }

    await programService.saveProgram(programId)
    savedProgramIds.add(programId)
    return true
  }

  async function toggleReviewLike(reviewId) {
    await ensureHydrated('좋아요 상태를 확인하지 못했습니다.')

    if (likedReviewIds.has(reviewId)) {
      const data = await reviewService.unlikeReview(reviewId)
      likedReviewIds.delete(reviewId)
      return data
    }

    const data = await reviewService.likeReview(reviewId)
    likedReviewIds.add(reviewId)
    return data
  }

  return {
    savedLibraryIds,
    savedBookIsbns,
    savedProgramIds,
    likedReviewIds,
    isHydrating,
    hydrateError,
    hasHydrated,
    hydrate,
    reset,
    toggleLibrarySave,
    toggleBookSave,
    toggleProgramSave,
    toggleReviewLike,
  }
})
