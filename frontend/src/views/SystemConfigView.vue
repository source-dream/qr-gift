<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef } from 'vue'

import {
  getClaimContact,
  getStorageConfig,
  testStorageConfig,
  updateClaimContact,
  updateStorageConfig,
  type StorageConfigPayload,
} from '../api/modules/systemConfig'

const loading = shallowRef(false)
const message = shallowRef('')
const testing = shallowRef(false)
const claimContact = shallowRef('')

const form = reactive<StorageConfigPayload>({
  provider: 'local',
  bucket: '',
  base_url: '',
  storage_prefix: '',
  local_storage_dir: '',
  minio_endpoint: '',
  minio_secure: false,
  minio_access_key: '',
  minio_secret_key: '',
  aliyun_oss_endpoint: '',
  aliyun_oss_region: '',
  aliyun_oss_access_key_id: '',
  aliyun_oss_access_key_secret: '',
})

const secretHint = reactive({
  minio_access_key_set: false,
  minio_secret_key_set: false,
  aliyun_oss_access_key_id_set: false,
  aliyun_oss_access_key_secret_set: false,
})

const isMinio = computed(() => form.provider === 'minio')
const isLocal = computed(() => form.provider === 'local')

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

async function loadConfig(): Promise<void> {
  try {
    const [data, contact] = await Promise.all([getStorageConfig(), getClaimContact()])
    form.provider = data.provider
    form.bucket = data.bucket
    form.base_url = data.base_url
    form.storage_prefix = data.storage_prefix
    form.local_storage_dir = data.local_storage_dir
    form.minio_endpoint = data.minio_endpoint
    form.minio_secure = data.minio_secure
    form.aliyun_oss_endpoint = data.aliyun_oss_endpoint
    form.aliyun_oss_region = data.aliyun_oss_region

    secretHint.minio_access_key_set = data.minio_access_key_set
    secretHint.minio_secret_key_set = data.minio_secret_key_set
    secretHint.aliyun_oss_access_key_id_set = data.aliyun_oss_access_key_id_set
    secretHint.aliyun_oss_access_key_secret_set = data.aliyun_oss_access_key_secret_set
    claimContact.value = contact.contact_text
  } catch (error) {
    message.value = resolveErrorMessage(error, '配置加载失败')
  }
}

async function saveConfig(): Promise<void> {
  loading.value = true
  message.value = ''
  try {
    await Promise.all([updateStorageConfig({ ...form }), updateClaimContact(claimContact.value)])
    message.value = '保存成功'
    form.minio_access_key = ''
    form.minio_secret_key = ''
    form.aliyun_oss_access_key_id = ''
    form.aliyun_oss_access_key_secret = ''
    await loadConfig()
  } catch (error) {
    message.value = resolveErrorMessage(error, '保存失败')
  } finally {
    loading.value = false
  }
}

