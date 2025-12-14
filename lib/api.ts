// API client configured to connect to FastAPI backend
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  model?: string
  tokens_used?: number
  credits_used?: number
  timestamp: Date
}

export interface TokenUsage {
  tokens_used: number
  tokens_remaining: number
  tokens_limit: number
  credits_used: number
  credits_remaining: number
  credits_limit: number
  percentage_used: number
}

export interface Subscription {
  id: string
  user_id: string
  tier_name: "Free" | "Pro" | "Enterprise"
  tier_id: "free" | "pro" | "enterprise"
  allowed_models: string[]
  tokens_limit: number
  tokens_used: number
  tokens_remaining: number
  credits_limit: number
  credits_used: number
  credits_remaining: number
  status: "active" | "expired" | "suspended"
  monthly_cost_usd: number
}

export interface Model {
  value: string
  label: string
  tier: "free" | "pro" | "enterprise"
  provider: "gemini" | "openai" | "anthropic" | "mock"
}

export interface AdminStats {
  total_users_with_usage: number
  total_api_calls_made: number
  total_tokens_consumed: number
  total_cost_usd: number
  by_provider: {
    [provider: string]: {
      calls: number
      tokens: number
      cost: number
    }
  }
}

export async function getTokenUsage(userId: string): Promise<TokenUsage> {
  const res = await fetch(`${API_URL}/subscriptions/${userId}`)
  if (!res.ok) throw new Error("Failed to fetch token usage")
  const data = await res.json()
  // Transform FastAPI response to match frontend interface
  return {
    tokens_used: data.tokens_used || 0,
    tokens_remaining: data.tokens_remaining || 0,
    tokens_limit: data.tokens_limit || 0,
    credits_used: data.credits_used || 0,
    credits_remaining: data.credits_remaining || 0,
    credits_limit: data.credits_limit || 0,
    percentage_used: data.tokens_limit > 0 ? (data.tokens_used / data.tokens_limit) * 100 : 0,
  }
}

export interface ConversationSummary {
  id: string
  title: string | null
  created_at: string
  total_cost_usd: number
  total_tokens: number
}

export interface ModelRichInfo {
  value: string
  label: string
  provider: string
  tier: "free" | "pro" | "enterprise"
  description: string
  input_cost: number
  output_cost: number
}

export async function getSubscription(userId: string): Promise<Subscription> {
  const res = await fetch(`${API_URL}/subscriptions/${userId}`)
  if (!res.ok) throw new Error("Failed to fetch subscription")
  const data = await res.json()
  // Transform FastAPI response
  return {
    id: data.id || `sub-${userId}`,
    user_id: userId,
    tier_name: data.tier_name || "Free",
    tier_id: data.tier_id || "free",
    allowed_models: data.allowed_models || [],
    tokens_limit: data.tokens_limit || 1000,
    tokens_used: data.tokens_used || 0,
    tokens_remaining: data.tokens_remaining || 1000,
    credits_limit: data.credits_limit || 500,
    credits_used: data.credits_used || 0,
    credits_remaining: data.credits_remaining || 500,
    status: data.status || "active",
    monthly_cost_usd: data.monthly_cost_usd || 0,
  }
}

export async function getAdminStats(): Promise<AdminStats> {
  const res = await fetch(`${API_URL}/admin/usage`)
  if (!res.ok) throw new Error("Failed to fetch admin stats")
  return res.json()
}

export async function getConversations(userId: string): Promise<ConversationSummary[]> {
  const res = await fetch(`${API_URL}/conversations/`, {
    headers: { "user-id": userId }
  })
  if (!res.ok) throw new Error("Failed to fetch conversations")
  return res.json()
}

export async function getModelsRich(): Promise<ModelRichInfo[]> {
  const res = await fetch(`${API_URL}/chat/models/formatted`)
  if (!res.ok) throw new Error("Failed to fetch models")
  return res.json()
}

export async function getAllSubscriptions(): Promise<Subscription[]> {
  const res = await fetch(`${API_URL}/admin/subscriptions`)
  if (!res.ok) throw new Error("Failed to fetch subscriptions")
  const data = await res.json()
  // Transform FastAPI response format
  if (Array.isArray(data)) {
    return data.map((sub: any) => ({
      id: `sub-${sub.user_id}`,
      user_id: sub.user_id,
      tier_name: sub.tier || sub.tier_name || "Free",
      tier_id: (sub.tier || sub.tier_name || "free").toLowerCase(),
      allowed_models: sub.allowed_models || [],
      tokens_limit: sub.tokens_limit || 1000,
      tokens_used: sub.tokens_used || 0,
      tokens_remaining: sub.tokens_remaining || 0,
      credits_limit: sub.credits_limit || 500,
      credits_used: sub.credits_used || 0,
      credits_remaining: sub.credits_remaining || 0,
      status: sub.status || "active",
      monthly_cost_usd: sub.monthly_cost_usd || 0,
    }))
  }
  return []
}

export async function addTokens(userId: string, tokens: number) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/add-tokens`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tokens),
  })
  if (!res.ok) throw new Error("Failed to add tokens")
  return res.json()
}

export async function addCredits(userId: string, credits: number) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/add-credits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credits),
  })
  if (!res.ok) throw new Error("Failed to add credits")
  return res.json()
}

export async function upgradeSubscription(userId: string, tier: string) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/upgrade?tier=${encodeURIComponent(tier)}`, {
    method: "POST",
  })
  if (!res.ok) throw new Error("Failed to upgrade subscription")
  return res.json()
}

export async function useTokens(userId: string, tokens: number) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/use-tokens`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tokens),
  })
  if (!res.ok) throw new Error("Failed to deduct tokens")
  return res.json()
}

export async function useCredits(userId: string, credits: number) {
  const res = await fetch(`${API_URL}/subscriptions/${userId}/use-credits`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credits),
  })
  if (!res.ok) throw new Error("Failed to deduct credits")
  return res.json()
}

// export async function getAvailableModels(): Promise<Model[]> {
//   const res = await fetch(`${API_URL}/chat/models/formatted`)
//   if (!res.ok) throw new Error("Failed to fetch models")
//   const data = await res.json()
  
//   // Data is already in the correct format from the new endpoint
//   return data
// }

export async function getAvailableModels() {
  return getModelsRich()
}