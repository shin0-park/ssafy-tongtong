<script setup>
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const { isAuthenticated, user } = storeToRefs(authStore)

async function handleLogout() {
  await authStore.logout()
  await router.push('/')
}
</script>

<template>
  <header class="app-header border-bottom bg-white">
    <nav class="navbar navbar-expand-lg">
      <div class="container">
        <RouterLink class="navbar-brand fw-bold" to="/">도서관 나들이</RouterLink>

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
          <ul class="navbar-nav me-auto mb-2 mb-lg-0">
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
          </ul>

          <div class="d-flex align-items-center gap-2">
            <RouterLink v-if="isAuthenticated" class="btn btn-outline-primary btn-sm" to="/my-outings/dashboard">
              나의 나들이
            </RouterLink>
            <RouterLink v-if="isAuthenticated" class="btn btn-outline-secondary btn-sm" to="/preferences">
              선호 설정
            </RouterLink>
            <RouterLink v-if="isAuthenticated" class="btn btn-outline-secondary btn-sm" to="/profile">
              {{ user?.nickname || '프로필' }}
            </RouterLink>
            <button v-if="isAuthenticated" class="btn btn-link btn-sm" type="button" @click="handleLogout">
              로그아웃
            </button>
            <RouterLink v-else class="btn btn-primary btn-sm" to="/auth/login">로그인</RouterLink>
            <RouterLink v-if="!isAuthenticated" class="btn btn-outline-secondary btn-sm" to="/auth/signup">
              회원가입
            </RouterLink>
          </div>
        </div>
      </div>
    </nav>
  </header>

  <main>
    <RouterView />
  </main>
</template>
