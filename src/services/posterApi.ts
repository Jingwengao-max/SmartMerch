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

export interface CopyVariant {
  title: string
  subtitle: string
  selling_points: string[]
  price_text: string
  promo_text: string
  price_estimated?: boolean
}
/** 与文案块一一对应的修改意见，未填的条目保持原样。 */
export interface CopyFeedback {
  title: string
  subtitle: string
  selling_points: string[]
  price_text: string
  promo_text: string
}
export interface CopyIdentification {
  category: string
  color: string
  visible_features: string[]
  scene: string[]
  confidence: number
  warning: string
}
export interface CopySet {
  source: 'ai' | 'local_fallback'
  identification: CopyIdentification
  variants: CopyVariant[]
  refinedFrom?: CopyVariant
  suggested: {
    name: string
    feature: string
    price: string
    promo: string
    selling_points: string[]
  }
  meta?: Record<string, unknown>
  jobId?: string
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
  input: {
    name: string
    feature: string
    vibe: string
    style: string
    price: string
    promo?: string
    selling_points?: string[]
  }
  skippedTemplates?: { templateId: string; reason: string }[]
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
  jobId?: string
  image?: File
  name?: string
  feature?: string
  sellingPoints?: string[]
  vibe?: string
  style?: string
  price?: string
  promo?: string
}): Promise<CopySet> {
  const body = new FormData()
  if (input.jobId) body.append('jobId', input.jobId)
  if (input.image) body.append('image', input.image)
  body.append('name', input.name ?? '')
  body.append('feature', input.feature ?? '')
  body.append('selling_points', JSON.stringify(input.sellingPoints ?? []))
  body.append('vibe', input.vibe ?? '')
  body.append('style', input.style ?? '')
  body.append('price', input.price ?? '')
  body.append('promo', input.promo ?? '')
  return parseResponse<CopySet>(
    await fetch(`${API_BASE}/api/copy`, { method: 'POST', body })
  )
}

export async function refineCopy(input: {
  jobId: string
  current: CopyVariant
  feedback: CopyFeedback
  context?: {
    name?: string
    feature?: string
    sellingPoints?: string[]
    vibe?: string
    style?: string
    price?: string
    promo?: string
  }
}): Promise<CopySet> {
  const response = await fetch(`${API_BASE}/api/copy/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jobId: input.jobId,
      current: input.current,
      feedback: input.feedback,
      context: {
        name: input.context?.name ?? '',
        feature: input.context?.feature ?? '',
        selling_points: input.context?.sellingPoints ?? [],
        vibe: input.context?.vibe ?? '',
        style: input.context?.style ?? '',
        price: input.context?.price ?? '',
        promo: input.context?.promo ?? '',
      },
    }),
  })
  return parseResponse<CopySet>(response)
}

export async function generatePosters(input: {
  image: File
  name: string
  feature: string
  vibe: string
  style: string
  price?: string
  promo?: string
  sellingPoints?: string[]
}): Promise<GenerateResult> {
  const body = new FormData()
  body.append('image', input.image)
  body.append('name', input.name)
  body.append('feature', input.feature)
  body.append('vibe', input.vibe)
  body.append('style', input.style)
  body.append('price', input.price ?? '')
  body.append('promo', input.promo ?? '')
  body.append('selling_points', JSON.stringify(input.sellingPoints ?? []))
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
