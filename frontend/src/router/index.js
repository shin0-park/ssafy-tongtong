import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { sanitizeInternalRedirect } from '@/utils/query'

const PlaceholderView = () => import('@/pages/system/PlaceholderView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: () => import('@/pages/home/HomeView.vue') },
    { path: '/libraries', name: 'library-list', component: () => import('@/pages/libraries/LibraryListView.vue') },
    {
      path: '/libraries/:id',
      name: 'library-detail',
      component: () => import('@/pages/libraries/LibraryDetailView.vue'),
      props: true,
    },
    { path: '/books', name: 'book-list', component: () => import('@/pages/books/BookExploreView.vue') },
    {
      path: '/books/:isbn13',
      name: 'book-detail',
      component: () => import('@/pages/books/BookDetailView.vue'),
      props: true,
    },
    { path: '/programs', name: 'program-list', component: () => import('@/pages/programs/ProgramListView.vue') },
    {
      path: '/programs/:id',
      name: 'program-detail',
      component: () => import('@/pages/programs/ProgramDetailView.vue'),
      props: true,
    },
    { path: '/reviews', redirect: '/community' },
    { path: '/community', name: 'review-list', component: () => import('@/pages/community/ReviewListView.vue') },
    {
      path: '/reviews/new',
      name: 'review-create',
      component: () => import('@/pages/community/ReviewFormView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/reviews/:id/edit',
      name: 'review-edit',
      component: () => import('@/pages/community/ReviewFormView.vue'),
      props: true,
      meta: { requiresAuth: true },
    },
    { path: '/reviews/:id', name: 'review-detail', component: () => import('@/pages/community/ReviewDetailView.vue'), props: true },
    { path: '/auth/login', name: 'login', component: () => import('@/pages/auth/LoginView.vue'), meta: { guestOnly: true } },
    { path: '/auth/signup', name: 'signup', component: () => import('@/pages/auth/SignupView.vue'), meta: { guestOnly: true } },
    { path: '/my-outings', redirect: '/my-outings/dashboard', meta: { requiresAuth: true } },
    {
      path: '/my-outings/dashboard',
      name: 'my-outings-dashboard',
      component: () => import('@/pages/myoutings/MyOutingsDashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/my-outings/libraries',
      name: 'my-outings-libraries',
      component: () => import('@/pages/myoutings/MyOutingsListView.vue'),
      meta: { requiresAuth: true },
      props: { kind: 'libraries' },
    },
    {
      path: '/my-outings/books',
      name: 'my-outings-books',
      component: () => import('@/pages/myoutings/MyOutingsListView.vue'),
      meta: { requiresAuth: true },
      props: { kind: 'books' },
    },
    {
      path: '/my-outings/programs',
      name: 'my-outings-programs',
      component: () => import('@/pages/myoutings/MyOutingsListView.vue'),
      meta: { requiresAuth: true },
      props: { kind: 'programs' },
    },
    {
      path: '/my-outings/reviews',
      name: 'my-outings-reviews',
      component: () => import('@/pages/myoutings/MyOutingsListView.vue'),
      meta: { requiresAuth: true },
      props: { kind: 'reviews' },
    },
    {
      path: '/my-outings/liked-reviews',
      name: 'my-outings-liked-reviews',
      component: () => import('@/pages/myoutings/MyOutingsListView.vue'),
      meta: { requiresAuth: true },
      props: { kind: 'liked-reviews' },
    },
    { path: '/profile', name: 'profile', component: () => import('@/pages/profile/ProfileView.vue'), meta: { requiresAuth: true } },
    {
      path: '/profile/edit',
      name: 'profile-edit',
      component: () => import('@/pages/profile/ProfileEditView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/preferences',
      name: 'preferences',
      component: () => import('@/pages/preferences/PreferenceSettingsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/onboarding/preferences',
      name: 'onboarding-preferences',
      component: () => import('@/pages/preferences/PreferenceSettingsView.vue'),
      meta: { requiresAuth: true },
    },
    { path: '/403', name: 'forbidden', component: () => import('@/pages/system/ForbiddenView.vue') },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: PlaceholderView,
      props: {
        title: '페이지를 찾을 수 없습니다.',
        description: '주소를 확인한 뒤 다시 이동해주세요.',
      },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (!authStore.accessToken) {
    await authStore.bootstrapSession()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: {
        redirect: sanitizeInternalRedirect(to.fullPath, '/'),
      },
    }
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return sanitizeInternalRedirect(to.query.redirect, '/')
  }

  return true
})

export default router
