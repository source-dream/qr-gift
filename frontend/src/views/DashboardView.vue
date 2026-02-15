<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, shallowRef, useTemplateRef } from 'vue'
import type { ECharts } from 'echarts'

import {
  getDashboardOverview,
  getDashboardTrend7d,
  type DashboardOverview,
  type DashboardTrend,
} from '../api/modules/dashboard'

const loading = shallowRef(false)
const hasError = shallowRef(false)
const trend = reactive<DashboardTrend>({
  days: [],
  success: [],
  rejected: [],
})
const trendRef = useTemplateRef<HTMLDivElement>('trend')
let trendChart: ECharts | null = null

const overview = reactive<DashboardOverview>({
  total_gifts: 0,
  total_red_packets: 0,
  total_bound: 0,
  total_claimed: 0,
  today_success_claims: 0,
  today_rejected_claims: 0,
})

const bindRate = computed(() => {
  if (!overview.total_gifts) {
    return '0%'
  }
  return `${Math.round((overview.total_bound / overview.total_gifts) * 100)}%`
})

const metrics = computed(() => [
  { label: '礼物二维码总数', value: String(overview.total_gifts), trend: '总创建量' },
  { label: '今日领取数', value: String(overview.today_success_claims), trend: '当日成功' },
  { label: '绑定完成率', value: bindRate.value, trend: '可领配置率' },
  { label: '异常拦截数', value: String(overview.today_rejected_claims), trend: '当日拦截' },
])

async function loadOverview(): Promise<void> {
  loading.value = true
  hasError.value = false
  try {
    const [overviewData, trendData] = await Promise.all([getDashboardOverview(), getDashboardTrend7d()])
    Object.assign(overview, overviewData)
    Object.assign(trend, trendData)
    await nextTick()
    await renderTrendChart()
  } catch (_error) {
    hasError.value = true
  } finally {
    loading.value = false
  }
}

async function renderTrendChart(): Promise<void> {
  if (!trendRef.value) {
    return
  }
  const echarts = await import('echarts')
  if (!trendChart) {
    trendChart = echarts.init(trendRef.value)
  }

  const isMobile = window.innerWidth <= 680

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: {
      left: 10,
      right: 10,
      top: isMobile ? 8 : 26,
      bottom: 14,
      containLabel: true,
    },
    legend: {
      show: !isMobile,
      data: ['成功领取', '拦截次数'],
      top: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { fontSize: 11 },
    },
    xAxis: { type: 'category', data: trend.days },
    yAxis: { type: 'value' },
    series: [
      {
        name: '成功领取',
        type: 'line',
        smooth: true,
        data: trend.success,
        lineStyle: { color: '#1f8a4c' },
        itemStyle: { color: '#1f8a4c' },
      },
      {
        name: '拦截次数',
        type: 'line',
        smooth: true,
        data: trend.rejected,
        lineStyle: { color: '#d9362b' },
        itemStyle: { color: '#d9362b' },
      },
    ],
  })

  trendChart.resize()
}

function handleResize(): void {
  trendChart?.resize()
}

onMounted(() => {
  loadOverview()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
})
</script>

<template>
  <div class="dashboard-grid">
    <article v-for="item in metrics" :key="item.label" class="card-surface metric-card">
      <p class="metric-label">{{ item.label }}</p>
      <p class="metric-value">{{ item.value }}</p>
      <p class="metric-trend">{{ item.trend }}</p>
    </article>

    <article class="card-surface panel-card">
      <h3 class="panel-title">领取趋势</h3>
      <div ref="trend" class="trend-chart"></div>
    </article>

    <article class="card-surface panel-card">
      <h3 class="panel-title">风险提示</h3>
      <p v-if="loading" class="panel-desc">正在加载看板数据...</p>
      <p v-else-if="hasError" class="panel-desc">看板数据加载失败，请检查登录状态与后端服务。</p>
      <p v-else class="panel-desc">今日拦截 {{ overview.today_rejected_claims }} 次，请关注安全策略。</p>
    </article>
  </div>
</template>

<style scoped>
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-label {
  margin: 0;
  color: var(--color-text-secondary);
}

.metric-value {
  margin: 0;
  font-family: var(--font-display);
  font-size: 32px;
  color: var(--color-primary-deep);
}

.metric-trend {
  margin: 0;
  color: var(--color-success);
  font-size: 13px;
}

.panel-card {
  grid-column: span 2;
}

.panel-title {
  margin: 0 0 8px;
}

.panel-desc {
  margin: 0;
  color: var(--color-text-secondary);
}

.trend-chart {
  height: 280px;
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .panel-card {
    grid-column: span 2;
  }
}

@media (max-width: 680px) {
  .dashboard-grid {
    gap: 10px;
    grid-template-columns: 1fr;
  }

  .metric-card {
    padding: 10px;
  }

  .panel-card {
    grid-column: span 1;
  }

  .metric-card {
    gap: 4px;
  }

  .metric-label {
    font-size: 12px;
  }

  .metric-value {
    font-size: 22px;
  }

  .metric-trend {
    font-size: 12px;
  }

  .panel-title {
    font-size: 16px;
  }

  .trend-chart {
    height: 170px;
  }
}

@media (max-width: 420px) {
  .metric-value {
    font-size: 20px;
  }

  .trend-chart {
    height: 155px;
  }
}
</style>
