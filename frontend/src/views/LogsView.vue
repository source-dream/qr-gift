<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'

import {
  listAccessLogs,
  listClaimLogs,
  listOperationLogs,
  type AccessLogItem,
  type ClaimLogItem,
  type OperationLogItem,
} from '../api/modules/logs'

const activeTab = shallowRef<'access' | 'claims' | 'operations'>('access')
const accessLogs = shallowRef<AccessLogItem[]>([])
const claimLogs = shallowRef<ClaimLogItem[]>([])
const operationLogs = shallowRef<OperationLogItem[]>([])

async function loadData(): Promise<void> {
  const [accessData, claimData, operationData] = await Promise.all([
    listAccessLogs(),
    listClaimLogs(),
    listOperationLogs(),
  ])
  accessLogs.value = accessData
  claimLogs.value = claimData
  operationLogs.value = operationData
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <section class="card-surface">
    <h2 class="title">日志中心</h2>
    <p class="desc">默认永久保留访问日志、领取日志与操作日志。</p>

    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'access' }" @click="activeTab = 'access'">访问日志</button>
      <button class="tab" :class="{ active: activeTab === 'claims' }" @click="activeTab = 'claims'">领取日志</button>
      <button class="tab" :class="{ active: activeTab === 'operations' }" @click="activeTab = 'operations'">操作日志</button>
    </div>

    <div v-if="activeTab === 'access'" class="table-wrap">
      <table class="table">
        <thead><tr><th>时间</th><th>来源</th><th>路径</th><th>IP</th><th>状态</th><th>耗时</th></tr></thead>
        <tbody>
          <tr v-for="item in accessLogs" :key="`a-${item.id}`">
            <td>{{ item.created_at }}</td><td>{{ item.source }}</td><td>{{ item.path }}</td><td>{{ item.ip }}</td><td>{{ item.status_code }}</td><td>{{ item.latency_ms }}ms</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="activeTab === 'claims'" class="table-wrap">
      <table class="table">
        <thead><tr><th>时间</th><th>礼物ID</th><th>红包ID</th><th>策略</th><th>IP</th><th>结果</th><th>原因</th></tr></thead>
        <tbody>
          <tr v-for="item in claimLogs" :key="`c-${item.id}`">
            <td>{{ item.created_at }}</td><td>{{ item.gift_qrcode_id }}</td><td>{{ item.red_packet_id || '-' }}</td><td>{{ item.dispatch_strategy || '-' }}</td><td>{{ item.ip }}</td><td>{{ item.result }}</td><td>{{ item.reason || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="activeTab === 'operations'" class="table-wrap">
      <table class="table">
        <thead><tr><th>时间</th><th>用户</th><th>动作</th><th>详情</th></tr></thead>
        <tbody>
          <tr v-for="item in operationLogs" :key="`o-${item.id}`">
            <td>{{ item.created_at }}</td><td>{{ item.user_id || '-' }}</td><td>{{ item.action }}</td><td>{{ item.detail }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.tab { border: 1px solid #ccc; border-radius: 10px; background: transparent; cursor: pointer; padding: 6px 10px; }
.tab.active { background: var(--color-primary-soft); border-color: var(--color-primary); color: var(--color-primary-deep); }
.table-wrap { margin-top: 14px; overflow: auto; }
.table { border-collapse: collapse; width: 100%; }
.table th, .table td { border-bottom: 1px solid color-mix(in oklab, var(--color-text-secondary) 20%, #ddd 80%); padding: 8px; text-align: left; white-space: nowrap; }
</style>
