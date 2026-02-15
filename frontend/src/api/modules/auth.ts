import client from '../client'

interface LoginData {
  access_token: string
  token_type: string
}

interface BootstrapStatus {
  initialized: boolean
}

interface SetupResult {
  user_id: number
  username: string
}

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
}

export async function loginApi(username: string, password: string): Promise<LoginData> {
  const response = await client.post<ApiEnvelope<LoginData>>('/auth/login', { username, password })
  return response.data.data
}

export async function getBootstrapStatusApi(): Promise<BootstrapStatus> {
  const response = await client.get<ApiEnvelope<BootstrapStatus>>('/auth/bootstrap-status')
  return response.data.data
}

export async function setupAdminApi(username: string, password: string): Promise<SetupResult> {
  const response = await client.post<ApiEnvelope<SetupResult>>('/auth/setup', { username, password })
  return response.data.data
}
