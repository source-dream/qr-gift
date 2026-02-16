<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { activateGift, disableGift, getGiftQrcodeDownloadUrl, listGifts, type GiftItem } from '../api/modules/gift'

const router = useRouter()
const route = useRoute()
const message = shallowRef('')
const list = shallowRef<GiftItem[]>([])

function resolveErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  return fallback
}

async function loadList(): Promise<void> {
  list.value = await listGifts()
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
          <tr v-for="item in list" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.title }}</td>
            <td>{{ item.status }}</td>
            <td>{{ item.activate_at || '-' }} ~ {{ item.expire_at || '-' }}</td>
            <td>{{ item.binding_count }}</td>
            <td>{{ item.dispatch_strategy }}</td>
            <td>{{ item.style_type }}</td>
            <td class="actions-cell">
              <button class="mini-button ghost" type="button" @click="router.push(`/gifts/${item.id}/edit`)">编辑</button>
              <button class="mini-button ghost" type="button" @click="downloadQrImage(item.id)">下载二维码</button>
              <button class="mini-button" type="button" @click="changeStatus(item.id, 'activate')">启用</button>
              <button class="mini-button ghost" type="button" @click="changeStatus(item.id, 'disable')">停用</button>
            </td>
          </tr>
        </tbody>
      </table>
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
.table th, .table td {
  border-bottom: 1px solid color-mix(in oklab, var(--color-text-secondary) 22%, transparent);
  color: var(--color-text-main);
  padding: 8px;
  text-align: left;
}
.actions-cell { display: flex; gap: 6px; }
.mini-button { border: 0; border-radius: 8px; background: var(--color-primary); color: #fff; padding: 4px 8px; cursor: pointer; }
.mini-button.ghost { background: transparent; border: 1px solid color-mix(in oklab, var(--color-primary) 28%, #999 20%); color: var(--color-text-main); }
@media (max-width: 900px) {
  .head-row { align-items: flex-start; flex-direction: column; }
}
</style>
