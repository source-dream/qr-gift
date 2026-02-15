<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'
import QRCode from 'qrcode'
import { useRouter } from 'vue-router'

import { createGift, getGiftQrcodeDownloadUrl } from '../api/modules/gift'
import { listRedPackets, type RedPacketItem } from '../api/modules/redPacket'

const router = useRouter()
const loading = shallowRef(false)
const message = shallowRef('')
const redPackets = shallowRef<RedPacketItem[]>([])
const claimUrl = shallowRef('')
const previewQrDataUrl = shallowRef('')
const createdGiftId = shallowRef(0)

const form = reactive({
  title: '',
  activate_at: '',
  expire_at: '',
  binding_mode: 'manual' as 'manual' | 'auto',
  dispatch_strategy: 'random' as 'amount_desc' | 'level_desc' | 'random',
  red_packet_ids: [] as number[],
  style_type: 'festival',
  auto_return_to_list: true,
})

const availablePackets = computed(() => redPackets.value.filter((item) => item.status === 'idle'))
const previewClass = computed(() => `preview-${form.style_type}`)

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

async function loadRedPackets(): Promise<void> {
  redPackets.value = await listRedPackets()
}

function buildPreviewContent(): string {
  const title = form.title.trim() || 'gift-preview'
  const strategy = form.dispatch_strategy
  return `https://preview.qr-gift.local/r/${encodeURIComponent(title)}?strategy=${strategy}`
}

async function generatePreviewQr(): Promise<void> {
  try {
    const content = claimUrl.value || buildPreviewContent()
    previewQrDataUrl.value = await QRCode.toDataURL(content, {
      width: 160,
      margin: 1,
      errorCorrectionLevel: 'M',
    })
  } catch {
    previewQrDataUrl.value = ''
  }
}

