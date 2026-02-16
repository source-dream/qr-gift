<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, shallowRef, watch } from 'vue'

import {
  getClaimContact,
  listStorageChannels,
  testStorageChannel,
  updateClaimContact,
  updateStorageChannels,
  type StorageChannelItem,
} from '../api/modules/systemConfig'

const testing = shallowRef(false)
const channelsSaving = shallowRef(false)
const contactSaving = shallowRef(false)
const claimContact = shallowRef('')
const channels = shallowRef<StorageChannelItem[]>([])
const errorToast = reactive({
  visible: false,
  text: '',
})

const drawerVisible = shallowRef(false)
const editingId = shallowRef('')
const draggingId = shallowRef('')
const hoverId = shallowRef('')
const dragStartSnapshot = shallowRef<StorageChannelItem[] | null>(null)
const contactReady = shallowRef(false)
const overlayItem = shallowRef<StorageChannelItem | null>(null)
const overlayLeft = shallowRef(0)
const overlayTop = shallowRef(0)
const overlayWidth = shallowRef(0)
const overlayHeight = shallowRef(0)
const dragPointerId = shallowRef(-1)
const dragPointerOffsetY = shallowRef(0)
const pointerClientY = shallowRef(0)
const pointerCaptureElement = shallowRef<HTMLElement | null>(null)
const itemElementMap = new Map<string, HTMLElement>()
const pointerDownState = shallowRef<{
  id: string
  pointerId: number
  pointerType: string
  clientX: number
  clientY: number
} | null>(null)
const dragOverlayStyle = computed(() => ({
  left: `${overlayLeft.value}px`,
  top: `${overlayTop.value}px`,
  width: `${overlayWidth.value}px`,
  minHeight: `${overlayHeight.value}px`,
}))

const TOUCH_LONG_PRESS_MS = 130
const TOUCH_CANCEL_DISTANCE = 14
const EDGE_SCROLL_THRESHOLD = 84
const EDGE_SCROLL_MAX_SPEED = 18

let channelsPersistQueue: { next: StorageChannelItem[]; previous: StorageChannelItem[]; reason: string } | null = null
let contactSaveTimer: ReturnType<typeof setTimeout> | null = null
let longPressTimer: ReturnType<typeof setTimeout> | null = null
let reorderRafId = 0
let autoScrollRafId = 0
let autoScrollSpeed = 0
let pendingReorderY: number | null = null
let errorToastTimer: ReturnType<typeof setTimeout> | null = null

const testLogs = shallowRef<Array<{ id: number; status: 'success' | 'failed'; text: string; time: string }>>([])

function logDrag(_stage: string, _extra: Record<string, unknown> = {}): void {}

const editor = reactive<StorageChannelItem>({
  id: '',
  name: '',
  provider: 'local',
  enabled: true,
  priority: 100,
  bucket: '',
  base_url: '',
  storage_prefix: '',
  local_storage_dir: '/data/object-storage',
  minio_endpoint: '',
  minio_secure: false,
  minio_access_key: '',
  minio_secret_key: '',
  aliyun_oss_endpoint: '',
  aliyun_oss_region: '',
  aliyun_oss_access_key_id: '',
  aliyun_oss_access_key_secret: '',
  minio_access_key_set: false,
  minio_secret_key_set: false,
  aliyun_oss_access_key_id_set: false,
  aliyun_oss_access_key_secret_set: false,
})

const editorIsLocal = computed(() => editor.provider === 'local')
const editorIsMinio = computed(() => editor.provider === 'minio')

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

function showErrorToast(text: string): void {
  errorToast.text = text
  errorToast.visible = true
  if (errorToastTimer) {
    clearTimeout(errorToastTimer)
  }
  errorToastTimer = setTimeout(() => {
    errorToast.visible = false
  }, 3200)
}

function generateId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `channel-${Date.now()}`
}

function cloneChannels(list: StorageChannelItem[]): StorageChannelItem[] {
  return list.map((item) => ({ ...item }))
}

function normalizeChannelOrder(items: StorageChannelItem[]): StorageChannelItem[] {
  return items.map((item, idx) => ({ ...item, priority: 1000 - idx }))
}

