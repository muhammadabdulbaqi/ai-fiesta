// API client configured to connect to FastAPI backend
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// Token management
const TOKEN_KEY = "fiesta_auth_token"

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeAuthToken(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(TOKEN_KEY)
}

// Helper to get auth headers
function getAuthHeaders(): HeadersInit {
  // Try regular token first, then admin token
  let token = getAuthToken()
  if (!token) {
    token = getAdminToken()
  }
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }
  return headers
}

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
  user_email?: string
  user_username?: string
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
  provider: "gemini" | "openai" | "anthropic" | "grok" | "perplexity" | "mock"
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user_id: string
  email: string
  username: string
  role?: "admin" | "user"
}

export interface User {
  id: string
  email: string
  username: string
  is_active: boolean
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

export async function getTokenUsage(): Promise<TokenUsage> {
  const res = await fetch(`${API_URL}/subscriptions/me`, {
    headers: getAuthHeaders()
  })
  if (!res.ok) {
    const errorText = await res.text()
    let errorMessage = "Failed to fetch token usage"
    try {
      const errorJson = JSON.parse(errorText)
      errorMessage = errorJson.detail || errorMessage
    } catch {
      // If not JSON, use status text
      errorMessage = res.status === 401 || res.status === 403 
        ? "Unauthorized" 
        : `Failed to fetch token usage: ${res.status} ${res.statusText}`
    }
    const error = new Error(errorMessage)
    ;(error as any).status = res.status
    throw error
  }
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

export async function getSubscription(): Promise<Subscription> {
  const res = await fetch(`${API_URL}/subscriptions/me`, {
    headers: getAuthHeaders()
  })
  if (!res.ok) {
    const errorText = await res.text()
    let errorMessage = "Failed to fetch subscription"
    try {
      const errorJson = JSON.parse(errorText)
      errorMessage = errorJson.detail || errorMessage
    } catch {
      errorMessage = res.status === 401 || res.status === 403 
        ? "Unauthorized" 
        : `Failed to fetch subscription: ${res.status} ${res.statusText}`
    }
    const error = new Error(errorMessage)
    ;(error as any).status = res.status
    throw error
  }
  const data = await res.json()
  // Transform FastAPI response
  return {
    id: data.id || `sub-${data.user_id}`,
    user_id: data.user_id,
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

// Admin token management
const ADMIN_TOKEN_KEY = "fiesta_admin_token"

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(ADMIN_TOKEN_KEY)
}

export function setAdminToken(token: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(ADMIN_TOKEN_KEY, token)
}

export function removeAdminToken(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(ADMIN_TOKEN_KEY)
}

function getAdminAuthHeaders(): HeadersInit {
  const token = getAdminToken()
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }
  return headers
}

export async function getAdminStats(): Promise<AdminStats> {
  const res = await fetch(`${API_URL}/admin/usage`, {
    headers: getAdminAuthHeaders()
  })
  if (!res.ok) throw new Error("Failed to fetch admin stats")
  return res.json()
}

export async function getModelsRich(): Promise<ModelRichInfo[]> {
  const res = await fetch(`${API_URL}/chat/models/formatted`)
  if (!res.ok) throw new Error("Failed to fetch models")
  return res.json()
}

export async function getAllSubscriptions(): Promise<Subscription[]> {
  const res = await fetch(`${API_URL}/admin/subscriptions`, {
    headers: getAdminAuthHeaders()
  })
  if (!res.ok) throw new Error("Failed to fetch subscriptions")
  const data = await res.json()
  // Transform FastAPI response format
  if (Array.isArray(data)) {
    return data.map((sub: any) => ({
      id: `sub-${sub.user_id}`,
      user_id: sub.user_id,
      user_email: sub.user_email || sub.email || "",
      user_username: sub.user_username || sub.username || "",
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

export async function addTokens(tokens: number) {
  const res = await fetch(`${API_URL}/subscriptions/me/add-tokens`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(tokens),
  })
  if (!res.ok) throw new Error("Failed to add tokens")
  return res.json()
}

export async function addCredits(credits: number) {
  const res = await fetch(`${API_URL}/subscriptions/me/add-credits`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(credits),
  })
  if (!res.ok) throw new Error("Failed to add credits")
  return res.json()
}

export async function upgradeSubscription(tier: string) {
  const res = await fetch(`${API_URL}/subscriptions/me/upgrade?tier=${encodeURIComponent(tier)}`, {
    method: "POST",
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to upgrade subscription")
  return res.json()
}

export async function useTokens(tokens: number) {
  const res = await fetch(`${API_URL}/subscriptions/me/use-tokens`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(tokens),
  })
  if (!res.ok) throw new Error("Failed to deduct tokens")
  return res.json()
}

export async function useCredits(credits: number) {
  const res = await fetch(`${API_URL}/subscriptions/me/use-credits`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(credits),
  })
  if (!res.ok) throw new Error("Failed to deduct credits")
  return res.json()
}

// Admin functions
export async function adminLogin(email: string, password: string) {
  const res = await fetch(`${API_URL}/admin/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const error = await res.json()
    throw new Error(error.detail || "Admin login failed")
  }
  const data = await res.json()
  setAdminToken(data.access_token)
  return data
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

// Authentication functions
export async function register(email: string, username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, username, password }),
  })
  if (!res.ok) {
    const error = await res.json()
    throw new Error(error.detail || "Registration failed")
  }
  const data = await res.json()
  setAuthToken(data.access_token)
  return data
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const error = await res.json()
    throw new Error(error.detail || "Login failed")
  }
  const data = await res.json()
  
  // Check if token has admin role by decoding it (simple check)
  // If it's an admin, store in both places so they can access both admin and regular endpoints
  try {
    const tokenParts = data.access_token.split('.')
    if (tokenParts.length === 3) {
      const payload = JSON.parse(atob(tokenParts[1]))
      if (payload.role === "admin") {
        // Store as both admin token AND regular token
        // This allows admins to access both admin endpoints and regular user endpoints
        setAdminToken(data.access_token)
        setAuthToken(data.access_token) // Also store as regular token
        data.role = "admin"
      } else {
        // Store as regular user token only
        setAuthToken(data.access_token)
        data.role = "user"
      }
    } else {
      // Fallback: store as regular token
      setAuthToken(data.access_token)
      data.role = "user"
    }
  } catch {
    // Fallback: store as regular token
    setAuthToken(data.access_token)
    data.role = "user"
  }
  
  return data
}

export async function getCurrentUser(): Promise<User> {
  const res = await fetch(`${API_URL}/auth/me`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to fetch current user")
  return res.json()
}

export function logout(): void {
  removeAuthToken()
  removeAdminToken()
}

// Update existing functions to use auth headers
export async function getConversations(): Promise<ConversationSummary[]> {
  const res = await fetch(`${API_URL}/conversations/`, {
    headers: getAuthHeaders()
  })
  if (!res.ok) throw new Error("Failed to fetch conversations")
  return res.json()
}

export async function getConversationMessages(conversationId: string): Promise<Message[]> {
  const res = await fetch(`${API_URL}/conversations/${conversationId}/messages`, {
    headers: getAuthHeaders()
  })
  if (!res.ok) {
    const errorText = await res.text()
    let errorMessage = "Failed to fetch conversation messages"
    try {
      const errorJson = JSON.parse(errorText)
      errorMessage = errorJson.detail || errorMessage
    } catch {
      errorMessage = res.status === 401 || res.status === 403 
        ? "Unauthorized" 
        : `Failed to fetch messages: ${res.status} ${res.statusText}`
    }
    const error = new Error(errorMessage)
    ;(error as any).status = res.status
    throw error
  }
  const data = await res.json()
  // Transform backend message format to frontend format
  // Backend returns Message objects with: id, conversation_id, role, content, model, total_tokens, created_at
  return data.map((msg: any) => ({
    id: msg.id,
    role: (msg.role || msg.sender || "user") as "user" | "assistant",
    content: msg.content || "",
    model: msg.model || undefined,
    tokens_used: msg.total_tokens || msg.tokens || undefined,
    credits_used: undefined, // Not in backend response
    timestamp: new Date(msg.created_at || msg.timestamp || Date.now()),
  }))
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${API_URL}/conversations/${conversationId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to delete conversation")
}