async function submitCreate(): Promise<void> {
  if (!form.title.trim()) {
    message.value = '请填写礼物名称'
    return
  }
  loading.value = true
  message.value = ''
  claimUrl.value = ''
  try {
    const result = await createGift({
      title: form.title,
      activate_at: form.activate_at || null,
      expire_at: form.expire_at || null,
      binding_mode: form.binding_mode,
      dispatch_strategy: form.dispatch_strategy,
      red_packet_ids: form.binding_mode === 'manual' ? form.red_packet_ids : [],
      style_type: form.style_type,
    })
    createdGiftId.value = result.id
    claimUrl.value = result.claim_url
    await generatePreviewQr()
    message.value = '礼物二维码创建成功'
    if (form.auto_return_to_list) {
      router.push('/gifts?created=1')
      return
    }
  } catch (error) {
    message.value = resolveErrorMessage(error, '创建失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRedPackets()
  generatePreviewQr()
})

watch(
  () => [form.title, form.dispatch_strategy, form.style_type],
  () => {
    generatePreviewQr()
  },
)

watch(
  () => claimUrl.value,
  () => {
    generatePreviewQr()
  },
)

function downloadQrCode(): void {
  if (!createdGiftId.value) {
    return
  }
  getGiftQrcodeDownloadUrl(createdGiftId.value)
    .then((url) => {
      const link = document.createElement('a')
      link.href = url
      link.target = '_blank'
      link.rel = 'noreferrer'
      link.click()
    })
    .catch((error) => {
      message.value = resolveErrorMessage(error, '二维码下载失败')
    })
}
</script>

<template>
  <section class="card-surface">
    <div class="head-row">
      <div>
        <h2 class="title">新建礼物二维码</h2>
        <p class="desc">单页分区配置：时间窗、派发策略、多红包绑定、样式预览。</p>
      </div>
      <button class="ghost-button" type="button" @click="router.push('/gifts')">返回列表</button>
    </div>

    <div class="form-grid">
      <label class="field full">
        <span>礼物名称</span>
        <input v-model="form.title" class="input" type="text" placeholder="新年红包礼物" />
      </label>

      <label class="field">
        <span>激活时间（可选）</span>
        <input v-model="form.activate_at" class="input" type="datetime-local" />
      </label>

      <label class="field">
        <span>失效时间（可选）</span>
        <input v-model="form.expire_at" class="input" type="datetime-local" />
      </label>

      <label class="field">
        <span>绑定规则</span>
        <select v-model="form.binding_mode" class="input">
          <option value="manual">手动多选红包</option>
          <option value="auto">自动绑定一条红包</option>
        </select>
      </label>

      <label class="field">
        <span>派发条件</span>
        <select v-model="form.dispatch_strategy" class="input">
          <option value="amount_desc">金额优先（先抢金额大）</option>
          <option value="level_desc">等级优先（等级高优先）</option>
          <option value="random">随机派发</option>
        </select>
      </label>

      <label class="field">
        <span>二维码样式</span>
        <select v-model="form.style_type" class="input">
          <option value="festival">节庆风格</option>
          <option value="simple">简洁风格</option>
          <option value="poster">海报风格</option>
        </select>
      </label>

      <div v-if="form.binding_mode === 'manual'" class="field full">
        <span>红包池多选（仅显示可用红包）</span>
        <div class="packet-grid">
          <label v-for="item in availablePackets" :key="item.id" class="packet-item">
            <input v-model="form.red_packet_ids" type="checkbox" :value="item.id" />
            <span>#{{ item.id }} 金额 {{ item.amount }} 等级 {{ item.level }}</span>
          </label>
        </div>
      </div>

      <div class="field full preview-field">
        <span>{{ claimUrl ? '真实领取二维码' : '二维码样式预览（创建前示意）' }}</span>
        <div class="preview-card" :class="previewClass">
          <img v-if="previewQrDataUrl" class="preview-qr" :src="previewQrDataUrl" alt="二维码预览" />
          <div v-else class="preview-qr preview-qr-fallback">生成中</div>
          <p class="preview-title">{{ form.title || '礼物二维码预览' }}</p>
          <p class="preview-desc">策略：{{ form.dispatch_strategy }}</p>
        </div>
      </div>

      <label class="field full option-field">
        <input v-model="form.auto_return_to_list" type="checkbox" />
        <span>创建成功后自动返回列表</span>
      </label>
    </div>

    <button class="action-button" type="button" :disabled="loading" @click="submitCreate">
      {{ loading ? '创建中...' : '创建礼物二维码' }}
    </button>

    <button v-if="claimUrl" class="ghost-button" type="button" @click="downloadQrCode">下载二维码</button>

    <p v-if="message" class="message">{{ message }}</p>
    <p v-if="claimUrl" class="claim-url">领取地址：{{ claimUrl }}</p>
  </section>
</template>

<style scoped>
.head-row { align-items: center; display: flex; justify-content: space-between; gap: 8px; }
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.form-grid { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 14px; }
.field { display: grid; gap: 6px; }
.field.full { grid-column: span 2; }
.input { border: 1px solid #ccc; border-radius: 10px; padding: 8px 10px; }
.packet-grid { display: grid; gap: 6px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 4px; }
.packet-item { align-items: center; border: 1px solid #e5dfd7; border-radius: 8px; display: flex; gap: 6px; padding: 6px 8px; }
.preview-field { margin-top: 2px; }
.preview-card { align-items: center; border-radius: 12px; display: flex; flex-direction: column; gap: 6px; min-height: 150px; justify-content: center; padding: 10px; }
.preview-festival { background: linear-gradient(135deg, #fff3ef, #ffe4db); border: 1px solid #f5c7b8; }
.preview-simple { background: #f5f5f5; border: 1px solid #ddd; }
.preview-poster { background: linear-gradient(135deg, #fff6e8, #ffe9bf); border: 1px solid #efcf91; }
.preview-qr { background: #fff; border: 1px dashed #aaa; border-radius: 8px; height: 86px; padding: 3px; width: 86px; }
.preview-qr-fallback { align-items: center; display: flex; font-weight: 700; justify-content: center; }
.preview-title, .preview-desc { margin: 0; }
.action-button { border: 0; border-radius: 10px; background: var(--color-primary); color: #fff; margin-top: 12px; padding: 8px 12px; cursor: pointer; }
.ghost-button { border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); border-radius: 10px; background: transparent; color: var(--color-text-main); cursor: pointer; padding: 8px 12px; }
.option-field { align-items: center; display: flex; gap: 8px; margin-top: 4px; }
.message { color: var(--color-text-secondary); margin: 10px 0 0; }
.claim-url { color: var(--color-primary-deep); margin: 8px 0 0; word-break: break-all; }
@media (max-width: 900px) {
  .head-row { align-items: flex-start; flex-direction: column; }
  .form-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: span 1; }
  .packet-grid { grid-template-columns: 1fr; }
}
</style>
