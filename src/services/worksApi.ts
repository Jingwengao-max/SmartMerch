const DEFAULT_API_BASE = import.meta.env.DEV ? '' : window.location.origin
const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE).replace(/\/$/, '')

import type { CopyVariant, PosterDocument } from '@/services/posterApi'

export interface WorkSummary {
  id: string
  title: string
  previewUrl: string
  createdAt?: string
  updatedAt: string
}

export interface SaveWorkPayload {
  title?: string
  style?: string | null
  copy?: CopyVariant
  document: PosterDocument
}

/** 携带 HTTP 状态码的错误，便于区分 401（登录过期）等场景。 */
export class WorksApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'WorksApiError'
    this.status = status
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      throw new WorksApiError(response.status, `无法解析服务端响应（HTTP ${response.status}）`)
    }
  }
  if (!response.ok) {
    const detail = (payload as { detail?: string } | null)?.detail
    throw new WorksApiError(response.status, detail || `请求失败（HTTP ${response.status}）`)
  }
  return payload as T
}

/** 作品接口统一通过 HttpOnly Cookie 鉴权，必须显式带上 credentials。 */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { credentials: 'include', ...init })
  } catch {
    throw new WorksApiError(0, '无法连接服务，请确认后端已启动。')
  }
  return parseResponse<T>(response)
}

function jsonRequest<T>(path: string, method: 'POST' | 'PUT', body: SaveWorkPayload): Promise<T> {
  return request<T>(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function createWork(body: SaveWorkPayload): Promise<WorkSummary> {
  return jsonRequest<WorkSummary>('/api/works', 'POST', body)
}

export function updateWork(workId: string, body: SaveWorkPayload): Promise<WorkSummary> {
  return jsonRequest<WorkSummary>(`/api/works/${encodeURIComponent(workId)}`, 'PUT', body)
}

export interface WorkDetail {
  id: string
  title: string
  meta: { style?: string | null; copy?: CopyVariant; productName?: string }
  document: PosterDocument
  previewUrl: string
  createdAt: string
  updatedAt: string
}

export function listWorks(): Promise<{ works: WorkSummary[] }> {
  return request<{ works: WorkSummary[] }>('/api/works')
}

export function getWork(workId: string): Promise<WorkDetail> {
  return request<WorkDetail>(`/api/works/${encodeURIComponent(workId)}`)
}

export function deleteWork(workId: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/works/${encodeURIComponent(workId)}`, { method: 'DELETE' })
}
