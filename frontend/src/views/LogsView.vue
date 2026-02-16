<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'

import {
  listAccessLogs,
  listClaimLogs,
  listOperationLogs,
  type AccessLogItem,
  type ClaimLogItem,
  type OperationLogItem,
} from '../api/modules/logs'

type TabKey = 'access' | 'claims' | 'operations'

const PAGE_SIZE = 50

const activeTab = shallowRef<TabKey>('access')
const accessLogs = shallowRef<AccessLogItem[]>([])
const claimLogs = shallowRef<ClaimLogItem[]>([])
const operationLogs = shallowRef<OperationLogItem[]>([])
const loadingByTab = reactive<Record<TabKey, boolean>>({
  access: false,
  claims: false,
  operations: false,
})
const loadedByTab = reactive<Record<TabKey, boolean>>({
  access: false,
  claims: false,
  operations: false,
})
const hasMoreByTab = reactive<Record<TabKey, boolean>>({
  access: true,
  claims: true,
  operations: true,
})
const offsetByTab = reactive<Record<TabKey, number>>({
  access: 0,
  claims: 0,
  operations: 0,
})
const error = shallowRef('')
const searchDraft = shallowRef('')
const searchKeyword = shallowRef('')

function resetLoadedState(): void {
  loadedByTab.access = false
  loadedByTab.claims = false
  loadedByTab.operations = false
  hasMoreByTab.access = true
  hasMoreByTab.claims = true
  hasMoreByTab.operations = true
  offsetByTab.access = 0
  offsetByTab.claims = 0
  offsetByTab.operations = 0
  accessLogs.value = []
  claimLogs.value = []
  operationLogs.value = []
}

function getTabLogs(tab: TabKey): AccessLogItem[] | ClaimLogItem[] | OperationLogItem[] {
  if (tab === 'access') {
    return accessLogs.value
  }
  if (tab === 'claims') {
    return claimLogs.value
  }
  return operationLogs.value
}

function setTabLogs(tab: TabKey, rows: AccessLogItem[] | ClaimLogItem[] | OperationLogItem[]): void {
  if (tab === 'access') {
    accessLogs.value = rows as AccessLogItem[]
    return
  }
  if (tab === 'claims') {
    claimLogs.value = rows as ClaimLogItem[]
    return
  }
  operationLogs.value = rows as OperationLogItem[]
}

async function loadTab(tab: TabKey, offset: number): Promise<void> {
  loadingByTab[tab] = true
  error.value = ''
  try {
    let rows: AccessLogItem[] | ClaimLogItem[] | OperationLogItem[] = []
    const query = searchKeyword.value
    if (tab === 'access') {
      rows = await listAccessLogs({ limit: PAGE_SIZE, offset, q: query })
    } else if (tab === 'claims') {
      rows = await listClaimLogs({ limit: PAGE_SIZE, offset, q: query })
    } else {
      rows = await listOperationLogs({ limit: PAGE_SIZE, offset, q: query })
    }
    setTabLogs(tab, rows)
    offsetByTab[tab] = offset
    hasMoreByTab[tab] = rows.length === PAGE_SIZE
    loadedByTab[tab] = true
  } catch {
    error.value = '日志加载失败，请稍后重试'
  } finally {
    loadingByTab[tab] = false
  }
}

const canPrev = computed(() => offsetByTab[activeTab.value] > 0)
const canNext = computed(() => hasMoreByTab[activeTab.value] && !loadingByTab[activeTab.value])
const currentPage = computed(() => Math.floor(offsetByTab[activeTab.value] / PAGE_SIZE) + 1)
const currentTabLoading = computed(() => loadingByTab[activeTab.value])
const currentTabRows = computed(() => getTabLogs(activeTab.value))

function submitSearch(): void {
  const nextKeyword = searchDraft.value.trim()
  if (nextKeyword === searchKeyword.value) {
    return
  }
  searchKeyword.value = nextKeyword
  resetLoadedState()
  void loadTab(activeTab.value, 0)
}

function clearSearch(): void {
  if (!searchDraft.value && !searchKeyword.value) {
    return
  }
  searchDraft.value = ''
  searchKeyword.value = ''
  resetLoadedState()
  void loadTab(activeTab.value, 0)
}

function prevPage(): void {
  const tab = activeTab.value
  if (!canPrev.value || loadingByTab[tab]) {
    return
  }
  const nextOffset = Math.max(0, offsetByTab[tab] - PAGE_SIZE)
  void loadTab(tab, nextOffset)
}

function nextPage(): void {
  const tab = activeTab.value
  if (!canNext.value || loadingByTab[tab]) {
    return
  }
  const nextOffset = offsetByTab[tab] + PAGE_SIZE
  void loadTab(tab, nextOffset)
}

watch(
  () => activeTab.value,
  (tab) => {
    if (!loadedByTab[tab]) {
      void loadTab(tab, 0)
    }
  },
)

