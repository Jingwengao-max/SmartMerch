const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export interface CopywritingOption { title: string; subtitle: string }
export interface CopyAnalysis {
  category: string
  color: string
  visible_features: string[]
  scene: string[]
  confidence: number
  warning: string
  copywriting: CopywritingOption[]
  source: 'ai' | 'local_fallback'
}
export interface PosterElement {
  id: string
  type: 'image' | 'text'
  role?: string
  src?: string
  content?: string
  x: number
  y: number
  width: number
  height: number
  rotation?: number
  zIndex: number
  fontSize?: number
  fontWeight?: number
  color?: string
}
export interface PosterDocument {
  id: string
  name: string
  templateId: string
  canvas: { width: number; height: number; backgroundImage?: string; backgroundColor?: string }
  elements: PosterElement[]
}
export interface PosterCandidate extends PosterDocument {
  previewUrl: string
  backgroundProvider: string
  quality?: { overall: number }
}
export interface GenerateResult {
  jobId: string
  input: { name: string; feature: string; vibe: string; style: string; price: string }
  candidates: PosterCandidate[]
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)
  if (!response.ok) throw new Error(payload?.detail || `请求失败（HTTP ${response.status}）`)
  return payload as T
}

export function assetUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (/^(https?:|data:|blob:)/.test(path)) return path
  return `${API_BASE}${path.startsWith('/') ? '' : '/'}${path}`
}

export async function cutoutProduct(file: File) {
  const body = new FormData()
  body.append('image', file)
  return parseResponse<{ jobId: string; imageName: string; cutoutUrl: string }>(
    await fetch(`${API_BASE}/api/cutout`, { method: 'POST', body })
  )
}

export async function analyzeCopy(file: File): Promise<CopyAnalysis> {
  const body = new FormData()
  body.append('image', file)
  return parseResponse<CopyAnalysis>(
    await fetch(`${API_BASE}/api/analyze-copy`, { method: 'POST', body })
  )
}

export async function generatePosters(input: {
  image: File
  name: string
  feature: string
  vibe: string
  style: string
}): Promise<GenerateResult> {
  const body = new FormData()
  body.append('image', input.image)
  body.append('name', input.name)
  body.append('feature', input.feature)
  body.append('vibe', input.vibe)
  body.append('style', input.style)
  return parseResponse<GenerateResult>(
    await fetch(`${API_BASE}/api/generate`, { method: 'POST', body })
  )
}

export async function renderPoster(document: PosterDocument): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/render`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(document),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || `导出失败（HTTP ${response.status}）`)
  }
  return response.blob()
}
