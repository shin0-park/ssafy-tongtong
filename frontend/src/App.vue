<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

import { useAuthStore } from '@/stores/auth'

const DEFAULT_PROFILE_IMAGE_URL = '/static/media_assets/placeholders/default_profile.png'

const authStore = useAuthStore()
const router = useRouter()
const { isAuthenticated, user } = storeToRefs(authStore)

async function handleLogout() {
  await authStore.logout()
  await router.push('/')
}
</script>

<template>
  <header class="app-header">
    <nav class="navbar navbar-expand-lg">
      <div class="container-fluid app-nav-container">
        <RouterLink class="navbar-brand app-brand" to="/">
          <img class="brand-icon" src="/brand/logo-icon.png" alt="" aria-hidden="true" />
          <img class="brand-wordmark" src="/brand/logo-wordmark.png" alt="도서관 나들이" />
        </RouterLink>

        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#main-navigation"
          aria-controls="main-navigation"
          aria-expanded="false"
          aria-label="메뉴 열기"
        >
          <span class="navbar-toggler-icon"></span>
        </button>

        <div id="main-navigation" class="collapse navbar-collapse">
          <ul class="navbar-nav mx-auto mb-2 mb-lg-0 app-main-nav">
            <li class="nav-item">
              <RouterLink class="nav-link" to="/">홈</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link" to="/libraries">도서관 찾기</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link" to="/books">책 둘러보기</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link" to="/programs">문화 프로그램</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link" to="/community">커뮤니티</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="nav-link" to="/my-outings/dashboard">나의 나들이</RouterLink>
            </li>
          </ul>

          <div class="d-flex align-items-center gap-2 app-user-actions">
            <template v-if="isAuthenticated">
              <RouterLink class="nav-profile-link" to="/profile" :aria-label="`${user?.nickname || '프로필'} 페이지로 이동`">
                <img
                  class="nav-profile-avatar"
                  :src="user?.profile_image_url || DEFAULT_PROFILE_IMAGE_URL"
                  :alt="user?.profile_image_alt || ''"
                />
                <span class="visually-hidden">{{ user?.nickname || '프로필' }}</span>
              </RouterLink>
              <button class="btn btn-link btn-sm" type="button" @click="handleLogout">로그아웃</button>
            </template>
            <template v-else>
              <RouterLink class="btn btn-primary btn-sm" to="/auth/login">로그인</RouterLink>
              <RouterLink class="btn btn-outline-secondary btn-sm" to="/auth/signup">회원가입</RouterLink>
            </template>
          </div>
        </div>
      </div>
    </nav>
  </header>

  <main>
    <RouterView />
  </main>
</template>
