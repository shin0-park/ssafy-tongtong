import { computed, reactive, ref } from 'vue'
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
  const hydrateError = ref(null)

  const hasHydrated = computed(
    () =>
      savedLibraryIds.size > 0 ||
      savedBookIsbns.size > 0 ||
      savedProgramIds.size > 0 ||
      likedReviewIds.size > 0,
  )

  function reset() {
    savedLibraryIds.clear()
    savedBookIsbns.clear()
    savedProgramIds.clear()
    likedReviewIds.clear()
    hydrateError.value = null
  }

  async function hydrate() {
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
    } catch (error) {
      hydrateError.value = error
    } finally {
      isHydrating.value = false
    }
  }

  async function toggleLibrarySave(libraryId) {
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