onMounted(() => {
  void loadTab(activeTab.value, 0)
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

    <div class="search-row">
      <input
        v-model="searchDraft"
        class="search-input"
        type="text"
        placeholder="搜索 IP、路径、结果、动作、详情..."
        @keydown.enter.prevent="submitSearch"
      />
      <button class="search-button" type="button" @click="submitSearch">搜索</button>
      <button class="clear-button" type="button" @click="clearSearch">清空</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

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

    <div class="pager-row">
      <p class="pager-tip">{{ currentTabLoading ? '加载中...' : `当前页 ${currentPage} · 每页 ${PAGE_SIZE} 条` }}</p>
      <div class="pager-actions">
        <button class="pager-button" type="button" :disabled="!canPrev || currentTabLoading" @click="prevPage">上一页</button>
        <button class="pager-button" type="button" :disabled="!canNext || currentTabLoading" @click="nextPage">下一页</button>
      </div>
    </div>

    <p v-if="!currentTabLoading && currentTabRows.length === 0" class="empty">暂无日志数据</p>
  </section>
</template>

<style scoped>
.title { margin: 0 0 8px; }
.desc { margin: 0; color: var(--color-text-secondary); }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.tab {
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 28%, transparent);
  border-radius: 10px;
  background: color-mix(in oklab, var(--color-surface) 86%, var(--color-bg) 14%);
  color: var(--color-text-main);
  cursor: pointer;
  padding: 6px 10px;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.tab:hover {
  background: color-mix(in oklab, var(--color-primary) 8%, var(--color-surface) 92%);
}

.tab:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-primary) 24%, transparent);
}

.tab.active {
  background: color-mix(in oklab, var(--color-primary) 14%, var(--color-surface) 86%);
  border-color: color-mix(in oklab, var(--color-primary) 44%, transparent);
  color: color-mix(in oklab, var(--color-primary-deep) 72%, var(--color-text-main) 28%);
}

.search-row {
  align-items: center;
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.search-input {
  flex: 1;
  min-width: 180px;
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 28%, transparent);
  border-radius: 10px;
  background: color-mix(in oklab, var(--color-surface) 90%, var(--color-bg) 10%);
  color: var(--color-text-main);
  padding: 7px 10px;
}

.search-input::placeholder {
  color: color-mix(in oklab, var(--color-text-secondary) 82%, transparent);
}

.search-input:focus {
  border-color: color-mix(in oklab, var(--color-primary) 44%, transparent);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-primary) 20%, transparent);
  outline: none;
}

.search-button,
.clear-button {
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 28%, transparent);
  border-radius: 10px;
  background: color-mix(in oklab, var(--color-surface) 90%, var(--color-bg) 10%);
  color: var(--color-text-main);
  cursor: pointer;
  padding: 7px 10px;
}

.search-button {
  background: color-mix(in oklab, var(--color-primary) 14%, var(--color-surface) 86%);
  border-color: color-mix(in oklab, var(--color-primary) 44%, transparent);
}

.error {
  color: color-mix(in oklab, var(--color-primary-deep) 80%, var(--color-text-main) 20%);
  margin: 10px 0 0;
}

.table-wrap {
  margin-top: 14px;
  max-height: clamp(320px, 58vh, 680px);
  overflow: auto;
  scrollbar-width: thin;
  scrollbar-color: color-mix(in oklab, var(--color-primary) 42%, transparent)
    color-mix(in oklab, var(--color-text-secondary) 12%, transparent);
}

.table-wrap::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.table-wrap::-webkit-scrollbar-track {
  background: color-mix(in oklab, var(--color-text-secondary) 10%, transparent);
  border-radius: 999px;
}

.table-wrap::-webkit-scrollbar-thumb {
  background: linear-gradient(
    180deg,
    color-mix(in oklab, var(--color-primary) 58%, transparent),
    color-mix(in oklab, var(--color-primary-deep) 52%, transparent)
  );
  border: 2px solid transparent;
  border-radius: 999px;
  background-clip: padding-box;
}

.table-wrap::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(
    180deg,
    color-mix(in oklab, var(--color-primary) 70%, transparent),
    color-mix(in oklab, var(--color-primary-deep) 64%, transparent)
  );
  border: 2px solid transparent;
  background-clip: padding-box;
}

.table {
  border-collapse: collapse;
  width: 100%;
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 24%, transparent);
  border-radius: 12px;
  overflow: hidden;
}

.table thead th {
  background: color-mix(in oklab, var(--color-primary) 8%, var(--color-surface) 92%);
}

.table tbody tr:hover {
  background: color-mix(in oklab, var(--color-primary) 6%, var(--color-surface) 94%);
}

.table th,
.table td {
  border-bottom: 1px solid color-mix(in oklab, var(--color-text-secondary) 22%, transparent);
  padding: 8px;
  text-align: left;
  white-space: nowrap;
}

.table th {
  color: color-mix(in oklab, var(--color-text-main) 82%, var(--color-text-secondary) 18%);
  font-weight: 600;
}

.table td {
  color: var(--color-text-main);
}

.pager-row {
  align-items: center;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  margin-top: 12px;
}

.pager-tip {
  color: var(--color-text-secondary);
  margin: 0;
}

.pager-actions {
  display: flex;
  gap: 8px;
}

.pager-button {
  border: 1px solid color-mix(in oklab, var(--color-text-secondary) 28%, transparent);
  border-radius: 10px;
  background: color-mix(in oklab, var(--color-surface) 90%, var(--color-bg) 10%);
  color: var(--color-text-main);
  cursor: pointer;
  padding: 6px 10px;
}

.pager-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.empty {
  color: var(--color-text-secondary);
  margin: 10px 0 0;
}

@media (max-width: 900px) {
  .search-row {
    flex-wrap: wrap;
  }

  .search-input {
    min-width: 100%;
  }

  .pager-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
