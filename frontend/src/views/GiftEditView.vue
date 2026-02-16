<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'
import QRCode from 'qrcode'
import { useRoute, useRouter } from 'vue-router'

import {
  deleteGift,
  getGiftById,
  getGiftQrcodeDownloadUrl,
  regenerateGiftQrcode,
  updateGift,
} from '../api/modules/gift'
import { listRedPackets, type RedPacketItem } from '../api/modules/redPacket'

const router = useRouter()
const route = useRoute()
const loading = shallowRef(false)
const saving = shallowRef(false)
const deleting = shallowRef(false)
const regenerating = shallowRef(false)
const confirmVisible = shallowRef(false)
const message = shallowRef('')
const redPackets = shallowRef<RedPacketItem[]>([])
const previewQrDataUrl = shallowRef('')
const realClaimUrl = shallowRef('')

const giftId = computed(() => Number(route.params.id || 0))

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

const availablePackets = computed(() => {
  return redPackets.value.filter((item) => item.status === 'idle')
})

const selectedPackets = computed(() => {
  const packetMap = new Map(redPackets.value.map((item) => [item.id, item]))
  return form.red_packet_ids.map((id) => {
    const found = packetMap.get(id)
    if (found) {
      return found
    }
    return {
      id,
      title: `红包 #${id}`,
      amount: 0,
      level: 1,
      category_name: '',
      category_code: '',
      tags: [],
      content_type: 'url' as const,
      content_value: '',
      content_image_url: '',
      status: 'bound',
      meta: {},
      available_from: null,
      available_to: null,
    }
  })
})

const previewClass = computed(() => `preview-${form.style_type}`)
const qrDisplaySrc = computed(() => previewQrDataUrl.value)

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

function packetStatusLabel(status: string): string {
  if (status === 'idle') {
    return '可用'
  }
  if (status === 'bound') {
    return '已绑定'
  }
  if (status === 'claimed') {
    return '已领取'
  }
  if (status === 'disabled') {
    return '已停用'
  }
  if (status === 'deleted') {
    return '已删除'
  }
  return status || '-'
}

