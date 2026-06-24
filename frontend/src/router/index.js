import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { sanitizeInternalRedirect } from '@/utils/query'

const PlaceholderView = () => import('@/pages/system/PlaceholderView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/pages/home/HomeView.vue'),
    },
    {
      path: '/libraries',
      name: 'library-list',
      component: () => import('@/pages/libraries/LibraryListView.vue'),
    },
    {
      path: '/libraries/:id',
      name: 'library-detail',
      component: () => import('@/pages/libraries/LibraryDetailView.vue'),
      props: true,
    },
    {
      path: '/books',
      name: 'book-list',
      component: () => import('@/pages/books/BookExploreView.vue'),
    },
    {
      path: '/books/:isbn13',
      name: 'book-detail',
      component: () => import('@/pages/books/BookDetailView.vue'),
      props: true,
    },
    {
      path: '/programs',
      name: 'program-list',
      component: PlaceholderView,
      props: {
        title: '문화 프로그램',
      },
    },
    {
      path: '/reviews',
      name: 'review-list',
      component: PlaceholderView,
      props: {
        title: '커뮤니티',
      },
    },
    {
      path: '/auth/login',
      name: 'login',
      component: () => import('@/pages/auth/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/auth/signup',
      name: 'signup',
      component: () => import('@/pages/auth/SignupView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/my-outings',
      redirect: '/my-outings/libraries',
      meta: { requiresAuth: true },
    },
    {
      path: '/my-outings/libraries',
      name: 'my-outings-libraries',
      component: PlaceholderView,
      meta: { requiresAuth: true },
      props: {
        title: '저장한 도서관',
      },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/pages/profile/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/profile/edit',
      name: 'profile-edit',
      component: () => import('@/pages/profile/ProfileEditView.vue'),
      meta: { requiresAuth: true },
    },
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
