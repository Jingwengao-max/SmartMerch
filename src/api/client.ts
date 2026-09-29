/**
 * 后端接口封装（poster-design 的 service）。
 *
 * 有两处约定和常见后端不同，改动前务必留意：
 * 1. 响应信封是 { code, msg, result }，业务数据在 result 里，不是 data；
 *    而且 result 为空时后端会整个省略该字段。
 * 2. 鉴权头是**裸 token**，不能加 "Bearer " 前缀——后端直接拿 header 原值
 *    去验签，多一个前缀就会判签名不符，表现为所有接口 401。
 *
 * 另外后端有两套路径前缀：/api/*（AI、上传、用户、后台）和 /design/*
 * （模板、素材、字体、作品）。写新接口时别混。
 */

const API_BASE = ((import.meta.env.VITE_API_URL as string | undefined) ?? '').replace(/\/$/, '')

/** 与 poster-design 共用的登录态存储 key */
const TOKEN_KEY = 'xp_token'

export interface CutoutResult {
  url: string
  width: number
  height: number
}

export interface CutoutOptions {
  /** 模型名，默认 u2netp；可选 isnet-general-use / birefnet-general 等 */
  model?: string
  /** 是否净化蒙版，边缘更干净但细节略损 */
  postProcess?: boolean
  /** 背景色，如 #FFFFFF，传了就把透明区填成该色 */
  bgcolor?: string
  /** 边缘羽化像素 0~50 */
  feather?: number
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/** 把后端返回的相对地址（/static/...）补成当前环境可访问的地址 */
export function resolveAssetUrl(url: string): string {
  if (!url) return url
  if (/^(https?:|blob:|data:)/i.test(url)) return url
  return `${API_BASE}${url}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  // 注意：裸 token，不加 Bearer 前缀
  if (token) headers.set('Authorization', token)

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  const text = await response.text()

  let body: any
  try {
    body = JSON.parse(text)
  } catch {
    throw new Error(`接口返回了非 JSON 内容（HTTP ${response.status}）`)
  }

  if (body?.code === 401) {
    clearToken()
    throw new Error('登录已失效，请重新登录')
  }
  if (body?.code !== 200) {
    throw new Error(body?.msg || `请求失败（HTTP ${response.status}）`)
  }
  // result 为空时后端会省略该字段，此时整个 body 就是结果
  return (body.result ?? body) as T
}

/** 抠图：上传商品图，返回透明背景 PNG 的地址 */
export async function cutout(file: Blob, options: CutoutOptions = {}): Promise<CutoutResult> {
  const form = new FormData()
  form.append('file', file, (file as File).name || 'image.png')
  if (options.model) form.append('model', options.model)
  if (options.postProcess) form.append('post_process', 'true')
  if (options.bgcolor) form.append('bgcolor', options.bgcolor)
  if (options.feather) form.append('feather', String(options.feather))

  // 不要手动设 Content-Type，multipart 的 boundary 必须由浏览器生成
  return request<CutoutResult>('/api/ai/cutout', { method: 'POST', body: form })
}

export interface AuthResult {
  token: string
  account: string
  role: number
}

/** 登录，成功后会写入本地 token */
export async function login(account: string, password: string): Promise<AuthResult> {
  const result = await request<AuthResult>('/api/user/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ account, password }),
  })
  setToken(result.token)
  return result
}

/** 注册，成功后会写入本地 token */
export async function register(account: string, password: string): Promise<AuthResult> {
  const result = await request<AuthResult>('/api/user/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ account, password }),
  })
  setToken(result.token)
  return result
}