function toDatetimeLocal(value: string | null): string {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

async function loadData(): Promise<void> {
  if (!giftId.value) {
    message.value = '礼物二维码 ID 无效'
    return
  }
  loading.value = true
  message.value = ''
  try {
    const [gift, packets] = await Promise.all([getGiftById(giftId.value), listRedPackets()])
    redPackets.value = packets
    form.title = gift.title
    form.activate_at = toDatetimeLocal(gift.activate_at)
    form.expire_at = toDatetimeLocal(gift.expire_at)
    form.binding_mode = gift.binding_mode
    form.dispatch_strategy = gift.dispatch_strategy
    form.red_packet_ids = [...gift.red_packet_ids]
    form.style_type = gift.style_type
    realClaimUrl.value = gift.claim_url || ''
    await generatePreviewQr()
  } catch (error) {
    message.value = resolveErrorMessage(error, '加载礼物二维码数据失败')
  } finally {
    loading.value = false
  }
}

function buildPreviewContent(): string {
  const title = form.title.trim() || 'gift-preview'
  const strategy = form.dispatch_strategy
  return `https://preview.qr-gift.local/r/${encodeURIComponent(title)}?strategy=${strategy}`
}

async function generatePreviewQr(): Promise<void> {
  try {
    const content = realClaimUrl.value || buildPreviewContent()
    previewQrDataUrl.value = await QRCode.toDataURL(content, {
      width: 160,
      margin: 1,
      errorCorrectionLevel: 'M',
    })
  } catch {
    previewQrDataUrl.value = ''
  }
}

function downloadQrCode(): void {
  if (!giftId.value) {
    return
  }
  getGiftQrcodeDownloadUrl(giftId.value)
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

async function regenerateQrCode(): Promise<void> {
  if (!giftId.value) {
    message.value = '礼物二维码 ID 无效'
    return
  }
  regenerating.value = true
  message.value = ''
  try {
    const result = await regenerateGiftQrcode(giftId.value)
    realClaimUrl.value = result.claim_url
    await generatePreviewQr()
    message.value = '真实二维码已重新生成'
  } catch (error) {
    message.value = resolveErrorMessage(error, '重新生成二维码失败')
  } finally {
    regenerating.value = false
  }
}

async function submitEdit(): Promise<void> {
  if (!giftId.value) {
    message.value = '礼物二维码 ID 无效'
    return
  }
  if (!form.title.trim()) {
    message.value = '请填写礼物名称'
    return
  }
  if (form.binding_mode === 'manual' && !form.red_packet_ids.length) {
    message.value = '手动绑定模式下请至少选择一个红包'
    return
  }

  saving.value = true
  message.value = ''
  try {
    await updateGift(giftId.value, {
      title: form.title,
      activate_at: form.activate_at || null,
      expire_at: form.expire_at || null,
      binding_mode: form.binding_mode,
      dispatch_strategy: form.dispatch_strategy,
      red_packet_ids: form.binding_mode === 'manual' ? form.red_packet_ids : [],
      style_type: form.style_type,
    })
    message.value = '礼物二维码更新成功'
    if (form.auto_return_to_list) {
      router.push('/gifts?updated=1')
      return
    }
    await loadData()
  } catch (error) {
    message.value = resolveErrorMessage(error, '更新失败')
  } finally {
    saving.value = false
  }
}

function removeSelectedPacket(packetId: number): void {
  form.red_packet_ids = form.red_packet_ids.filter((id) => id !== packetId)
}

async function removeGift(): Promise<void> {
  if (!giftId.value) {
    message.value = '礼物二维码 ID 无效'
    return
  }
  deleting.value = true
  message.value = ''
  try {
    await deleteGift(giftId.value)
    router.push('/gifts?deleted=1')
  } catch (error) {
    message.value = resolveErrorMessage(error, '删除失败')
  } finally {
    deleting.value = false
    confirmVisible.value = false
  }
}

function openDeleteConfirm(): void {
  if (deleting.value || saving.value) {
    return
  }
  confirmVisible.value = true
}

function closeDeleteConfirm(): void {
  if (deleting.value) {
    return
  }
  confirmVisible.value = false
}

onMounted(async () => {
  await loadData()
})

watch(
  () => [form.title, form.dispatch_strategy, form.style_type],
  () => {
    generatePreviewQr()
  },
)
</script>

<template>
  <section class="card-surface">
    <div class="head-row">
      <div>
        <h2 class="title">编辑礼物二维码</h2>
        <p class="desc">可继续调整时间窗、派发策略、绑定规则与绑定红包。</p>
      </div>
      <div class="head-actions">
        <button class="ghost-button" type="button" :disabled="regenerating || saving" @click="regenerateQrCode">
          {{ regenerating ? '生成中...' : '重新生成二维码' }}
        </button>
        <button class="danger-button" type="button" :disabled="deleting || saving" @click="openDeleteConfirm">
          {{ deleting ? '删除中...' : '删除礼物二维码' }}
        </button>
        <button class="ghost-button" type="button" @click="router.push('/gifts')">返回列表</button>
      </div>
    </div>

    <p v-if="loading" class="message">加载中...</p>

    <div v-else class="form-grid">
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
        <span>当前已绑定红包</span>
        <div class="selected-grid">
          <div v-for="item in selectedPackets" :key="`selected-${item.id}`" class="selected-item">
            <span>#{{ item.id }} 金额 {{ item.amount }} 等级 {{ item.level }} 状态 {{ packetStatusLabel(item.status) }}</span>
            <button class="mini-remove" type="button" @click="removeSelectedPacket(item.id)">移除</button>
          </div>
        </div>

        <span>红包池多选（仅显示未绑定且未领取红包）</span>
        <div class="packet-grid">
          <label v-for="item in availablePackets" :key="item.id" class="packet-item">
            <input v-model="form.red_packet_ids" type="checkbox" :value="item.id" />
            <span>#{{ item.id }} 金额 {{ item.amount }} 等级 {{ item.level }} 状态 {{ packetStatusLabel(item.status) }}</span>
          </label>
        </div>
        <p v-if="!availablePackets.length" class="hint">当前无可选红包（可能都已绑定或已领取）</p>
      </div>

      <div class="field full preview-field">
        <span>真实领取二维码</span>
        <div class="preview-card" :class="previewClass">
          <img v-if="qrDisplaySrc" class="preview-qr" :src="qrDisplaySrc" alt="二维码预览" />
          <div v-else class="preview-qr preview-qr-fallback">生成中</div>
          <p class="preview-title">{{ form.title || '礼物二维码预览' }}</p>
          <p class="preview-desc">策略：{{ form.dispatch_strategy }}</p>
        </div>
        <button class="ghost-button" type="button" @click="downloadQrCode">下载二维码</button>
        <p v-if="realClaimUrl" class="claim-url">领取地址：{{ realClaimUrl }}</p>
      </div>

      <label class="field full option-field">
        <input v-model="form.auto_return_to_list" type="checkbox" />
        <span>更新成功后自动返回列表</span>
      </label>
    </div>

    <button class="action-button" type="button" :disabled="saving || loading" @click="submitEdit">
      {{ saving ? '更新中...' : '保存更新' }}
    </button>

    <p v-if="message" class="message">{{ message }}</p>

    <div v-if="confirmVisible" class="confirm-mask" @click="closeDeleteConfirm">
      <div class="confirm-dialog" role="dialog" aria-modal="true" @click.stop>
        <h3 class="confirm-title">确认删除礼物二维码？</h3>
        <p class="confirm-desc">删除后将自动解绑已绑定红包，且无法恢复。</p>
        <div class="confirm-actions">
          <button class="ghost-button" type="button" :disabled="deleting" @click="closeDeleteConfirm">取消</button>
          <button class="danger-button" type="button" :disabled="deleting" @click="removeGift">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.head-row { align-items: center; display: flex; justify-content: space-between; gap: 8px; }
.head-actions { display: flex; gap: 8px; }
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.form-grid { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 14px; }
.field { display: grid; gap: 6px; }
.field.full { grid-column: span 2; }
.input { border: 1px solid #ccc; border-radius: 10px; padding: 8px 10px; }
.packet-grid { display: grid; gap: 6px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 4px; }
.packet-item { align-items: center; border: 1px solid #e5dfd7; border-radius: 8px; display: flex; gap: 6px; padding: 6px 8px; }
.selected-grid { display: grid; gap: 6px; margin: 4px 0 10px; }
.selected-item { align-items: center; border: 1px solid #e5dfd7; border-radius: 8px; display: flex; justify-content: space-between; gap: 8px; padding: 6px 8px; }
.mini-remove { border: 0; border-radius: 8px; background: #f7e4dc; color: #8a3d2a; cursor: pointer; padding: 4px 8px; }
.preview-field { margin-top: 2px; }
.preview-card { align-items: center; border-radius: 12px; display: flex; flex-direction: column; gap: 6px; min-height: 150px; justify-content: center; padding: 10px; }
.preview-festival { background: linear-gradient(135deg, #fff3ef, #ffe4db); border: 1px solid #f5c7b8; }
.preview-simple { background: #f5f5f5; border: 1px solid #ddd; }
.preview-poster { background: linear-gradient(135deg, #fff6e8, #ffe9bf); border: 1px solid #efcf91; }
.preview-qr { background: #fff; border: 1px dashed #aaa; border-radius: 8px; height: 86px; padding: 3px; width: 86px; }
.preview-qr-fallback { align-items: center; display: flex; font-weight: 700; justify-content: center; }
.preview-title, .preview-desc { margin: 0; }
.action-button { border: 0; border-radius: 10px; background: var(--color-primary); color: #fff; margin-top: 12px; padding: 8px 12px; cursor: pointer; }
.danger-button { border: 0; border-radius: 10px; background: #bf3f2b; color: #fff; cursor: pointer; padding: 8px 12px; }
.ghost-button { border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); border-radius: 10px; background: transparent; color: var(--color-text-main); cursor: pointer; padding: 8px 12px; }
.option-field { align-items: center; display: flex; gap: 8px; margin-top: 4px; }
.hint { color: var(--color-text-secondary); margin: 6px 0 0; }
.claim-url { color: var(--color-primary-deep); margin: 8px 0 0; word-break: break-all; }
.message { color: var(--color-text-secondary); margin: 10px 0 0; }
.confirm-mask {
  align-items: center;
  background: rgba(26, 18, 12, 0.42);
  display: flex;
  inset: 0;
  justify-content: center;
  position: fixed;
  z-index: 60;
}
.confirm-dialog {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 12px 36px rgba(21, 12, 8, 0.18);
  max-width: 420px;
  padding: 16px;
  width: calc(100% - 24px);
}
.confirm-title { margin: 0; }
.confirm-desc { color: var(--color-text-secondary); margin: 8px 0 0; }
.confirm-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 14px; }
@media (max-width: 900px) {
  .head-row { align-items: flex-start; flex-direction: column; }
  .head-actions { width: 100%; }
  .form-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: span 1; }
  .packet-grid { grid-template-columns: 1fr; }
}
</style>
