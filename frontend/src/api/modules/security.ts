import client from '../client'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
}

export interface SecurityRules {
  claim_enabled: boolean
  ip_whitelist: string[]
  ip_blacklist: string[]
  max_per_ip_per_hour: number
}

export async function getSecurityRules(): Promise<SecurityRules> {
  const response = await client.get<ApiEnvelope<{ rules: SecurityRules }>>('/security/rules')
  return response.data.data.rules
}

export async function updateSecurityRules(rules: SecurityRules): Promise<void> {
  await client.put<ApiEnvelope<{ rules: SecurityRules }>>('/security/rules', rules)
}
