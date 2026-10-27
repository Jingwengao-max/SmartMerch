const DEFAULT_API_BASE = import.meta.env.DEV ? 'http://127.0.0.1:8000' : window.location.origin
const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE).replace(/\/$/, '')

/** 一条文案：键名由风格配置决定，值是字符串或字符串数组。 */
export type CopyVariant = Record<string, string | string[]>

export interface StyleField {
  key: string
  label: string
  kind: 'text' | 'list'
  maxChars: number
  maxItems: number
  generated: boolean
}

export interface StyleSpec {
  key: string
  label: string
  fields: StyleField[]
}

/** 与文案块一一对应的修改意见；留空的条目保持原样。 */
export type CopyFeedback = Record<string, string | string[]>
export interface CopyAnalysis {
  category: string
  color: string
  visible_features: string[]
  scene: string[]
  confidence: number
  warning: string
  copywriting: CopyVariant[]
  source: 'ai' | 'local_fallback'
}
export interface PosterElement {
  id: string
  type: 'image' | 'text' | 'shape'
  role?: string
  src?: string
  content?: string
  shape?: 'rect' | 'tech-corner' | 'soft-shadow'
  fill?: string
  opacity?: number
  radius?: number
  blur?: number
  x: number
  y: number
  width: number
  height: number
  rotation?: number
  zIndex: number
  fontSize?: number
  fontWeight?: number
  fontFamily?: string
  letterSpacing?: number
  lineSpacings?: number[]
  lineAlignments?: Array<'left' | 'center' | 'right' | 'justify'>
  lineHeight?: number
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
  input: Record<string, unknown>
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

export async function fetchStyleSpecs(): Promise<Record<string, StyleSpec>> {
  const payload = await parseResponse<{ styles: StyleSpec[] }>(
    await fetch(`${API_BASE}/api/styles`)
  )
  return Object.fromEntries(payload.styles.map((item) => [item.key, item]))
}

export async function generateCopy(input: {
  jobId: string
  style: string
  context: CopyVariant
}): Promise<CopyAnalysis & { jobId: string }> {
  const body = new FormData()
  body.append('jobId', input.jobId)
  body.append('style', input.style)
  body.append('context', JSON.stringify(input.context))
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
  style: string
  current: CopyVariant
  feedback: CopyFeedback
}): Promise<CopyAnalysis & { jobId: string }> {
  return parseResponse<CopyAnalysis & { jobId: string }>(
    await fetch(`${API_BASE}/api/copy/refine`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jobId: input.jobId,
        style: input.style,
        current: input.current,
        feedback: input.feedback,
      }),
    })
  )
}

export async function generatePosters(input: {
  image: File
  style: string
  copy: CopyVariant
}): Promise<GenerateResult> {
  const body = new FormData()
  body.append('image', input.image)
  body.append('style', input.style)
  body.append('copy', JSON.stringify(input.copy))
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