async function testConfig(): Promise<void> {
  testing.value = true
  message.value = ''
  try {
    await testStorageConfig({ ...form })
    message.value = '连接测试通过'
  } catch (error) {
    message.value = resolveErrorMessage(error, '连接测试失败')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <section class="card-surface">
    <h2 class="title">系统配置</h2>
    <p class="desc">在 WebUI 配置对象存储，保存后自动应用到后续业务请求。</p>
    <p class="desc hint">提示：测试连接会使用当前输入的密钥，留空将无法测试。</p>

    <div class="form-grid">
      <label class="field">
        <span>存储类型</span>
        <select v-model="form.provider" class="input">
          <option value="local">本地存储</option>
          <option value="minio">MinIO</option>
          <option value="aliyun">阿里云 OSS</option>
        </select>
      </label>

      <label class="field" :class="{ dimmed: isLocal }">
        <span>Bucket</span>
        <input v-model="form.bucket" class="input" type="text" :disabled="isLocal" />
      </label>

      <label class="field full" :class="{ dimmed: isLocal }">
        <span>自定义访问域名（可选）</span>
        <input v-model="form.base_url" class="input" type="text" placeholder="https://cdn.example.com" :disabled="isLocal" />
      </label>

      <label class="field full">
        <span>对象前缀目录（可选）</span>
        <input v-model="form.storage_prefix" class="input" type="text" placeholder="如 gifts/2026" />
      </label>

      <template v-if="isLocal">
        <label class="field full">
          <span>本地存储目录</span>
          <input v-model="form.local_storage_dir" class="input" type="text" placeholder="/data/object-storage" />
        </label>
      </template>

      <template v-else-if="isMinio">
        <label class="field">
          <span>MinIO Endpoint</span>
          <input v-model="form.minio_endpoint" class="input" type="text" placeholder="127.0.0.1:9000" />
        </label>

        <label class="field checkbox-field">
          <span>启用 HTTPS</span>
          <input v-model="form.minio_secure" type="checkbox" />
        </label>

        <label class="field">
          <span>Access Key</span>
          <input
            v-model="form.minio_access_key"
            class="input"
            type="password"
            :placeholder="secretHint.minio_access_key_set ? '已配置，留空不修改' : ''"
          />
        </label>

        <label class="field">
          <span>Secret Key</span>
          <input
            v-model="form.minio_secret_key"
            class="input"
            type="password"
            :placeholder="secretHint.minio_secret_key_set ? '已配置，留空不修改' : ''"
          />
        </label>
      </template>

      <template v-else>
        <label class="field">
          <span>OSS Endpoint</span>
          <input
            v-model="form.aliyun_oss_endpoint"
            class="input"
            type="text"
            placeholder="oss-cn-hangzhou.aliyuncs.com"
          />
        </label>

        <label class="field">
          <span>Region</span>
          <input v-model="form.aliyun_oss_region" class="input" type="text" placeholder="可选，示例 cn-hangzhou" />
        </label>

        <label class="field">
          <span>AccessKey ID</span>
          <input
            v-model="form.aliyun_oss_access_key_id"
            class="input"
            type="password"
            :placeholder="secretHint.aliyun_oss_access_key_id_set ? '已配置，留空不修改' : ''"
          />
        </label>

        <label class="field">
          <span>AccessKey Secret</span>
          <input
            v-model="form.aliyun_oss_access_key_secret"
            class="input"
            type="password"
            :placeholder="secretHint.aliyun_oss_access_key_secret_set ? '已配置，留空不修改' : ''"
          />
        </label>
      </template>

      <label class="field full">
        <span>礼物失效联系方式</span>
        <input v-model="claimContact" class="input" type="text" placeholder="例如：微信 qrgift-support / 电话 138****0000" />
      </label>
    </div>

    <div class="actions">
      <button class="ghost-button" type="button" :disabled="testing" @click="testConfig">
        {{ testing ? '测试中...' : '测试连接' }}
      </button>
      <button class="action-button" type="button" :disabled="loading" @click="saveConfig">
        {{ loading ? '保存中...' : '保存配置' }}
      </button>
    </div>

    <p v-if="message" class="message">{{ message }}</p>
  </section>
</template>

<style scoped>
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.hint { font-size: 12px; margin-top: 4px; }
.form-grid { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 14px; }
.field { display: grid; gap: 6px; }
.field.full { grid-column: span 2; }
.checkbox-field { align-items: center; grid-template-columns: 1fr auto; }
.input { border: 1px solid #ccc; border-radius: 10px; padding: 8px 10px; }
.actions { display: flex; gap: 8px; margin-top: 14px; }
.action-button { border: 0; border-radius: 10px; background: var(--color-primary); color: #fff; padding: 8px 12px; cursor: pointer; }
.ghost-button { border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); border-radius: 10px; background: transparent; color: var(--color-text-main); padding: 8px 12px; cursor: pointer; }
.message { color: var(--color-text-secondary); margin: 10px 0 0; }
.dimmed { opacity: 0.7; }
@media (max-width: 900px) {
  .form-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: span 1; }
}
</style>