function resetEditor(): void {
  editingId.value = ''
  editor.id = ''
  editor.name = ''
  editor.provider = 'local'
  editor.enabled = true
  editor.priority = 100
  editor.bucket = ''
  editor.base_url = ''
  editor.storage_prefix = ''
  editor.local_storage_dir = '/data/object-storage'
  editor.minio_endpoint = ''
  editor.minio_secure = false
  editor.minio_access_key = ''
  editor.minio_secret_key = ''
  editor.aliyun_oss_endpoint = ''
  editor.aliyun_oss_region = ''
  editor.aliyun_oss_access_key_id = ''
  editor.aliyun_oss_access_key_secret = ''
  editor.minio_access_key_set = false
  editor.minio_secret_key_set = false
  editor.aliyun_oss_access_key_id_set = false
  editor.aliyun_oss_access_key_secret_set = false
}

function appendTestLog(status: 'success' | 'failed', text: string): void {
  const now = new Date()
  const time = now.toLocaleString('zh-CN', { hour12: false })
  const record = {
    id: now.getTime() + Math.floor(Math.random() * 1000),
    status,
    text,
    time,
  }
  testLogs.value = [record, ...testLogs.value].slice(0, 20)
}

async function loadConfig(): Promise<void> {
  try {
    const [contact, channelList] = await Promise.all([getClaimContact(), listStorageChannels()])
    claimContact.value = contact.contact_text
    channels.value = normalizeChannelOrder(
      channelList
        .slice()
        .sort((a, b) => b.priority - a.priority)
        .map((item) => ({ ...item })),
    )
    contactReady.value = true
  } catch (error) {
    showErrorToast(resolveErrorMessage(error, '配置加载失败'))
  }
}

async function persistChannels(next: StorageChannelItem[], previous: StorageChannelItem[], reason: string): Promise<void> {
  if (channelsSaving.value) {
    channelsPersistQueue = {
      next: cloneChannels(next),
      previous: cloneChannels(previous),
      reason,
    }
    return
  }
  channelsSaving.value = true
  try {
    await updateStorageChannels(next.map((item) => ({ ...item })))
  } catch (error) {
    channels.value = cloneChannels(previous)
    showErrorToast(resolveErrorMessage(error, `渠道自动保存失败（${reason}）`))
  } finally {
    channelsSaving.value = false
    if (channelsPersistQueue) {
      const queued = channelsPersistQueue
      channelsPersistQueue = null
      await persistChannels(queued.next, queued.previous, queued.reason)
    }
  }
}

function applyChannelChange(reason: string, mutator: (current: StorageChannelItem[]) => StorageChannelItem[]): void {
  const previous = cloneChannels(channels.value)
  const next = normalizeChannelOrder(mutator(cloneChannels(channels.value)))
  channels.value = next
  void persistChannels(next, previous, reason)
}

function openCreateDrawer(): void {
  resetEditor()
  testLogs.value = []
  drawerVisible.value = true
}

function openEditDrawer(item: StorageChannelItem): void {
  editingId.value = item.id
  Object.assign(editor, { ...item })
  testLogs.value = []
  drawerVisible.value = true
}

function closeDrawer(): void {
  drawerVisible.value = false
  testLogs.value = []
  resetEditor()
}

function saveChannelDraft(): void {
  if (!editor.name.trim()) {
    showErrorToast('请填写渠道名称')
    return
  }

  if (editor.provider === 'local') {
    if (!editor.local_storage_dir.trim()) {
      showErrorToast('请填写本地存储目录')
      return
    }
  }

  if (editor.provider === 'minio') {
    if (!editor.minio_endpoint.trim()) {
      showErrorToast('请填写 MinIO Endpoint')
      return
    }
    if (!editor.bucket.trim()) {
      showErrorToast('请填写 MinIO Bucket')
      return
    }
    if (!editor.minio_access_key.trim() && !editor.minio_access_key_set) {
      showErrorToast('请填写 MinIO Access Key')
      return
    }
    if (!editor.minio_secret_key.trim() && !editor.minio_secret_key_set) {
      showErrorToast('请填写 MinIO Secret Key')
      return
    }
  }

  if (editor.provider === 'aliyun') {
    if (!editor.aliyun_oss_endpoint.trim()) {
      showErrorToast('请填写 OSS Endpoint')
      return
    }
    if (!editor.bucket.trim()) {
      showErrorToast('请填写 OSS Bucket')
      return
    }
    if (!editor.aliyun_oss_access_key_id.trim() && !editor.aliyun_oss_access_key_id_set) {
      showErrorToast('请填写 AccessKey ID')
      return
    }
    if (!editor.aliyun_oss_access_key_secret.trim() && !editor.aliyun_oss_access_key_secret_set) {
      showErrorToast('请填写 AccessKey Secret')
      return
    }
  }

  if (!editingId.value) {
    const created: StorageChannelItem = {
      ...editor,
      id: generateId(),
      name: editor.name.trim(),
      priority: 1000 - channels.value.length,
    }
    applyChannelChange('新增', (current) => [...current, created])
    closeDrawer()
    return
  }

  applyChannelChange('编辑', (current) =>
    current.map((item) =>
      item.id === editingId.value
        ? {
            ...item,
            ...editor,
            id: item.id,
            name: editor.name.trim(),
            minio_access_key: editor.minio_access_key || item.minio_access_key,
            minio_secret_key: editor.minio_secret_key || item.minio_secret_key,
            aliyun_oss_access_key_id: editor.aliyun_oss_access_key_id || item.aliyun_oss_access_key_id,
            aliyun_oss_access_key_secret:
              editor.aliyun_oss_access_key_secret || item.aliyun_oss_access_key_secret,
          }
        : item,
    ),
  )
  closeDrawer()
}

