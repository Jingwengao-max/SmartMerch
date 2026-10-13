const DEFAULT_API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:8000' : window.location.origin
const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE).replace(/\/$/, '')

export interface CopywritingOption {
  title: string
  subtitle: string
  sellingPoints?: string[]
  footer?: string
  launchText?: string
  badgeText?: string
}
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
  fontFamily?: string
  color?: string
  textAlign?: 'left' | 'center' | 'right'
  verticalAlign?: 'top' | 'middle' | 'bottom'
}
export interface PosterDocument {
  id: string
  name: string
  productName?: string
  templateId: string
  canvas: { width: number; height: number; backgroundImage?: string; backgroundColor?: string }
  elements: PosterElement[]
}
export interface PosterCandidate extends PosterDocument {
  previewUrl: string
  backgroundProvider: string
}
export interface GenerateResult {
  jobId: string
  input: {
    name: string
    feature: string
    sellingPoints: string[]
    footer: string
    launchText: string
    badgeText: string
    price: string
  }
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

export async function generateCopy(input: {
  jobId: string
  name: string
  feature: string
  sellingPoints: string[]
  footer: string
  launchText: string
  badgeText: string
}): Promise<CopyAnalysis & { jobId: string }> {
  const body = new FormData()
  body.append('jobId', input.jobId)
  body.append('name', input.name)
  body.append('feature', input.feature)
  body.append('selling_points', JSON.stringify(input.sellingPoints.filter(Boolean).slice(0, 3)))
  body.append('footer', input.footer)
  body.append('launch_text', input.launchText)
  body.append('badge_text', input.badgeText)
  return parseResponse<CopyAnalysis & { jobId: string }>(
    await fetch(`${API_BASE}/api/copy`, { method: 'POST', body })
  )
}

export async function translateProductName(text: string): Promise<string> {
  const result = await parseResponse<{ translation: string }>(
    await fetch(`${API_BASE}/api/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),
  )
  return result.translation
}

export async function refineCopy(input: {
  jobId: string
  current: CopywritingOption
  instruction: string
}): Promise<CopyAnalysis & { jobId: string }> {
  return parseResponse<CopyAnalysis & { jobId: string }>(
    await fetch(`${API_BASE}/api/copy/refine`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
  )
}

export async function generatePosters(input: {
  image: File
  name: string
  feature: string
  sellingPoints: string[]
  footer: string
  launchText: string
  badgeText: string
}): Promise<GenerateResult> {
  const body = new FormData()
  body.append('image', input.image)
  body.append('name', input.name)
  body.append('feature', input.feature)
  body.append('selling_points', JSON.stringify(input.sellingPoints.filter((item) => item.trim()).slice(0, 3)))
  body.append('footer', input.footer)
  body.append('launch_text', input.launchText)
  body.append('badge_text', input.badgeText)
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
