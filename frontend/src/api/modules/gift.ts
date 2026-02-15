import client from '../client'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
}

function resolveWebOrigin(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.location.origin
}

export interface GiftItem {
  id: number
  title: string
  status: string
  activate_at: string | null
  expire_at: string | null
  binding_mode: string
  dispatch_strategy: string
  binding_count: number
  style_type: string
  image_url: string
  claim_url: string
}

export interface CreateGiftPayload {
  title: string
  activate_at: string | null
  expire_at: string | null
  binding_mode: 'manual' | 'auto'
  dispatch_strategy: 'amount_desc' | 'level_desc' | 'random'
  red_packet_ids: number[]
  style_type: string
}

export interface CreateGiftResult {
  id: number
  title: string
  claim_url: string
}

export interface UpdateGiftPayload {
  title: string
  activate_at: string | null
  expire_at: string | null
  binding_mode: 'manual' | 'auto'
  dispatch_strategy: 'amount_desc' | 'level_desc' | 'random'
  red_packet_ids: number[]
  style_type: string
}

export interface GiftDetail {
  id: number
  title: string
  status: string
  activate_at: string | null
  expire_at: string | null
  binding_mode: 'manual' | 'auto'
  dispatch_strategy: 'amount_desc' | 'level_desc' | 'random'
  style_type: string
  image_url: string
  claim_url: string
  red_packet_ids: number[]
}

export interface RegenerateGiftQrcodeResult {
  claim_url: string
  image_url: string
}

export interface GiftQrcodeDownloadUrlResult {
  url: string
}

export async function createGift(payload: CreateGiftPayload): Promise<CreateGiftResult> {
  const response = await client.post<ApiEnvelope<CreateGiftResult>>('/gifts', payload, {
    headers: {
      'X-Web-Origin': resolveWebOrigin(),
    },
  })
  return response.data.data
}

export async function listGifts(): Promise<GiftItem[]> {
  const response = await client.get<ApiEnvelope<GiftItem[]>>('/gifts')
  return response.data.data
}

export async function getGiftById(giftId: number): Promise<GiftDetail> {
  const response = await client.get<ApiEnvelope<GiftDetail>>(`/gifts/${giftId}`)
  return response.data.data
}

export async function activateGift(giftId: number): Promise<void> {
  await client.post(`/gifts/${giftId}/activate`)
}

export async function disableGift(giftId: number): Promise<void> {
  await client.post(`/gifts/${giftId}/disable`)
}

export async function updateGift(giftId: number, payload: UpdateGiftPayload): Promise<void> {
  await client.put(`/gifts/${giftId}`, payload)
}

export async function deleteGift(giftId: number): Promise<void> {
  await client.delete(`/gifts/${giftId}`)
}

export async function regenerateGiftQrcode(giftId: number): Promise<RegenerateGiftQrcodeResult> {
  const response = await client.post<ApiEnvelope<RegenerateGiftQrcodeResult>>(
    `/gifts/${giftId}/regenerate-qrcode`,
    undefined,
    {
      headers: {
        'X-Web-Origin': resolveWebOrigin(),
      },
    },
  )
  return response.data.data
}

export async function getGiftQrcodeDownloadUrl(giftId: number): Promise<string> {
  const response = await client.get<ApiEnvelope<GiftQrcodeDownloadUrlResult>>(
    `/gifts/${giftId}/qrcode-download-url`,
  )
  return response.data.data.url
}
