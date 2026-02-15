import client from '../client'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
}

export interface RedPacketItem {
  id: number
  title: string
  amount: number
  level: number
  category_name: string
  category_code: string
  tags: string[]
  content_type: 'url' | 'text' | 'qr_image'
  content_value: string
  content_image_url: string
  status: string
  meta: Record<string, string>
  available_from: string | null
  available_to: string | null
}

export interface RedPacketCategory {
  id: number
  name: string
  code: string
  is_builtin: boolean
  allowed_content_types: Array<'url' | 'text' | 'qr_image'>
}

export interface CreateRedPacketPayload {
  title: string
  amount: number
  level: number
  category_code?: string
  custom_category_name?: string
  content_type: 'url' | 'text' | 'qr_image'
  content_value: string
  tags: string[]
  meta: Record<string, string>
  available_from: string | null
  available_to: string | null
}

export interface UpdateRedPacketPayload {
  title: string
  amount: number
  level: number
  content_value: string
  available_from: string | null
  available_to: string | null
}

export interface ParsedImageUrlItem {
  filename: string
  status: 'success' | 'failed'
  decoded_url: string
}

export interface ParseImagesResult {
  success_count: number
  failed_count: number
  results: ParsedImageUrlItem[]
}

export async function listRedPackets(): Promise<RedPacketItem[]> {
  const response = await client.get<ApiEnvelope<RedPacketItem[]>>('/red-packets')
  return response.data.data
}

export async function listRedPacketCategories(): Promise<RedPacketCategory[]> {
  const response = await client.get<ApiEnvelope<RedPacketCategory[]>>('/red-packets/categories')
  return response.data.data
}

export async function createRedPacketCategory(name: string): Promise<RedPacketCategory> {
  const response = await client.post<ApiEnvelope<RedPacketCategory>>('/red-packets/categories', { name })
  return response.data.data
}

export async function createRedPacket(payload: CreateRedPacketPayload): Promise<void> {
  await client.post<ApiEnvelope<null>>('/red-packets', payload)
}

export async function updateRedPacket(redPacketId: number, payload: UpdateRedPacketPayload): Promise<void> {
  await client.put<ApiEnvelope<null>>(`/red-packets/${redPacketId}`, payload)
}

export async function disableRedPacket(redPacketId: number): Promise<void> {
  await client.post<ApiEnvelope<null>>(`/red-packets/${redPacketId}/disable`)
}

export async function enableRedPacket(redPacketId: number): Promise<void> {
  await client.post<ApiEnvelope<null>>(`/red-packets/${redPacketId}/enable`)
}

export async function deleteRedPacket(redPacketId: number): Promise<void> {
  await client.delete<ApiEnvelope<null>>(`/red-packets/${redPacketId}`)
}

export async function batchImportRedPacketImages(payload: {
  files: File[]
  titlePrefix: string
  amount: number
  level: number
  categoryCode: string
  tags: string[]
}): Promise<{ batch_no: string; imported_count: number }> {
  const formData = new FormData()
  for (const file of payload.files) {
    formData.append('files', file)
  }
  formData.append('title_prefix', payload.titlePrefix)
  formData.append('amount', String(payload.amount))
  formData.append('level', String(payload.level))
  formData.append('category_code', payload.categoryCode)
  formData.append('tags', payload.tags.join(','))

  const response = await client.post<ApiEnvelope<{ batch_no: string; imported_count: number }>>(
    '/red-packets/batch-images',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  )
  return response.data.data
}

export async function parseImagesToUrls(files: File[]): Promise<ParseImagesResult> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  const response = await client.post<ApiEnvelope<ParseImagesResult>>('/red-packets/parse-images-to-urls', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data.data
}

export async function batchImportRedPacketUrls(payload: {
  titlePrefix: string
  amount: number
  level: number
  categoryCode: string
  tags: string[]
  availableFrom: string | null
  availableTo: string | null
  urls: Array<{ filename: string; url: string }>
}): Promise<{ batch_no: string; imported_count: number }> {
  const response = await client.post<ApiEnvelope<{ batch_no: string; imported_count: number }>>(
    '/red-packets/batch-urls',
    {
      title_prefix: payload.titlePrefix,
      amount: payload.amount,
      level: payload.level,
      category_code: payload.categoryCode,
      tags: payload.tags,
      available_from: payload.availableFrom,
      available_to: payload.availableTo,
      urls: payload.urls,
    },
  )
  return response.data.data
}
