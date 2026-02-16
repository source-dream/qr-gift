<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'
import QRCode from 'qrcode'
import { useRoute, useRouter } from 'vue-router'

import {
  activateGift,
  deleteGift,
  disableGift,
  getGiftById,
  getGiftQrcodeDownloadUrl,
  listGifts,
  regenerateGiftQrcode,
  updateGift,
  type GiftItem,
} from '../api/modules/gift'
import { listRedPackets, type RedPacketItem } from '../api/modules/redPacket'

const router = useRouter()
const route = useRoute()
const message = shallowRef('')
const list = shallowRef<GiftItem[]>([])
const drawerVisible = shallowRef(false)
const loadingBase = shallowRef(false)
const loadingPackets = shallowRef(false)
const loadingQrPreview = shallowRef(false)
const saving = shallowRef(false)
const deleting = shallowRef(false)
const regenerating = shallowRef(false)
const confirmVisible = shallowRef(false)
const editingId = shallowRef<number | null>(null)
const redPackets = shallowRef<RedPacketItem[]>([])
const packetsLoaded = shallowRef(false)
const previewQrDataUrl = shallowRef('')
const realClaimUrl = shallowRef('')
let detailRequestToken = 0

const form = reactive({
  title: '',
  activate_at: '',
  expire_at: '',
  binding_mode: 'manual' as 'manual' | 'auto',
  dispatch_strategy: 'random' as 'amount_desc' | 'level_desc' | 'random',
  red_packet_ids: [] as number[],
  style_type: 'festival',
})

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

