<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  deleteRedPacket,
  disableRedPacket,
  enableRedPacket,
  listRedPackets,
  updateRedPacket,
  type RedPacketItem,
} from '../api/modules/redPacket'

const router = useRouter()
const route = useRoute()
const message = shallowRef('')
const list = shallowRef<RedPacketItem[]>([])
const editingId = shallowRef<number | null>(null)
const saving = shallowRef(false)
const deleting = shallowRef(false)
const removeTarget = shallowRef<RedPacketItem | null>(null)
const confirmVisible = shallowRef(false)
const filters = reactive({
  keyword: '',
  category: '',
  contentType: '',
  status: '',
  tag: '',
})

const editForm = reactive({
  title: '',
  amount: 0,
  level: 1,
  content_value: '',
  available_from: '',
  available_to: '',
})

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

function statusLabel(status: string): string {
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

const categoryOptions = computed(() => {
  const set = new Set<string>()
  for (const item of list.value) {
    if (item.category_name) {
      set.add(item.category_name)
    }
  }
  return Array.from(set)
})

const tagOptions = computed(() => {
  const set = new Set<string>()
  for (const item of list.value) {
    for (const tag of item.tags) {
      set.add(tag)
    }
  }
  return Array.from(set)
})

const filteredList = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return list.value.filter((item) => {
    if (filters.category && item.category_name !== filters.category) {
      return false
    }
    if (filters.contentType && item.content_type !== filters.contentType) {
      return false
    }
    if (filters.status && item.status !== filters.status) {
      return false
    }
    if (filters.tag && !item.tags.includes(filters.tag)) {
      return false
    }
    if (!keyword) {
      return true
    }
    const haystack = [item.title, item.content_value, item.category_name, item.tags.join(',')]
      .join(' ')
      .toLowerCase()
    return haystack.includes(keyword)
  })
})

