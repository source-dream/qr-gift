import { computed, shallowRef } from 'vue'
import { defineStore } from 'pinia'

import { loginApi } from '../api/modules/auth'

const TOKEN_KEY = 'qrgift-access-token'

export const useAuthStore = defineStore('auth', () => {
  const token = shallowRef<string>(localStorage.getItem(TOKEN_KEY) || '')
  const username = shallowRef<string>(localStorage.getItem('qrgift-username') || 'admin')

  const isAuthed = computed(() => !!token.value)

  function setToken(nextToken: string): void {
    token.value = nextToken
    if (nextToken) {
      localStorage.setItem(TOKEN_KEY, nextToken)
      return
    }
    localStorage.removeItem(TOKEN_KEY)
  }

  async function login(name: string, password: string): Promise<void> {
    const result = await loginApi(name, password)
    setToken(result.access_token)
    username.value = name
    localStorage.setItem('qrgift-username', name)
  }

  function logout(): void {
    setToken('')
  }

  return {
    token,
    username,
    isAuthed,
    login,
    logout,
  }
})
