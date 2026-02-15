<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'

interface NavItem {
  to: string
  label: string
}

const navItems: NavItem[] = [
  { to: '/', label: '监控看板' },
  { to: '/gifts', label: '礼物二维码' },
  { to: '/red-packets', label: '礼物管理' },
  { to: '/security', label: '安全策略' },
  { to: '/logs', label: '日志中心' },
  { to: '/system-config', label: '系统配置' },
]

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const authStore = useAuthStore()

const currentTitle = computed(() => {
  const current = navItems.find((item) => item.to === route.path)
  if (current) {
    return current.label
  }
  if (route.path.startsWith('/gifts/')) {
    return '礼物二维码'
  }
  if (route.path.startsWith('/red-packets/')) {
    return '礼物管理'
  }
  return 'QRGift 控制台'
})

function logout(): void {
  authStore.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar card-surface">
      <div class="brand-row">
        <div>
          <h1 class="brand-title">QRGift</h1>
          <p class="brand-subtitle">节庆礼赠与数据可视化平台</p>
        </div>
        <div class="mobile-action-row">
          <button class="theme-button" type="button" @click="themeStore.toggleMode()">
            {{ themeStore.isDark ? '浅色' : '深色' }}
          </button>
          <button class="logout-button" type="button" @click="logout">退出</button>
        </div>
      </div>

      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.to" class="nav-link" :to="item.to">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <main class="content">
      <header class="topbar card-surface">
        <div>
          <p class="topbar-title">{{ currentTitle }}</p>
          <p class="topbar-subtitle">欢迎回来，{{ authStore.username || '管理员' }}</p>
        </div>
        <div class="action-row">
          <button class="theme-button" type="button" @click="themeStore.toggleMode()">
            {{ themeStore.isDark ? '切换浅色' : '切换深色' }}
          </button>
          <button class="logout-button" type="button" @click="logout">退出</button>
        </div>
      </header>

      <section class="view-wrap">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  align-items: start;
  gap: 16px;
  min-height: 100vh;
  min-width: 0;
  padding: 16px;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.brand-title {
  margin: 0;
  font-family: var(--font-display);
  color: var(--color-primary);
}

.brand-row {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.brand-subtitle {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.mobile-action-row {
  display: none;
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-link {
  border-radius: 12px;
  padding: 10px 12px;
  color: var(--color-text-main);
  text-decoration: none;
  transition: background-color 0.2s ease;
}

.nav-link.router-link-exact-active {
  background-color: var(--color-primary-soft);
  color: var(--color-primary-deep);
}

.content {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 16px;
  min-width: 0;
}

.topbar {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.topbar-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.topbar-subtitle {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.theme-button {
  border: 0;
  border-radius: 12px;
  background: linear-gradient(120deg, var(--color-primary), var(--color-accent));
  color: #fff;
  cursor: pointer;
  padding: 8px 12px;
}

.action-row {
  display: flex;
  gap: 8px;
}

.logout-button {
  border: 1px solid color-mix(in oklab, var(--color-primary) 35%, #999 20%);
  border-radius: 12px;
  background-color: transparent;
  color: var(--color-text-main);
  cursor: pointer;
  padding: 8px 12px;
}

.view-wrap {
  display: block;
  min-width: 0;
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: 1fr;
    gap: 10px;
    min-height: auto;
    padding: 10px;
  }

  .sidebar {
    align-self: start;
    gap: 10px;
    padding: 10px;
  }

  .mobile-action-row {
    display: flex;
    gap: 6px;
  }

  .nav-list {
    display: grid;
    gap: 6px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 0;
    width: 100%;
  }

  .nav-link {
    border-radius: 10px;
    font-size: 13px;
    padding: 8px 10px;
    text-align: center;
  }

  .topbar {
    display: none;
  }

  .topbar-title {
    font-size: 18px;
  }

  .topbar-subtitle {
    font-size: 12px;
    margin-top: 4px;
  }

  .action-row {
    display: none;
  }

  .mobile-action-row .theme-button,
  .mobile-action-row .logout-button,
  .logout-button {
    flex: 0 0 auto;
    font-size: 12px;
    justify-content: center;
    min-height: 30px;
    padding: 4px 8px;
    text-align: center;
    white-space: nowrap;
  }
}

@media (max-width: 480px) {
  .brand-title {
    font-size: 22px;
  }

  .brand-subtitle {
    display: none;
  }

  .nav-list {
    gap: 5px;
  }

  .nav-link {
    font-size: 12px;
    padding: 7px 8px;
  }
}
</style>
