import client from '../client'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
}

export interface AccessLogItem {
  id: number
  source: string
  path: string
  method: string
  ip: string
  status_code: number
  latency_ms: number
  created_at: string
}

export interface ClaimLogItem {
  id: number
  gift_qrcode_id: number
  red_packet_id: number | null
  dispatch_strategy: string
  ip: string
  result: string
  reason: string
  created_at: string
}

export interface OperationLogItem {
  id: number
  user_id: number | null
  action: string
  detail: string
  created_at: string
}

export async function listAccessLogs(): Promise<AccessLogItem[]> {
  const response = await client.get<ApiEnvelope<AccessLogItem[]>>('/logs/access')
  return response.data.data
}

export async function listClaimLogs(): Promise<ClaimLogItem[]> {
  const response = await client.get<ApiEnvelope<ClaimLogItem[]>>('/logs/claims')
  return response.data.data
}

export async function listOperationLogs(): Promise<OperationLogItem[]> {
  const response = await client.get<ApiEnvelope<OperationLogItem[]>>('/logs/operations')
  return response.data.data
}
