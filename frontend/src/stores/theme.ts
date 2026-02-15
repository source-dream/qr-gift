import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'

type ThemeMode = 'light' | 'dark'

const THEME_KEY = 'qrgift-theme'

export const useThemeStore = defineStore('theme', () => {
  const mode = shallowRef<ThemeMode>((localStorage.getItem(THEME_KEY) as ThemeMode) || 'light')

  const isDark = computed(() => mode.value === 'dark')

  function applyMode(nextMode: ThemeMode): void {
    mode.value = nextMode
    localStorage.setItem(THEME_KEY, nextMode)
    document.documentElement.setAttribute('data-theme', nextMode)
  }

  function toggleMode(): void {
    // 中文注释：主题切换统一由 Store 管理，避免组件各自维护状态导致 UI 不一致。
    applyMode(mode.value === 'light' ? 'dark' : 'light')
  }

  applyMode(mode.value)

  return {
    mode,
    isDark,
    applyMode,
    toggleMode,
  }
})
