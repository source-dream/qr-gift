import client from '../client'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
}

export interface StorageConfigResponse {
  provider: 'local' | 'minio' | 'aliyun'
  bucket: string
  base_url: string
  storage_prefix: string
  local_storage_dir: string
  minio_endpoint: string
  minio_secure: boolean
  minio_access_key_set: boolean
  minio_secret_key_set: boolean
  aliyun_oss_endpoint: string
  aliyun_oss_region: string
  aliyun_oss_access_key_id_set: boolean
  aliyun_oss_access_key_secret_set: boolean
}

export interface StorageConfigPayload {
  provider: 'local' | 'minio' | 'aliyun'
  bucket: string
  base_url: string
  storage_prefix: string
  local_storage_dir: string
  minio_endpoint: string
  minio_secure: boolean
  minio_access_key: string
  minio_secret_key: string
  aliyun_oss_endpoint: string
  aliyun_oss_region: string
  aliyun_oss_access_key_id: string
  aliyun_oss_access_key_secret: string
}

export interface ClaimContactResponse {
  contact_text: string
}

export interface StorageChannelItem {
  id: string
  name: string
  provider: 'local' | 'minio' | 'aliyun'
  enabled: boolean
  priority: number
  bucket: string
  base_url: string
  storage_prefix: string
  local_storage_dir: string
  minio_endpoint: string
  minio_secure: boolean
  minio_access_key: string
  minio_secret_key: string
  aliyun_oss_endpoint: string
  aliyun_oss_region: string
  aliyun_oss_access_key_id: string
  aliyun_oss_access_key_secret: string
  minio_access_key_set: boolean
  minio_secret_key_set: boolean
  aliyun_oss_access_key_id_set: boolean
  aliyun_oss_access_key_secret_set: boolean
}

export interface StorageChannelsResponse {
  channels: StorageChannelItem[]
}

export async function getStorageConfig(): Promise<StorageConfigResponse> {
  const response = await client.get<ApiEnvelope<StorageConfigResponse>>('/system/storage-config')
  return response.data.data
}

export async function updateStorageConfig(payload: StorageConfigPayload): Promise<void> {
  await client.put<ApiEnvelope<StorageConfigResponse>>('/system/storage-config', payload)
}

export async function testStorageConfig(payload: StorageConfigPayload): Promise<void> {
  await client.post<ApiEnvelope<null>>('/system/storage-config/test', payload)
}

export async function getClaimContact(): Promise<ClaimContactResponse> {
  const response = await client.get<ApiEnvelope<ClaimContactResponse>>('/system/claim-contact')
  return response.data.data
}

export async function updateClaimContact(contactText: string): Promise<void> {
  await client.put<ApiEnvelope<ClaimContactResponse>>('/system/claim-contact', {
    contact_text: contactText,
  })
}

export async function listStorageChannels(): Promise<StorageChannelItem[]> {
  const response = await client.get<ApiEnvelope<StorageChannelsResponse>>('/system/storage-channels')
  return response.data.data.channels
}

export async function updateStorageChannels(channels: StorageChannelItem[]): Promise<void> {
  await client.put<ApiEnvelope<StorageChannelsResponse>>('/system/storage-channels', { channels })
}

export async function testStorageChannel(channel: StorageChannelItem): Promise<void> {
  await client.post<ApiEnvelope<null>>('/system/storage-channels/test', channel)
}