function removeChannel(id: string): void {
  applyChannelChange('删除', (current) => current.filter((item) => item.id !== id))
}

function toggleChannel(id: string): void {
  applyChannelChange('启停', (current) =>
    current.map((item) => (item.id === id ? { ...item, enabled: !item.enabled } : item)),
  )
}

function setChannelElement(id: string, element: Element | null): void {
  if (element instanceof HTMLElement) {
    itemElementMap.set(id, element)
    if (draggingId.value === id) {
      logDrag('setChannelElement:mount-dragging-item', { id })
    }
    return
  }
  if (draggingId.value === id) {
    logDrag('setChannelElement:unmount-dragging-item', { id })
  }
  itemElementMap.delete(id)
}

function clearLongPressTimer(): void {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

function stopAutoScrollLoop(): void {
  autoScrollSpeed = 0
  if (autoScrollRafId) {
    cancelAnimationFrame(autoScrollRafId)
    autoScrollRafId = 0
    logDrag('stopAutoScrollLoop')
  }
}

function scheduleReorder(clientY: number): void {
  pendingReorderY = clientY
  if (reorderRafId) {
    return
  }
  reorderRafId = requestAnimationFrame(() => {
    reorderRafId = 0
    if (!draggingId.value || pendingReorderY === null) {
      return
    }
    const dragging = channels.value.find((item) => item.id === draggingId.value)
    if (!dragging) {
      return
    }
    const others = channels.value.filter((item) => item.id !== draggingId.value)
    if (!others.length) {
      hoverId.value = ''
      return
    }

    let insertIndex = others.length
    let currentHover = others[others.length - 1]?.id || ''
    for (let index = 0; index < others.length; index += 1) {
      const row = others[index]
      if (!row) {
        continue
      }
      const element = itemElementMap.get(row.id)
      if (!element) {
        continue
      }
      const rect = element.getBoundingClientRect()
      const midline = rect.top + rect.height / 2
      if (pendingReorderY < midline) {
        insertIndex = index
        currentHover = row.id
        break
      }
    }

    const reordered = others.slice()
    reordered.splice(insertIndex, 0, dragging)
    const beforeOrder = channels.value.map((item) => item.id).join(',')
    const afterOrder = reordered.map((item) => item.id).join(',')
    hoverId.value = currentHover
    if (beforeOrder === afterOrder) {
      return
    }
    logDrag('reorder:swap', {
      clientY: pendingReorderY,
      insertIndex,
      currentHover,
      beforeOrder,
      afterOrder,
    })
    channels.value = normalizeChannelOrder(reordered)
  })
}

function startAutoScrollLoop(): void {
  if (autoScrollRafId) {
    return
  }
  autoScrollRafId = requestAnimationFrame(() => {
    autoScrollRafId = 0
    if (!draggingId.value || autoScrollSpeed === 0) {
      return
    }
    window.scrollBy({ top: autoScrollSpeed, behavior: 'auto' })
    if (pointerClientY.value) {
      scheduleReorder(pointerClientY.value)
    }
    startAutoScrollLoop()
  })
}

function updateAutoScroll(clientY: number): void {
  let speed = 0
  if (clientY < EDGE_SCROLL_THRESHOLD) {
    const ratio = (EDGE_SCROLL_THRESHOLD - clientY) / EDGE_SCROLL_THRESHOLD
    speed = -Math.round(ratio * EDGE_SCROLL_MAX_SPEED)
  } else if (clientY > window.innerHeight - EDGE_SCROLL_THRESHOLD) {
    const ratio = (clientY - (window.innerHeight - EDGE_SCROLL_THRESHOLD)) / EDGE_SCROLL_THRESHOLD
    speed = Math.round(ratio * EDGE_SCROLL_MAX_SPEED)
  }

  autoScrollSpeed = speed
  if (speed === 0) {
    stopAutoScrollLoop()
    return
  }
  logDrag('updateAutoScroll:start', { clientY, speed })
  startAutoScrollLoop()
}

function finishPointerDrag(): void {
  logDrag('finishPointerDrag:start')
  stopAutoScrollLoop()
  if (reorderRafId) {
    cancelAnimationFrame(reorderRafId)
    reorderRafId = 0
  }
  pendingReorderY = null

  const before = dragStartSnapshot.value
  const after = channels.value
  if (before) {
    const beforeOrder = before.map((item) => item.id).join(',')
    const afterOrder = after.map((item) => item.id).join(',')
    if (beforeOrder !== afterOrder) {
      void persistChannels(cloneChannels(after), before, '排序')
    }
  }

  draggingId.value = ''
  hoverId.value = ''
  dragStartSnapshot.value = null
  overlayItem.value = null
  const captureEl = pointerCaptureElement.value
  if (captureEl && dragPointerId.value >= 0 && captureEl.hasPointerCapture(dragPointerId.value)) {
    captureEl.releasePointerCapture(dragPointerId.value)
    logDrag('finishPointerDrag:releaseCapture', { releasedPointerId: dragPointerId.value })
  }
  pointerCaptureElement.value = null
  dragPointerId.value = -1
  dragPointerOffsetY.value = 0
  document.body.classList.remove('channel-dragging')
  logDrag('finishPointerDrag:end')
}

function beginPointerDrag(
  state: NonNullable<typeof pointerDownState.value>,
  sourceElement?: HTMLElement,
): void {
  logDrag('beginPointerDrag:attempt', {
    state: {
      id: state.id,
      pointerId: state.pointerId,
      pointerType: state.pointerType,
      clientX: state.clientX,
      clientY: state.clientY,
    },
    hasSourceElement: Boolean(sourceElement),
  })
  const element = itemElementMap.get(state.id)
  if (!element) {
    logDrag('beginPointerDrag:missing-item-element', { id: state.id })
    return
  }

  clearLongPressTimer()
  dragStartSnapshot.value = cloneChannels(channels.value)
  draggingId.value = state.id
  dragPointerId.value = state.pointerId
  const captureTarget = sourceElement ?? element
  if (!captureTarget.hasPointerCapture(state.pointerId)) {
    captureTarget.setPointerCapture(state.pointerId)
    logDrag('beginPointerDrag:setPointerCapture', {
      id: state.id,
      pointerId: state.pointerId,
      captureTargetConnected: captureTarget.isConnected,
    })
  }
  pointerCaptureElement.value = captureTarget
  pointerClientY.value = state.clientY

  const rect = element.getBoundingClientRect()
  overlayItem.value = channels.value.find((item) => item.id === state.id) ?? null
  overlayLeft.value = rect.left
  overlayTop.value = rect.top
  overlayWidth.value = rect.width
  overlayHeight.value = rect.height
  dragPointerOffsetY.value = state.clientY - rect.top
  document.body.classList.add('channel-dragging')
  logDrag('beginPointerDrag:started', {
    id: state.id,
    rectTop: rect.top,
    rectLeft: rect.left,
    rectHeight: rect.height,
    rectWidth: rect.width,
    offsetY: dragPointerOffsetY.value,
  })
}

function onChannelPointerDown(event: PointerEvent, id: string): void {
  logDrag('onChannelPointerDown:entry', {
    id,
    pointerType: event.pointerType,
    pointerId: event.pointerId,
    button: event.button,
    buttons: event.buttons,
    clientX: event.clientX,
    clientY: event.clientY,
  })
  if (event.button === 2) {
    logDrag('onChannelPointerDown:skip-right-button', { id })
    return
  }
  if (!(event.target instanceof HTMLElement)) {
    logDrag('onChannelPointerDown:skip-non-htmlelement', { id })
    return
  }
  if (event.target.closest('button, a, input, select, textarea, label')) {
    logDrag('onChannelPointerDown:skip-interactive-control', { id })
    return
  }
  const isTouch = event.pointerType === 'touch'
  if (!isTouch && event.cancelable) {
    event.preventDefault()
  }

  const sourceElement = event.currentTarget instanceof HTMLElement ? event.currentTarget : undefined

  pointerDownState.value = {
    id,
    pointerId: event.pointerId,
    pointerType: event.pointerType || 'mouse',
    clientX: event.clientX,
    clientY: event.clientY,
  }
  logDrag('onChannelPointerDown:state-set', {
    id,
    isTouch,
    pointerId: event.pointerId,
  })

  if (!isTouch) {
    logDrag('onChannelPointerDown:desktop-begin', { id })
    beginPointerDrag(pointerDownState.value, sourceElement)
    return
  }

  clearLongPressTimer()
  longPressTimer = setTimeout(() => {
    const pending = pointerDownState.value
    if (!pending || pending.id !== id || pending.pointerId !== event.pointerId) {
      logDrag('onChannelPointerDown:long-press-cancelled', { id, pointerId: event.pointerId })
      return
    }
    logDrag('onChannelPointerDown:long-press-begin', { id, pointerId: event.pointerId })
    beginPointerDrag(pending, sourceElement)
  }, TOUCH_LONG_PRESS_MS)
}

function onWindowPointerMove(event: PointerEvent): void {
  const pending = pointerDownState.value
  if (pending && !draggingId.value && pending.pointerId === event.pointerId) {
    if (pending.pointerType === 'touch') {
      const dx = event.clientX - pending.clientX
      const dy = event.clientY - pending.clientY
      if (Math.hypot(dx, dy) > TOUCH_CANCEL_DISTANCE) {
        clearLongPressTimer()
        pointerDownState.value = null
      }
    }
  }

  if (!draggingId.value || dragPointerId.value !== event.pointerId) {
    return
  }

  if (event.cancelable) {
    event.preventDefault()
  }
  pointerClientY.value = event.clientY
  overlayTop.value = event.clientY - dragPointerOffsetY.value
  logDrag('onWindowPointerMove:dragging', {
    pointerId: event.pointerId,
    pointerType: event.pointerType,
    clientY: event.clientY,
    overlayTop: overlayTop.value,
  })
  scheduleReorder(event.clientY)
  updateAutoScroll(event.clientY)
}

function onWindowPointerUpOrCancel(event: PointerEvent): void {
  logDrag('onWindowPointerUpOrCancel:entry', {
    pointerId: event.pointerId,
    pointerType: event.pointerType,
    draggingId: draggingId.value,
    dragPointerId: dragPointerId.value,
  })
  if (pointerDownState.value?.pointerId === event.pointerId) {
    clearLongPressTimer()
    pointerDownState.value = null
    logDrag('onWindowPointerUpOrCancel:clear-pointer-down', { pointerId: event.pointerId })
  }
  if (!draggingId.value || dragPointerId.value !== event.pointerId) {
    logDrag('onWindowPointerUpOrCancel:skip-not-active-drag', { pointerId: event.pointerId })
    return
  }
  logDrag('onWindowPointerUpOrCancel:finish-drag', { pointerId: event.pointerId })
  finishPointerDrag()
}

async function testDraft(): Promise<void> {
  testing.value = true
  try {
    await testStorageChannel({ ...editor })
    appendTestLog('success', '连接测试通过')
  } catch (error) {
    const detail = resolveErrorMessage(error, '连接测试失败')
    showErrorToast(detail)
    appendTestLog('failed', detail)
  } finally {
    testing.value = false
  }
}

async function saveClaimContactDebounced(value: string): Promise<void> {
  contactSaving.value = true
  try {
    await updateClaimContact(value)
  } catch (error) {
    showErrorToast(resolveErrorMessage(error, '联系方式自动保存失败'))
  } finally {
    contactSaving.value = false
  }
}

watch(
  () => claimContact.value,
  (value, oldValue) => {
    if (!contactReady.value || value === oldValue) {
      return
    }
    if (contactSaveTimer) {
      clearTimeout(contactSaveTimer)
    }
    contactSaveTimer = setTimeout(() => {
      void saveClaimContactDebounced(value)
    }, 700)
  },
)

onBeforeUnmount(() => {
  if (contactSaveTimer) {
    clearTimeout(contactSaveTimer)
  }
  if (errorToastTimer) {
    clearTimeout(errorToastTimer)
  }
  clearLongPressTimer()
  stopAutoScrollLoop()
  if (reorderRafId) {
    cancelAnimationFrame(reorderRafId)
  }
  window.removeEventListener('pointermove', onWindowPointerMove)
  window.removeEventListener('pointerup', onWindowPointerUpOrCancel)
  window.removeEventListener('pointercancel', onWindowPointerUpOrCancel)
  document.body.classList.remove('channel-dragging')
})

onMounted(() => {
  window.addEventListener('pointermove', onWindowPointerMove, { passive: false })
  window.addEventListener('pointerup', onWindowPointerUpOrCancel)
  window.addEventListener('pointercancel', onWindowPointerUpOrCancel)
  loadConfig()
})
</script>

<template>
  <section class="card-surface">
    <div v-if="errorToast.visible" class="toast-error">{{ errorToast.text }}</div>
    <div class="top-row">
      <div>
        <h2 class="title">系统配置</h2>
        <p class="desc">存储渠道支持拖拽排序，列表越靠上优先级越高。</p>
        <p class="desc hint" v-if="channelsSaving || contactSaving">
          {{ channelsSaving ? '渠道自动保存中...' : '联系方式自动保存中...' }}
        </p>
      </div>
      <button class="ghost-button" type="button" @click="openCreateDrawer">新增渠道</button>
    </div>

    <transition-group name="channel-motion" tag="div" class="channel-list">
      <div
        v-for="item in channels"
        :key="item.id"
        :ref="(el) => setChannelElement(item.id, el as Element | null)"
        class="channel-item"
        :class="{
          dragging: draggingId === item.id,
          'drag-over': hoverId === item.id,
        }"
        @pointerdown="onChannelPointerDown($event, item.id)"
      >
        <div class="item-main">
          <strong>{{ item.name }}</strong>
          <span class="chip">{{ item.provider }}</span>
          <span class="chip" :class="item.enabled ? 'on' : 'off'">{{ item.enabled ? '启用' : '停用' }}</span>
        </div>
        <div class="item-actions">
          <button class="mini-button ghost" type="button" @click="openEditDrawer(item)">编辑</button>
          <button class="mini-button" type="button" @click="toggleChannel(item.id)">{{ item.enabled ? '停用' : '启用' }}</button>
          <button class="mini-button danger" type="button" @click="removeChannel(item.id)">删除</button>
        </div>
      </div>
    </transition-group>

    <div v-if="overlayItem && draggingId" class="channel-overlay" :style="dragOverlayStyle">
      <div class="item-main">
        <strong>{{ overlayItem.name }}</strong>
        <span class="chip">{{ overlayItem.provider }}</span>
        <span class="chip" :class="overlayItem.enabled ? 'on' : 'off'">{{ overlayItem.enabled ? '启用' : '停用' }}</span>
      </div>
      <div class="overlay-tip">拖动调整优先级</div>
    </div>

    <label class="field full contact-field">
      <span>礼物失效联系方式</span>
      <input v-model="claimContact" class="input" type="text" placeholder="例如：微信 qrgift-support / 电话 138****0000" />
    </label>

    <div v-if="drawerVisible" class="drawer-mask" @click="closeDrawer">
      <aside class="drawer" @click.stop>
        <div class="drawer-head">
          <h3>{{ editingId ? '编辑渠道' : '新增渠道' }}</h3>
          <button class="ghost-button" type="button" @click="closeDrawer">关闭</button>
        </div>

        <div class="form-grid">
          <label class="field">
            <span>渠道名称</span>
            <input v-model="editor.name" class="input" type="text" placeholder="例如：主 OSS" />
          </label>
          <label class="field">
            <span>类型</span>
            <select v-model="editor.provider" class="input">
              <option value="local">本地</option>
              <option value="aliyun">OSS</option>
              <option value="minio">MinIO</option>
            </select>
          </label>

          <label class="field full">
            <span>对象前缀（可选）</span>
            <input v-model="editor.storage_prefix" class="input" type="text" placeholder="gifts/2026" />
          </label>

          <template v-if="editorIsLocal">
            <label class="field full">
              <span>本地目录</span>
              <input v-model="editor.local_storage_dir" class="input" type="text" placeholder="/data/object-storage" />
            </label>
          </template>

          <template v-else-if="editorIsMinio">
            <label class="field">
              <span>Endpoint</span>
              <input v-model="editor.minio_endpoint" class="input" type="text" placeholder="minio.example.com:9000" />
            </label>
            <label class="field">
              <span>Bucket</span>
              <input v-model="editor.bucket" class="input" type="text" />
            </label>
            <label class="field">
              <span>Access Key</span>
              <input v-model="editor.minio_access_key" class="input" type="password" :placeholder="editor.minio_access_key_set ? '已配置，留空不改' : ''" />
            </label>
            <label class="field">
              <span>Secret Key</span>
              <input v-model="editor.minio_secret_key" class="input" type="password" :placeholder="editor.minio_secret_key_set ? '已配置，留空不改' : ''" />
            </label>
          </template>

          <template v-else>
            <label class="field">
              <span>OSS Endpoint</span>
              <input v-model="editor.aliyun_oss_endpoint" class="input" type="text" placeholder="oss-cn-hangzhou.aliyuncs.com" />
            </label>
            <label class="field">
              <span>Bucket</span>
              <input v-model="editor.bucket" class="input" type="text" />
            </label>
            <label class="field">
              <span>AccessKey ID</span>
              <input v-model="editor.aliyun_oss_access_key_id" class="input" type="password" :placeholder="editor.aliyun_oss_access_key_id_set ? '已配置，留空不改' : ''" />
            </label>
            <label class="field">
              <span>AccessKey Secret</span>
              <input v-model="editor.aliyun_oss_access_key_secret" class="input" type="password" :placeholder="editor.aliyun_oss_access_key_secret_set ? '已配置，留空不改' : ''" />
            </label>
          </template>
        </div>

        <div class="drawer-actions">
          <button class="ghost-button" type="button" :disabled="testing" @click="testDraft">{{ testing ? '测试中...' : '测试当前渠道' }}</button>
          <button class="action-button" type="button" @click="saveChannelDraft">{{ editingId ? '更新渠道' : '添加渠道' }}</button>
        </div>

        <section class="test-log-panel">
          <h4 class="test-log-title">测试日志</h4>
          <p v-if="!testLogs.length" class="test-log-empty">暂无测试记录</p>
          <div v-else class="test-log-list">
            <div v-for="item in testLogs" :key="item.id" class="test-log-item" :class="item.status">
              <div class="test-log-head">
                <span>{{ item.status === 'success' ? '成功' : '失败' }}</span>
                <span>{{ item.time }}</span>
              </div>
              <p>{{ item.text }}</p>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.hint { font-size: 12px; margin-top: 4px; }
