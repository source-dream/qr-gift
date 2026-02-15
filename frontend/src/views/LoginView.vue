<script setup lang="ts">
import { onMounted, reactive, shallowRef } from 'vue'
import { useRouter } from 'vue-router'

import { getBootstrapStatusApi, setupAdminApi } from '../api/modules/auth'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  username: authStore.username || '',
  password: '',
  confirmPassword: '',
})

const loading = shallowRef(false)
const errorMessage = shallowRef('')
const initialized = shallowRef(true)

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

async function loadBootstrapStatus(): Promise<void> {
  try {
    const status = await getBootstrapStatusApi()
    initialized.value = status.initialized
    if (!initialized.value && !form.username) {
      form.username = 'admin'
    }
  } catch (_error) {
    initialized.value = true
  }
}

async function setup(): Promise<void> {
  if (!form.username.trim()) {
    errorMessage.value = '请输入管理员账号'
    return
  }
  if (form.password.length < 8) {
    errorMessage.value = '密码长度至少为8位'
    return
  }
  if (form.password !== form.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    await setupAdminApi(form.username, form.password)
    initialized.value = true
    form.confirmPassword = ''
    await authStore.login(form.username, form.password)
    await router.replace('/')
  } catch (error) {
    errorMessage.value = resolveErrorMessage(error, '初始化失败，请检查账号和密码格式')
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  if (!initialized.value) {
    await setup()
    return
  }

  if (!form.username.trim() || !form.password) {
    errorMessage.value = '请输入账号和密码'
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    await authStore.login(form.username, form.password)
    await router.replace('/')
  } catch (error) {
    errorMessage.value = resolveErrorMessage(error, '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadBootstrapStatus()
})
</script>

<template>
  <main class="login-page">
    <section class="login-panel card-surface">
      <h1 class="title">QRGift 管理后台</h1>
      <p class="subtitle">{{ initialized ? '节庆礼赠与数据可视化融合平台' : '首次打开，请先创建管理员账号' }}</p>

      <form class="form" @submit.prevent="submit">
        <label class="field-label" for="username">账号</label>
        <input id="username" v-model="form.username" class="field-input" autocomplete="username" />

        <label class="field-label" for="password">密码</label>
        <input
          id="password"
          v-model="form.password"
          class="field-input"
          type="password"
          :autocomplete="initialized ? 'current-password' : 'new-password'"
        />

        <template v-if="!initialized">
          <label class="field-label" for="confirmPassword">确认密码</label>
          <input
            id="confirmPassword"
            v-model="form.confirmPassword"
            class="field-input"
            type="password"
            autocomplete="new-password"
          />
        </template>

        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

        <button class="submit-button" type="submit" :disabled="loading">
          {{ loading ? '处理中...' : initialized ? '登录' : '创建管理员并登录' }}
        </button>
      </form>

      <p v-if="!initialized" class="tip-text">
        本地重置命令：<code>uv run python scripts/reset_admin.py --username admin --password 新密码</code>
      </p>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  align-items: center;
  display: flex;
  justify-content: center;
  min-height: 100vh;
  padding: 20px;
}

.login-panel {
  max-width: 420px;
  width: 100%;
}

.title {
  font-family: var(--font-display);
  margin: 0;
}

.subtitle {
  color: var(--color-text-secondary);
  margin: 8px 0 20px;
}

.form {
  display: grid;
  gap: 10px;
}

.field-label {
  font-size: 14px;
}

.field-input {
  background-color: transparent;
  border: 1px solid color-mix(in oklab, var(--color-primary) 20%, #999 30%);
  border-radius: var(--radius-md);
  color: var(--color-text-main);
  padding: 10px 12px;
}

.error-text {
  color: var(--color-primary);
  margin: 0;
}

.submit-button {
  border: 0;
  border-radius: var(--radius-md);
  background: linear-gradient(120deg, var(--color-primary), var(--color-gold));
  color: #fff;
  cursor: pointer;
  font-weight: 600;
  margin-top: 6px;
  padding: 10px 12px;
}

.submit-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.tip-text {
  color: var(--color-text-secondary);
  font-size: 12px;
  margin: 14px 0 0;
}
</style>