function statusLabel(status: string): string {
  if (status === 'draft') {
    return '草稿'
  }
  if (status === 'active') {
    return '启用中'
  }
  if (status === 'disabled') {
    return '已停用'
  }
  if (status === 'claimed') {
    return '已领取'
  }
  if (status === 'expired') {
    return '已过期'
  }
  return status || '-'
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

function dispatchLabel(value: string): string {
  if (value === 'amount_desc') {
    return '金额优先'
  }
  if (value === 'level_desc') {
    return '等级优先'
  }
  if (value === 'random') {
    return '随机派发'
  }
  return value || '-'
}

function styleLabel(value: string): string {
  if (value === 'festival') {
    return '节庆'
  }
  if (value === 'simple') {
    return '简洁'
  }
  if (value === 'poster') {
    return '海报'
  }
  return value || '-'
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

const availablePackets = computed(() => redPackets.value.filter((item) => item.status === 'idle'))

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

async function loadList(): Promise<void> {
  list.value = await listGifts()
}

async function loadPackets(giftId: number): Promise<void> {
  if (packetsLoaded.value || loadingPackets.value || editingId.value !== giftId) {
    return
  }
  loadingPackets.value = true
  const token = detailRequestToken
  try {
    const packets = await listRedPackets()
    if (token !== detailRequestToken || editingId.value !== giftId) {
      return
    }
    redPackets.value = packets
    packetsLoaded.value = true
  } catch (error) {
    if (token !== detailRequestToken || editingId.value !== giftId) {
      return
    }
    message.value = resolveErrorMessage(error, '红包池加载失败')
  } finally {
    if (token === detailRequestToken && editingId.value === giftId) {
      loadingPackets.value = false
    }
  }
}

async function loadDetailBase(giftId: number): Promise<void> {
  const token = ++detailRequestToken
  loadingBase.value = true
  loadingPackets.value = false
  packetsLoaded.value = false
  redPackets.value = []
  try {
    const gift = await getGiftById(giftId)
    if (token !== detailRequestToken || editingId.value !== giftId) {
      return
    }
    form.title = gift.title
    form.activate_at = toDatetimeLocal(gift.activate_at)
    form.expire_at = toDatetimeLocal(gift.expire_at)
    form.binding_mode = gift.binding_mode
    form.dispatch_strategy = gift.dispatch_strategy
    form.red_packet_ids = [...gift.red_packet_ids]
    form.style_type = gift.style_type
    realClaimUrl.value = gift.claim_url || ''
    void generatePreviewQr()
    if (form.binding_mode === 'manual') {
      void loadPackets(giftId)
    }
  } catch (error) {
    if (token !== detailRequestToken || editingId.value !== giftId) {
      return
    }
    message.value = resolveErrorMessage(error, '加载礼物二维码详情失败')
    drawerVisible.value = false
    editingId.value = null
  } finally {
    if (token === detailRequestToken && editingId.value === giftId) {
      loadingBase.value = false
    }
  }
}

function openEditDrawer(giftId: number): void {
  if (saving.value || deleting.value || regenerating.value) {
    return
  }
  form.title = ''
  form.activate_at = ''
  form.expire_at = ''
  form.binding_mode = 'manual'
  form.dispatch_strategy = 'random'
  form.red_packet_ids = []
  form.style_type = 'festival'
  previewQrDataUrl.value = ''
  realClaimUrl.value = ''
  editingId.value = giftId
  drawerVisible.value = true
  void loadDetailBase(giftId)
}

function closeDrawer(): void {
  if (saving.value || deleting.value || regenerating.value) {
    return
  }
  confirmVisible.value = false
  drawerVisible.value = false
  editingId.value = null
  loadingBase.value = false
  loadingPackets.value = false
  loadingQrPreview.value = false
}

async function changeStatus(id: number, next: 'activate' | 'disable'): Promise<void> {
  try {
    if (next === 'activate') {
      await activateGift(id)
    } else {
      await disableGift(id)
    }
    await loadList()
  } catch (error) {
    message.value = resolveErrorMessage(error, '状态更新失败')
  }
}

async function downloadQrImage(id: number): Promise<void> {
  try {
    const url = await getGiftQrcodeDownloadUrl(id)
    const link = document.createElement('a')
    link.href = url
    link.target = '_blank'
    link.rel = 'noreferrer'
    link.click()
  } catch (error) {
    message.value = resolveErrorMessage(error, '二维码下载失败')
  }
}

async function generatePreviewQr(): Promise<void> {
  loadingQrPreview.value = true
  try {
    const content = realClaimUrl.value || `https://preview.qr-gift.local/r/${encodeURIComponent(form.title || 'gift-preview')}`
    previewQrDataUrl.value = await QRCode.toDataURL(content, {
      width: 160,
      margin: 1,
      errorCorrectionLevel: 'M',
    })
  } catch {
    previewQrDataUrl.value = ''
  } finally {
    loadingQrPreview.value = false
  }
}

function removeSelectedPacket(packetId: number): void {
  form.red_packet_ids = form.red_packet_ids.filter((id) => id !== packetId)
}

async function downloadDrawerQrCode(): Promise<void> {
  if (!editingId.value) {
    return
  }
  await downloadQrImage(editingId.value)
}

async function regenerateQrCode(): Promise<void> {
  if (!editingId.value) {
    return
  }
  regenerating.value = true
  try {
    const result = await regenerateGiftQrcode(editingId.value)
    realClaimUrl.value = result.claim_url
    await generatePreviewQr()
    message.value = '真实二维码已重新生成'
    await loadList()
  } catch (error) {
    message.value = resolveErrorMessage(error, '重新生成二维码失败')
  } finally {
    regenerating.value = false
  }
}

async function submitEdit(): Promise<void> {
  if (!editingId.value) {
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
  try {
    await updateGift(editingId.value, {
      title: form.title,
      activate_at: form.activate_at || null,
      expire_at: form.expire_at || null,
      binding_mode: form.binding_mode,
      dispatch_strategy: form.dispatch_strategy,
      red_packet_ids: form.binding_mode === 'manual' ? form.red_packet_ids : [],
      style_type: form.style_type,
    })
    message.value = '礼物二维码更新成功'
    await loadList()
    await loadDetailBase(editingId.value)
  } catch (error) {
    message.value = resolveErrorMessage(error, '更新失败')
  } finally {
    saving.value = false
  }
}

function openDeleteConfirm(): void {
  if (!editingId.value || deleting.value || saving.value) {
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

async function removeGift(): Promise<void> {
  if (!editingId.value) {
    return
  }
  deleting.value = true
  try {
    await deleteGift(editingId.value)
    message.value = '礼物二维码已删除，列表已刷新'
    confirmVisible.value = false
    drawerVisible.value = false
    editingId.value = null
    await loadList()
  } catch (error) {
    message.value = resolveErrorMessage(error, '删除失败')
  } finally {
    deleting.value = false
  }
}

watch(
  () => [form.title, form.dispatch_strategy, form.style_type],
  () => {
    if (drawerVisible.value) {
      void generatePreviewQr()
    }
  },
)

watch(
  () => form.binding_mode,
  (mode) => {
    if (mode !== 'manual' || !drawerVisible.value || !editingId.value) {
      return
    }
    void loadPackets(editingId.value)
  },
)

onMounted(async () => {
  await loadList()
  if (route.query.created === '1') {
    message.value = '礼物二维码创建成功，列表已刷新'
    router.replace('/gifts')
    return
  }
  if (route.query.updated === '1') {
    message.value = '礼物二维码更新成功，列表已刷新'
    router.replace('/gifts')
    return
  }
  if (route.query.deleted === '1') {
    message.value = '礼物二维码已删除，列表已刷新'
    router.replace('/gifts')
  }
})
</script>

<template>
  <section class="card-surface">
    <div class="head-row">
      <div>
        <h2 class="title">礼物二维码</h2>
        <p class="desc">查看礼物列表、状态与绑定信息。</p>
      </div>
      <button class="action-button" type="button" @click="router.push('/gifts/create')">新建礼物二维码</button>
    </div>

    <p v-if="message" class="message">{{ message }}</p>

    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>状态</th>
            <th>有效期</th>
            <th>绑定数量</th>
            <th>派发条件</th>
            <th>样式</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in list"
            :key="item.id"
            class="clickable-row"
            :class="{ active: drawerVisible && editingId === item.id }"
            @click="openEditDrawer(item.id)"
          >
            <td>{{ item.id }}</td>
            <td>{{ item.title }}</td>
            <td>{{ statusLabel(item.status) }}</td>
            <td>{{ item.activate_at || '-' }} ~ {{ item.expire_at || '-' }}</td>
            <td>{{ item.binding_count }}</td>
            <td>{{ dispatchLabel(item.dispatch_strategy) }}</td>
            <td>{{ styleLabel(item.style_type) }}</td>
            <td class="actions-cell">
              <button class="mini-button ghost" type="button" @click.stop="openEditDrawer(item.id)">编辑</button>
              <button class="mini-button ghost" type="button" @click.stop="downloadQrImage(item.id)">下载二维码</button>
              <button class="mini-button" type="button" @click.stop="changeStatus(item.id, 'activate')">启用</button>
              <button class="mini-button ghost" type="button" @click.stop="changeStatus(item.id, 'disable')">停用</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="drawerVisible" class="drawer-mask" @click="closeDrawer">
      <aside class="drawer" role="dialog" aria-modal="true" @click.stop>
        <header class="drawer-head">
          <div>
            <h3 class="drawer-title">编辑礼物二维码</h3>
            <p class="drawer-desc">点击整行可快速进入编辑，保存后列表即时刷新。</p>
          </div>
          <button class="drawer-btn secondary" type="button" :disabled="saving || deleting || regenerating" @click="closeDrawer">关闭</button>
        </header>

        <p v-if="loadingBase" class="message">基础信息加载中...</p>

        <div v-if="!loadingBase" class="form-grid">
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
            <p v-if="loadingPackets" class="hint">红包池加载中...</p>
            <div v-else class="packet-grid">
              <label v-for="item in availablePackets" :key="item.id" class="packet-item">
                <input v-model="form.red_packet_ids" type="checkbox" :value="item.id" />
                <span>#{{ item.id }} 金额 {{ item.amount }} 等级 {{ item.level }} 状态 {{ packetStatusLabel(item.status) }}</span>
              </label>
            </div>
          </div>

          <div class="field full preview-field">
            <span>真实领取二维码</span>
            <div class="preview-card" :class="previewClass">
              <img v-if="qrDisplaySrc" class="preview-qr" :src="qrDisplaySrc" alt="二维码预览" />
              <div v-else class="preview-qr preview-qr-fallback">{{ loadingQrPreview ? '预览生成中' : '预览不可用' }}</div>
              <p class="preview-title">{{ form.title || '礼物二维码预览' }}</p>
              <p class="preview-desc">策略：{{ dispatchLabel(form.dispatch_strategy) }}</p>
            </div>
            <div class="drawer-actions-inline">
              <button class="drawer-btn secondary" type="button" :disabled="regenerating || saving" @click="downloadDrawerQrCode">下载二维码</button>
              <button class="drawer-btn secondary" type="button" :disabled="regenerating || saving" @click="regenerateQrCode">
                {{ regenerating ? '生成中...' : '重新生成二维码' }}
              </button>
            </div>
            <p v-if="realClaimUrl" class="claim-url">领取地址：{{ realClaimUrl }}</p>
          </div>
        </div>

        <div class="drawer-foot">
          <button class="drawer-btn primary" type="button" :disabled="saving || loadingBase || deleting" @click="submitEdit">
            {{ saving ? '更新中...' : '保存更新' }}
          </button>
          <button class="drawer-btn danger" type="button" :disabled="deleting || saving || loadingBase" @click="openDeleteConfirm">
            {{ deleting ? '删除中...' : '删除礼物二维码' }}
          </button>
        </div>

        <div v-if="confirmVisible" class="confirm-mask" @click="closeDeleteConfirm">
          <div class="confirm-dialog" role="dialog" aria-modal="true" @click.stop>
            <h3 class="confirm-title">确认删除礼物二维码？</h3>
            <p class="confirm-desc">删除后将自动解绑已绑定红包，且无法恢复。</p>
            <div class="confirm-actions">
              <button class="drawer-btn secondary" type="button" :disabled="deleting" @click="closeDeleteConfirm">取消</button>
              <button class="drawer-btn danger" type="button" :disabled="deleting" @click="removeGift">
                {{ deleting ? '删除中...' : '确认删除' }}
              </button>
            </div>
          </div>
        </div>
      </aside>
    </div>

  </section>
</template>

<style scoped>
.head-row { align-items: center; display: flex; gap: 10px; justify-content: space-between; }
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.action-button { border: 0; border-radius: 10px; background: var(--color-primary); color: #fff; margin-top: 12px; padding: 8px 12px; cursor: pointer; }
.head-row .action-button { margin-top: 0; }
.message { color: var(--color-text-secondary); margin: 10px 0 0; }
.table-wrap { margin-top: 14px; overflow: auto; }
.table {
  border-collapse: collapse;
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 24%, transparent);
  border-radius: 12px;
  overflow: hidden;
  width: 100%;
}
.table thead th {
  background: color-mix(in oklab, var(--color-primary) 8%, var(--color-surface) 92%);
}
.table tbody tr:hover {
  background: color-mix(in oklab, var(--color-primary) 6%, var(--color-surface) 94%);
}
.clickable-row { cursor: pointer; }
.clickable-row.active {
  background: color-mix(in oklab, var(--color-primary) 10%, var(--color-surface) 90%);
}
.table th, .table td {
  border-bottom: 1px solid color-mix(in oklab, var(--color-text-secondary) 22%, transparent);
  color: var(--color-text-main);
  padding: 8px;
  text-align: left;
}
.actions-cell { display: flex; gap: 6px; }
.mini-button { border: 0; border-radius: 8px; background: var(--color-primary); color: #fff; padding: 4px 8px; cursor: pointer; }
.mini-button.ghost { background: transparent; border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); color: var(--color-text-main); }
.drawer-btn {
  border: 0;
  border-radius: 10px;
  cursor: pointer;
  min-height: 36px;
  padding: 8px 12px;
}

.drawer-btn.primary {
  background: var(--color-primary);
  color: #fff;
}

.drawer-btn.secondary {
  background: color-mix(in oklab, var(--color-surface) 86%, var(--color-bg) 14%);
  border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%);
  color: var(--color-text-main);
}

.drawer-btn.danger {
  background: color-mix(in oklab, var(--color-primary-deep) 82%, #7a1f18 18%);
  color: #fff;
}

.drawer-btn:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.drawer-mask {
  background: rgba(15, 10, 7, 0.4);
  inset: 0;
  position: fixed;
  z-index: 70;
}

.drawer {
  background: var(--color-surface);
  box-shadow: -10px 0 30px color-mix(in oklab, #000 32%, transparent);
  height: 100%;
  overflow: auto;
  padding: 14px;
  position: absolute;
  right: 0;
  top: 0;
  width: min(720px, 100%);
}

.drawer-head {
  align-items: flex-start;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.drawer-title { margin: 0; }
.drawer-desc { margin: 6px 0 0; color: var(--color-text-secondary); }

.form-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 14px;
}

.field { display: grid; gap: 6px; }
.field.full { grid-column: span 2; }

.input {
  background: color-mix(in oklab, var(--color-surface) 82%, var(--color-bg) 18%);
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 28%, transparent);
  border-radius: 10px;
  color: var(--color-text-main);
  padding: 8px 10px;
}

.packet-grid { display: grid; gap: 6px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 4px; }

.packet-item {
  align-items: center;
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 24%, transparent);
  border-radius: 8px;
  display: flex;
  gap: 6px;
  padding: 6px 8px;
}

.selected-grid { display: grid; gap: 6px; margin: 4px 0 10px; }
.hint { color: var(--color-text-secondary); margin: 6px 0 0; }

.selected-item {
  align-items: center;
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 24%, transparent);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px;
}

.mini-remove {
  border: 0;
  border-radius: 8px;
  background: color-mix(in oklab, var(--color-primary) 12%, var(--color-surface) 88%);
  color: color-mix(in oklab, var(--color-primary-deep) 82%, var(--color-text-main) 18%);
  cursor: pointer;
  padding: 4px 8px;
}

.preview-field { margin-top: 2px; }

.preview-card {
  align-items: center;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 150px;
  justify-content: center;
  padding: 10px;
}

.preview-festival {
  background: linear-gradient(
    135deg,
    color-mix(in oklab, var(--color-primary) 8%, var(--color-surface) 92%),
    color-mix(in oklab, var(--color-accent) 12%, var(--color-surface) 88%)
  );
  border: 1px solid color-mix(in oklab, var(--color-primary) 28%, transparent);
}

.preview-simple {
  background: color-mix(in oklab, var(--color-surface) 84%, var(--color-bg) 16%);
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 24%, transparent);
}

.preview-poster {
  background: linear-gradient(
    135deg,
    color-mix(in oklab, var(--color-gold) 16%, var(--color-surface) 84%),
    color-mix(in oklab, var(--color-accent) 18%, var(--color-surface) 82%)
  );
  border: 1px solid color-mix(in oklab, var(--color-gold) 28%, transparent);
}

.preview-qr {
  background: var(--color-surface);
  border: 1px dashed color-mix(in oklab, var(--color-text-secondary) 40%, transparent);
  border-radius: 8px;
  height: 86px;
  padding: 3px;
  width: 86px;
}

.preview-qr-fallback { align-items: center; display: flex; font-weight: 700; justify-content: center; }
.preview-title, .preview-desc { margin: 0; }
.claim-url { color: var(--color-primary-deep); margin: 8px 0 0; word-break: break-all; }

.drawer-actions-inline { display: flex; gap: 8px; margin-top: 10px; }

.drawer-foot {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.confirm-mask {
  align-items: center;
  background: rgba(26, 18, 12, 0.42);
  display: flex;
  inset: 0;
  justify-content: center;
  position: fixed;
  z-index: 80;
}

.confirm-dialog {
  background: var(--color-surface);
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
  .form-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: span 1; }
  .packet-grid { grid-template-columns: 1fr; }
  .drawer-foot { flex-direction: column; }
}
</style>