.top-row { align-items: center; display: flex; gap: 10px; justify-content: space-between; }
.channel-list { display: grid; gap: 8px; margin-top: 14px; }
.channel-item {
  background: color-mix(in oklab, var(--color-surface) 88%, var(--color-bg) 12%);
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 22%, transparent);
  border-radius: 12px;
  cursor: grab;
  padding: 10px;
  touch-action: pan-y;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, opacity 180ms ease;
}
.channel-item :is(strong, span, p, div) {
  user-select: none;
  -webkit-user-select: none;
}
.channel-item.dragging {
  cursor: grabbing;
  opacity: 0;
  visibility: hidden;
}
.channel-item.dragging * {
  pointer-events: none;
}
.channel-item.drag-over {
  border-color: color-mix(in oklab, var(--color-primary) 56%, #d4b39f 44%);
  transform: translateY(-2px);
}
.channel-motion-move { transition: transform 220ms ease; }
.channel-motion-enter-active,
.channel-motion-leave-active { transition: opacity 160ms ease, transform 160ms ease; }
.channel-motion-enter-from,
.channel-motion-leave-to { opacity: 0; transform: translateY(4px); }

.channel-overlay {
  background: color-mix(in oklab, var(--color-surface) 90%, var(--color-bg) 10%);
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 22%, transparent);
  border-radius: 12px;
  box-shadow: var(--shadow-card);
  cursor: grabbing;
  left: 0;
  opacity: 0.94;
  padding: 10px;
  pointer-events: none;
  position: fixed;
  top: 0;
  transform: scale(1.01);
  z-index: 95;
}

