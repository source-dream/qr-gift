<script setup lang="ts">
import { onMounted, reactive, shallowRef } from 'vue'

import { getSecurityRules, updateSecurityRules } from '../api/modules/security'

const loading = shallowRef(false)
const message = shallowRef('')

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

const form = reactive({
  claim_enabled: true,
  ip_whitelist_text: '',
  ip_blacklist_text: '',
  max_per_ip_per_hour: 5,
})

function splitText(text: string): string[] {
  return text
    .split(/[,\n]/g)
    .map((item) => item.trim())
    .filter(Boolean)
}

function isValidIp(ip: string): boolean {
  const ipv4 = /^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/
  if (ipv4.test(ip)) {
    return true
  }
  if (ip.includes(':')) {
    // 中文注释：前端仅做轻量预校验，IPv6 兼容格式较多，最终以服务端 ipaddress 校验为准。
    return /^[0-9a-fA-F:]+$/.test(ip)
  }
  return false
}

async function loadRules(): Promise<void> {
  const rules = await getSecurityRules()
  form.claim_enabled = rules.claim_enabled
  form.max_per_ip_per_hour = rules.max_per_ip_per_hour
  form.ip_whitelist_text = rules.ip_whitelist.join('\n')
  form.ip_blacklist_text = rules.ip_blacklist.join('\n')
}

async function submit(): Promise<void> {
  const whitelist = splitText(form.ip_whitelist_text)
  const blacklist = splitText(form.ip_blacklist_text)

  const invalid = [...whitelist, ...blacklist].find((item) => !isValidIp(item))
  if (invalid) {
    message.value = `存在无效 IP：${invalid}`
    return
  }

  loading.value = true
  message.value = ''
  try {
    await updateSecurityRules({
      claim_enabled: form.claim_enabled,
      max_per_ip_per_hour: form.max_per_ip_per_hour,
      ip_whitelist: whitelist,
      ip_blacklist: blacklist,
    })
    message.value = '策略已更新'
  } catch (error) {
    message.value = resolveErrorMessage(error, '策略更新失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRules()
})
</script>

<template>
  <section class="card-surface">
    <h2 class="title">安全策略</h2>
    <p class="desc">支持开关领取、IP 白黑名单、单 IP 频控。</p>

    <div class="form-grid">
      <label class="field">
        <span>是否允许领取</span>
        <select v-model="form.claim_enabled" class="input">
          <option :value="true">允许</option>
          <option :value="false">暂停</option>
        </select>
      </label>

      <label class="field">
        <span>单 IP 每小时最大领取次数</span>
        <input v-model.number="form.max_per_ip_per_hour" class="input" min="1" max="1000" type="number" />
      </label>

      <label class="field full">
        <span>IP 白名单（每行一个）</span>
        <textarea v-model="form.ip_whitelist_text" class="input textarea"></textarea>
      </label>

      <label class="field full">
        <span>IP 黑名单（每行一个）</span>
        <textarea v-model="form.ip_blacklist_text" class="input textarea"></textarea>
      </label>
    </div>

    <button class="action-button" type="button" :disabled="loading" @click="submit">
      {{ loading ? '保存中...' : '保存策略' }}
    </button>
    <p v-if="message" class="message">{{ message }}</p>
  </section>
</template>

<style scoped>
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.form-grid { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 14px; }
.field { display: grid; gap: 6px; }
.field.full { grid-column: span 2; }
.input { border: 1px solid #ccc; border-radius: 10px; padding: 8px 10px; }
.textarea { min-height: 90px; resize: vertical; }
.action-button { border: 0; border-radius: 10px; background: var(--color-primary); color: #fff; margin-top: 12px; padding: 8px 12px; cursor: pointer; }
.message { color: var(--color-text-secondary); margin: 10px 0 0; }
@media (max-width: 900px) { .form-grid { grid-template-columns: 1fr; } .field.full { grid-column: span 1; } }
</style>