async function loadList(): Promise<void> {
  list.value = await listRedPackets()
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

function beginEdit(item: RedPacketItem): void {
  if (item.status === 'claimed') {
    message.value = '已领取记录不可编辑'
    return
  }
  editingId.value = item.id
  editForm.title = item.title
  editForm.amount = item.amount
  editForm.level = item.level
  editForm.content_value = item.content_value
  editForm.available_from = toDatetimeLocal(item.available_from)
  editForm.available_to = toDatetimeLocal(item.available_to)
}

function cancelEdit(): void {
  if (saving.value) {
    return
  }
  editingId.value = null
}

async function submitEdit(): Promise<void> {
  if (!editingId.value) {
    return
  }
  saving.value = true
  message.value = ''
  try {
    await updateRedPacket(editingId.value, {
      title: editForm.title,
      amount: Number(editForm.amount || 0),
      level: Number(editForm.level || 1),
      content_value: editForm.content_value,
      available_from: editForm.available_from || null,
      available_to: editForm.available_to || null,
    })
    message.value = '更新成功'
    editingId.value = null
    await loadList()
  } catch (error) {
    message.value = resolveErrorMessage(error, '更新失败')
  } finally {
    saving.value = false
  }
}

async function toggleDisable(item: RedPacketItem): Promise<void> {
  try {
    if (item.status === 'disabled') {
      await enableRedPacket(item.id)
      message.value = '已启用'
    } else {
      await disableRedPacket(item.id)
      message.value = '已停用'
    }
    await loadList()
  } catch (error) {
    message.value = resolveErrorMessage(error, '状态更新失败')
  }
}

function openRemoveConfirm(item: RedPacketItem): void {
  if (deleting.value) {
    return
  }
  removeTarget.value = item
  confirmVisible.value = true
}

function closeRemoveConfirm(): void {
  if (deleting.value) {
    return
  }
  confirmVisible.value = false
  removeTarget.value = null
}

async function removeItem(): Promise<void> {
  const item = removeTarget.value
  if (!item) {
    return
  }
  deleting.value = true
  try {
    await deleteRedPacket(item.id)
    message.value = item.status === 'claimed' ? '已标记删除（日志保留）' : '已自动解绑并删除'
    if (editingId.value === item.id) {
      editingId.value = null
    }
    await loadList()
  } catch (error) {
    message.value = resolveErrorMessage(error, '删除失败')
  } finally {
    deleting.value = false
    closeRemoveConfirm()
  }
}

onMounted(async () => {
  await loadList()
  if (route.query.imported === '1') {
    message.value = '导入完成，礼物列表已刷新'
    router.replace('/red-packets')
  }
})
</script>

<template>
  <section class="card-surface">
    <div class="head-row">
      <div>
        <h2 class="title">礼物管理</h2>
        <p class="desc">统一管理链接、文本、图片三类红包内容。</p>
      </div>
      <button class="action-button" type="button" @click="router.push('/red-packets/import')">导入礼物</button>
    </div>

    <p v-if="message" class="message">{{ message }}</p>

    <div class="filters">
      <input v-model="filters.keyword" class="input" type="text" placeholder="搜索名称、内容、标签" />
      <select v-model="filters.category" class="input">
        <option value="">全部分类</option>
        <option v-for="item in categoryOptions" :key="item" :value="item">{{ item }}</option>
      </select>
      <select v-model="filters.contentType" class="input">
        <option value="">全部类型</option>
        <option value="url">链接</option>
        <option value="text">文本</option>
        <option value="qr_image">图片</option>
      </select>
      <select v-model="filters.status" class="input">
        <option value="">全部状态</option>
        <option value="idle">可用</option>
        <option value="bound">已绑定</option>
        <option value="claimed">已领取</option>
      </select>
      <select v-model="filters.tag" class="input">
        <option value="">全部标签</option>
        <option v-for="item in tagOptions" :key="item" :value="item">{{ item }}</option>
      </select>
    </div>

    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>分类</th>
            <th>金额</th>
            <th>等级</th>
            <th>内容类型</th>
            <th>标签</th>
            <th>状态</th>
            <th>内容</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in filteredList"
            :key="item.id"
            class="clickable-row"
            :class="{ active: editingId === item.id }"
            @click="beginEdit(item)"
          >
            <td>{{ item.id }}</td>
            <td>{{ item.title }}</td>
            <td>{{ item.category_name }}</td>
            <td>{{ item.amount }}</td>
            <td>{{ item.level }}</td>
            <td>{{ item.content_type }}</td>
            <td>{{ item.tags.join(', ') || '-' }}</td>
            <td>{{ statusLabel(item.status) }}</td>
            <td class="url-cell">
              <template v-if="item.content_type === 'qr_image'">
                <a :href="item.content_image_url" target="_blank" rel="noreferrer">查看图片</a>
              </template>
              <template v-else>
                {{ item.content_value }}
              </template>
            </td>
            <td class="actions-cell">
              <button class="mini-button ghost" type="button" @click.stop="beginEdit(item)">编辑</button>
              <button
                class="mini-button"
                type="button"
                :disabled="item.status === 'claimed'"
                @click.stop="toggleDisable(item)"
              >
                {{ item.status === 'disabled' ? '启用' : '停用' }}
              </button>
              <button class="mini-button danger" type="button" @click.stop="openRemoveConfirm(item)">
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="editingId" class="drawer-mask" @click="cancelEdit">
      <aside class="drawer" role="dialog" aria-modal="true" @click.stop>
        <header class="drawer-head">
          <div>
            <h3 class="edit-title">编辑礼物 #{{ editingId }}</h3>
            <p class="drawer-desc">在抽屉中编辑后可直接保存并刷新列表。</p>
          </div>
          <button class="mini-button ghost" type="button" :disabled="saving" @click="cancelEdit">关闭</button>
        </header>

        <div class="edit-grid">
          <label class="field full">
            <span>名称</span>
            <input v-model="editForm.title" class="input" type="text" />
          </label>
          <label class="field">
            <span>金额</span>
            <input v-model.number="editForm.amount" class="input" min="0" step="0.01" type="number" />
          </label>
          <label class="field">
            <span>等级</span>
            <input v-model.number="editForm.level" class="input" min="1" max="10" type="number" />
          </label>
          <label class="field full">
            <span>链接内容</span>
            <input v-model="editForm.content_value" class="input" type="text" />
          </label>
          <label class="field">
            <span>激活时间（可选）</span>
            <input v-model="editForm.available_from" class="input" type="datetime-local" />
          </label>
          <label class="field">
            <span>失效时间（可选）</span>
            <input v-model="editForm.available_to" class="input" type="datetime-local" />
          </label>
        </div>

        <div class="edit-actions">
          <button class="mini-button" type="button" :disabled="saving" @click="submitEdit">{{ saving ? '保存中...' : '保存' }}</button>
          <button class="mini-button ghost" type="button" :disabled="saving" @click="cancelEdit">取消</button>
        </div>
      </aside>
    </div>

    <div v-if="confirmVisible" class="confirm-mask" @click="closeRemoveConfirm">
      <div class="confirm-dialog" role="dialog" aria-modal="true" @click.stop>
        <h3 class="confirm-title">确认删除红包？</h3>
        <p class="confirm-desc">
          {{
            removeTarget?.status === 'claimed'
              ? `【${removeTarget.title}】已领取，删除后会标记为已删除并保留日志。`
              : `【${removeTarget?.title || ''}】删除后将自动解绑关联礼物。`
          }}
        </p>
        <div class="confirm-actions">
          <button class="mini-button ghost" type="button" :disabled="deleting" @click="closeRemoveConfirm">取消</button>
          <button class="mini-button danger" type="button" :disabled="deleting" @click="removeItem">
            {{ deleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.head-row { align-items: center; display: flex; justify-content: space-between; gap: 10px; }
.action-button { border: 0; border-radius: 10px; background: var(--color-primary); color: #fff; padding: 8px 12px; cursor: pointer; }
.message { color: var(--color-text-secondary); margin: 10px 0 0; }
.filters { display: grid; gap: 8px; grid-template-columns: repeat(5, minmax(0, 1fr)); margin-top: 12px; }
.input {
  background: color-mix(in oklab, var(--color-surface) 82%, var(--color-bg) 18%);
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 28%, transparent);
  border-radius: 10px;
  color: var(--color-text-main);
  padding: 8px 10px;
}
.input::placeholder { color: color-mix(in oklab, var(--color-text-secondary) 82%, transparent); }
.input:focus {
  border-color: color-mix(in oklab, var(--color-primary) 46%, transparent);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-primary) 20%, transparent);
  outline: none;
}
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
.url-cell { max-width: 440px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.url-cell a { color: var(--color-primary-deep); }
.actions-cell { display: flex; gap: 6px; }
.mini-button { border: 0; border-radius: 8px; background: var(--color-primary); color: #fff; cursor: pointer; padding: 4px 8px; }
.mini-button.ghost { background: transparent; border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); color: var(--color-text-main); }
.mini-button.danger { background: color-mix(in oklab, var(--color-primary-deep) 82%, #7a1f18 18%); }
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
  width: min(620px, 100%);
}

.drawer-head {
  align-items: flex-start;
  display: flex;
  gap: 10px;
  justify-content: space-between;
}

.edit-title { margin: 0 0 10px; }
.drawer-desc { color: var(--color-text-secondary); margin: 6px 0 0; }
.edit-grid { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.field { display: grid; gap: 6px; }
.field.full { grid-column: span 2; }
.edit-actions { display: flex; gap: 8px; margin-top: 12px; }
.confirm-mask {
  align-items: center;
  background: rgba(22, 16, 12, 0.42);
  display: flex;
  inset: 0;
  justify-content: center;
  position: fixed;
  z-index: 90;
}
.confirm-dialog {
  background: var(--color-surface);
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 24%, transparent);
  border-radius: 12px;
  box-shadow: var(--shadow-card);
  max-width: 520px;
  padding: 14px;
  width: min(92vw, 520px);
}
.confirm-title { margin: 0; }
.confirm-desc { color: var(--color-text-secondary); margin: 10px 0 0; }
.confirm-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 14px; }
@media (max-width: 900px) {
  .head-row { align-items: flex-start; flex-direction: column; }
  .filters { grid-template-columns: 1fr; }
  .edit-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: span 1; }
}
</style>
