const DEFAULT_API_BASE = import.meta.env.DEV ? '' : window.location.origin
const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE).replace(/\/$/, '')

export interface AuthUser {
  id: string
  email: string
  name: string
}

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      // 后端未实现时 SPA 兜底会返回 200 的 HTML，必须当作失败，不能静默返回 null。
      throw new Error(`无法解析服务端响应（HTTP ${response.status}）`)
    }
  }
  if (!response.ok) {
    const detail = (payload as { detail?: string } | null)?.detail
    throw new Error(detail || `请求失败（HTTP ${response.status}）`)
  }
  return payload as T
}

/**
 * 认证接口统一通过 HttpOnly Cookie 鉴权，必须显式带上 credentials。
 * 统一处理三类错误：
 * - 网络错误（后端未启动）：提示无法连接。
 * - 服务端错误（非 2xx）：透传 detail 或 HTTP 状态。
 * - 非 JSON 响应（如 SPA 兜底 HTML）：视为失败。
 */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init })
  } catch {
    throw new Error('无法连接认证服务，请确认后端已启动。')
  }
  return parseResponse<T>(response)
}

function postJson<T>(path: string, body: Record<string, unknown>): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function login(email: string, password: string): Promise<AuthUser> {
  return postJson<AuthUser>('/api/auth/login', { email, password })
}

export function register(email: string, password: string): Promise<AuthUser> {
  return postJson<AuthUser>('/api/auth/register', { email, password })
}

/** 读取当前登录用户；未登录、后端未就绪或响应不是合法用户时抛错，由调用方归为 guest。 */
export async function me(): Promise<AuthUser> {
  const user = await request<AuthUser | null>('/api/auth/me')
  if (!user || typeof user.id !== 'string') {
    throw new Error('未登录')
  }
  return user
}

export function logout(): Promise<void> {
  return request<void>('/api/auth/logout', { method: 'POST' })
}
