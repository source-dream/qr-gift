import client from '../client'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
}

export interface DashboardOverview {
  total_gifts: number
  total_red_packets: number
  total_bound: number
  total_claimed: number
  today_success_claims: number
  today_rejected_claims: number
}

export interface DashboardTrend {
  days: string[]
  success: number[]
  rejected: number[]
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const response = await client.get<ApiEnvelope<DashboardOverview>>('/dashboard/overview')
  return response.data.data
}

export async function getDashboardTrend7d(): Promise<DashboardTrend> {
  const response = await client.get<ApiEnvelope<DashboardTrend>>('/dashboard/trend-7d')
  return response.data.data
}