.overlay-tip {
  color: var(--color-text-secondary);
  font-size: 11px;
  margin-top: 8px;
}

:global(body.channel-dragging) {
  cursor: grabbing;
  user-select: none;
}

.item-main { align-items: center; display: flex; gap: 6px; }
.chip {
  border-radius: 999px;
  background: color-mix(in oklab, var(--color-primary-soft) 78%, var(--color-surface) 22%);
  color: color-mix(in oklab, var(--color-primary-deep) 82%, var(--color-text-main) 18%);
  font-size: 11px;
  padding: 2px 8px;
}
.chip.on {
  background: color-mix(in oklab, var(--color-success) 18%, var(--color-surface) 82%);
  color: color-mix(in oklab, var(--color-success) 86%, var(--color-text-main) 14%);
}
.chip.off {
  background: color-mix(in oklab, var(--color-primary) 14%, var(--color-surface) 86%);
  color: color-mix(in oklab, var(--color-primary-deep) 84%, var(--color-text-main) 16%);
}
.item-actions { display: flex; gap: 6px; margin-top: 8px; }
.field { display: grid; gap: 6px; }
.field.full { grid-column: span 2; }
.contact-field { margin-top: 14px; }
.input {
  background: color-mix(in oklab, var(--color-surface) 78%, var(--color-bg) 22%);
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 28%, transparent);
  border-radius: 10px;
  color: var(--color-text-main);
  padding: 8px 10px;
}
.input::placeholder { color: color-mix(in oklab, var(--color-text-secondary) 80%, transparent); }
.input:focus {
  border-color: color-mix(in oklab, var(--color-primary) 52%, var(--color-text-secondary) 48%);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-primary) 24%, transparent);
  outline: none;
}
.action-button { border: 0; border-radius: 10px; background: var(--color-primary); color: #fff; padding: 8px 12px; cursor: pointer; }
.ghost-button { border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); border-radius: 10px; background: transparent; color: var(--color-text-main); padding: 8px 12px; cursor: pointer; }
.mini-button { border: 0; border-radius: 8px; background: var(--color-primary); color: #fff; cursor: pointer; padding: 4px 8px; }
.mini-button.ghost { background: transparent; border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); color: var(--color-text-main); }
.mini-button.danger { background: #bf3f2b; }

.toast-error {
  background: #b53a29;
  border-radius: 10px;
  color: #fff;
  padding: 8px 12px;
  position: fixed;
  right: 14px;
  top: 14px;
  z-index: 95;
}

.drawer-mask { background: rgba(15, 10, 7, 0.4); inset: 0; position: fixed; z-index: 70; }
.drawer {
  background: var(--color-surface);
  box-shadow: -10px 0 30px color-mix(in oklab, #000 32%, transparent);
  height: 100%;
  overflow: auto;
  padding: 14px;
  position: absolute;
  right: 0;
  top: 0;
  width: min(540px, 100%);
}
.drawer-head { align-items: center; display: flex; justify-content: space-between; gap: 8px; }
.drawer-head h3 { margin: 0; }
.form-grid { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 12px; }
.drawer-actions { display: flex; gap: 8px; margin-top: 12px; }
.test-log-panel { margin-top: 14px; }
.test-log-title { margin: 0 0 8px; }
.test-log-empty { color: var(--color-text-secondary); margin: 0; }
.test-log-list { display: grid; gap: 8px; }
.test-log-item {
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 24%, transparent);
  border-radius: 10px;
  padding: 8px 10px;
}
.test-log-item.success {
  background: color-mix(in oklab, var(--color-success) 12%, var(--color-surface) 88%);
  border-color: color-mix(in oklab, var(--color-success) 28%, transparent);
}
.test-log-item.failed {
  background: color-mix(in oklab, var(--color-primary) 10%, var(--color-surface) 90%);
  border-color: color-mix(in oklab, var(--color-primary) 24%, transparent);
}
.test-log-head {
  align-items: center;
  display: flex;
  justify-content: space-between;
  color: var(--color-text-secondary);
  font-size: 12px;
}
.test-log-item p { margin: 6px 0 0; white-space: pre-wrap; word-break: break-word; }

@media (max-width: 900px) {
  .top-row { align-items: flex-start; flex-direction: column; }
  .form-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: span 1; }
}
</style>
