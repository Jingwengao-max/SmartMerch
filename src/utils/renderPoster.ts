/**
 * 海报渲染器（Canvas 2D）。
 *
 * 预览和导出走的是同一套代码：给同一个模板和同一份数据，
 * 只是 width / pixelRatio 不同，所以"所见即所得"。
 *
 * 之所以不用 DOM + html2canvas：一是省一个依赖，二是导出时不会被外链图片
 * 的 CORS 和字体时序坑到，三是这套描述以后要搬到后端（sharp / node-canvas）
 * 渲染时，逻辑是同构的。
 */
import type { ColorRole, Palette, PosterLayer, PosterTemplate } from '@/data/templates'

export interface PosterData {
  imageUrl: string | null
  name: string
  feature: string
  vibe: string
  styleName: string
  styleEn: string
}

export interface RenderOptions {
  /** 逻辑宽度（画布最终按这个宽度布局），默认 900 */
  width?: number
  /** 超采样倍数，2 表示按 2 倍分辨率出图，默认 2 */
  pixelRatio?: number
}

const FONT_STACKS: Record<string, string> = {
  display: '"LXGW WenKai", "Kaiti SC", "STKaiti", serif',
  body: '"LXGW WenKai", "Noto Sans SC", "PingFang SC", sans-serif',
  mono: '"SF Mono", ui-monospace, Menlo, Monaco, monospace',
}

function resolveColor(role: ColorRole | undefined, palette: Palette): string {
  switch (role) {
    case 'fg':
      return palette.fg
    case 'accent':
      return palette.accent
    case 'soft':
      return palette.soft
    case 'deep':
      return palette.deep
    case 'none':
      return 'transparent'
    default:
      return palette.bg
  }
}

// ── 文本换行 ────────────────────────────────────────────────

/** 中日韩字符与全角标点，这类字符可以逐字断行 */
const CJK = /[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef\u3000-\u303f]/

/** 把文本切成"可断行单元"：中文按字、英文按词、空格单独成 token */
function tokenize(text: string): string[] {
  const tokens: string[] = []
  let buffer = ''
  const flush = () => {
    if (buffer) {
      tokens.push(buffer)
      buffer = ''
    }
  }
  for (const char of text) {
    if (CJK.test(char)) {
      flush()
      tokens.push(char)
    } else if (/\s/.test(char)) {
      flush()
      tokens.push(' ')
    } else {
      buffer += char
    }
  }
  flush()
  return tokens
}

/** 截断到能放下为止并补省略号（用于超出 clamp 行数的最后一行） */
function clipWithEllipsis(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
  let cut = text
  while (cut.length > 1 && ctx.measureText(cut + '…').width > maxWidth) {
    cut = cut.slice(0, -1)
  }
  return cut + '…'
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = []
  for (const paragraph of String(text).split('\n')) {
    const tokens = tokenize(paragraph)
    let line = ''
    for (const token of tokens) {
      const candidate = line + token
      if (line && ctx.measureText(candidate.trimEnd()).width > maxWidth) {
        lines.push(line.trimEnd())
        line = token === ' ' ? '' : token
      } else {
        line = candidate
      }
    }
    lines.push(line.trimEnd())
  }
  return lines
}

// ── 纹理 ────────────────────────────────────────────────────

let grainCanvas: HTMLCanvasElement | null = null

/** 生成一张噪点贴图，用 pattern 平铺出胶片颗粒感 */
function getGrainCanvas(): HTMLCanvasElement {
  if (grainCanvas) return grainCanvas
  const size = 160
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const data = ctx.createImageData(size, size)
  for (let i = 0; i < data.data.length; i += 4) {
    const value = 118 + Math.random() * 74
    data.data[i] = value
    data.data[i + 1] = value
    data.data[i + 2] = value
    data.data[i + 3] = 255
  }
  ctx.putImageData(data, 0, 0)
  grainCanvas = canvas
  return canvas
}

// ── 各图层绘制 ──────────────────────────────────────────────

function drawBackground(
  ctx: CanvasRenderingContext2D,
  template: PosterTemplate,
  W: number,
  H: number,
): void {
  const { bg, deep, fg } = template.palette
  const { gradient, texture, textureOpacity = 0.05 } = template.background

  if (!gradient || gradient === 'none') {
    ctx.fillStyle = bg
  } else {
    // up：底部是底色，向上压暗；down：顶部是底色，向下压暗
    const g = ctx.createLinearGradient(0, gradient === 'up' ? H : 0, 0, gradient === 'up' ? 0 : H)
    g.addColorStop(0, bg)
    g.addColorStop(1, deep)
    ctx.fillStyle = g
  }
  ctx.fillRect(0, 0, W, H)

  if (!texture || texture === 'none') return
  ctx.save()
  ctx.globalAlpha = textureOpacity
  if (texture === 'grain') {
    const pattern = ctx.createPattern(getGrainCanvas(), 'repeat')
    if (pattern) {
      ctx.globalCompositeOperation = 'overlay'
      ctx.fillStyle = pattern
      ctx.fillRect(0, 0, W, H)
    }
  } else {
    ctx.strokeStyle = fg
    ctx.lineWidth = Math.max(1, W * 0.0008)
    const step = W / 16
    ctx.beginPath()
    for (let x = 0; x <= W; x += step) {
      ctx.moveTo(x, 0)
      ctx.lineTo(x, H)
    }
    for (let y = 0; y <= H; y += step) {
      ctx.moveTo(0, y)
      ctx.lineTo(W, y)
    }
    ctx.stroke()
  }
  ctx.restore()
}

function drawShape(
  ctx: CanvasRenderingContext2D,
  layer: Extract<PosterLayer, { kind: 'shape' }>,
  W: number,
  H: number,
  palette: Palette,
): void {
  const { x, y, w, h } = layer.frame
  const px = x * W
  const py = y * H
  const pw = w * W
  const ph = h * H

  ctx.save()
  ctx.globalAlpha = layer.opacity ?? 1

  if (layer.shape === 'line') {
    ctx.fillStyle = resolveColor(layer.fill, palette)
    ctx.fillRect(px, py, pw, Math.max(1, ph))
  } else if (layer.shape === 'circle') {
    ctx.fillStyle = resolveColor(layer.fill, palette)
    ctx.beginPath()
    ctx.ellipse(px + pw / 2, py + ph / 2, pw / 2, ph / 2, 0, 0, Math.PI * 2)
    ctx.fill()
  } else {
    ctx.beginPath()
    const radius = (layer.radius ?? 0) * W
    if (radius > 0 && typeof ctx.roundRect === 'function') ctx.roundRect(px, py, pw, ph, radius)
    else ctx.rect(px, py, pw, ph)

    if (layer.fill && layer.fill !== 'none') {
      ctx.fillStyle = resolveColor(layer.fill, palette)
      ctx.fill()
    }
    if (layer.stroke && layer.stroke !== 'none') {
      ctx.strokeStyle = resolveColor(layer.stroke, palette)
      ctx.lineWidth = Math.max(1, ((layer.strokeWidth ?? 0.16) / 100) * W)
      ctx.stroke()
    }
  }
  ctx.restore()
}

function resolveText(
  layer: Extract<PosterLayer, { kind: 'text' }>,
  data: PosterData,
): string {
  switch (layer.source) {
    case 'name':
      return data.name || '商品名称'
    case 'feature':
      return data.feature || ''
    case 'vibe':
      return data.vibe || ''
    case 'styleName':
      return data.styleName
    case 'styleEn':
      return data.styleEn
    default:
      return layer.text ?? ''
  }
}

function drawText(
  ctx: CanvasRenderingContext2D,
  layer: Extract<PosterLayer, { kind: 'text' }>,
  data: PosterData,
  W: number,
  H: number,
  palette: Palette,
): void {
  const raw = resolveText(layer, data)
  if (!raw || !raw.trim()) return
  const content = layer.upper ? raw.toUpperCase() : raw

  const fontSize = (layer.size / 100) * W
  const family = FONT_STACKS[layer.font ?? 'body']
  const weight = layer.weight ?? 400

  ctx.save()
  ctx.font = `${weight} ${fontSize}px ${family}`
  // letterSpacing 是较新的 canvas 能力，不支持时退化为无字距，不会报错
  if ('letterSpacing' in ctx) {
    (ctx as unknown as { letterSpacing: string }).letterSpacing = `${(layer.tracking ?? 0) * fontSize}px`
  }
  ctx.fillStyle = resolveColor(layer.color, palette)
  ctx.textBaseline = 'top'
  ctx.globalAlpha = layer.opacity ?? 1

  const boxX = layer.frame.x * W
  const boxY = layer.frame.y * H
  const boxW = layer.frame.w * W
  const lineHeight = (layer.lineHeight ?? 1.3) * fontSize
  const align = layer.align ?? 'left'
  const maxLines = layer.clamp ?? 99

  let lines = wrapText(ctx, content, boxW)
  if (lines.length > maxLines) {
    lines = lines.slice(0, maxLines)
    lines[maxLines - 1] = clipWithEllipsis(ctx, lines[maxLines - 1], boxW)
  }

  lines.forEach((line, index) => {
    let dx = boxX
    if (align === 'center') dx = boxX + (boxW - ctx.measureText(line).width) / 2
    else if (align === 'right') dx = boxX + boxW - ctx.measureText(line).width
    ctx.fillText(line, dx, boxY + index * lineHeight)
  })
  ctx.restore()
}

function drawPlaceholder(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  palette: Palette,
): void {
  ctx.save()
  ctx.globalAlpha = 0.25
  ctx.strokeStyle = palette.fg
  ctx.lineWidth = Math.max(1, w * 0.004)
  ctx.setLineDash([w * 0.03, w * 0.02])
  ctx.strokeRect(x, y, w, h)
  ctx.restore()
}

function drawProduct(
  ctx: CanvasRenderingContext2D,
  layer: Extract<PosterLayer, { kind: 'product' }>,
  image: HTMLImageElement | null,
  W: number,
  H: number,
  palette: Palette,
): void {
  const px = layer.frame.x * W
  const py = layer.frame.y * H
  const pw = layer.frame.w * W
  const ph = layer.frame.h * H

  if (!image || !image.width || !image.height) {
    drawPlaceholder(ctx, px, py, pw, ph, palette)
    return
  }

  // contain：等比缩放塞进框内，绝不裁切——抠图商品的完整性优先
  const scale = Math.min(pw / image.width, ph / image.height)
  const dw = image.width * scale
  const dh = image.height * scale
  const dx = px + (pw - dw) / 2
  const dy = py + (ph - dh) / 2

  if (layer.ground) {
    ctx.save()
    ctx.globalAlpha = 0.18
    ctx.fillStyle = '#000'
    ctx.beginPath()
    ctx.ellipse(dx + dw / 2, dy + dh * 0.98, dw * 0.32, dh * 0.035, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }

  ctx.save()
  if (layer.shadow) {
    // 阴影按图的 alpha 剪影生成，抠图的边缘会自然跟着走
    ctx.shadowColor = 'rgba(0, 0, 0, 0.26)'
    ctx.shadowBlur = layer.shadow * W
    ctx.shadowOffsetY = layer.shadow * W * 0.42
  }
  ctx.drawImage(image, dx, dy, dw, dh)
  ctx.restore()
}

// ── 资源准备 ────────────────────────────────────────────────

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    const isSameOrigin =
      url.startsWith('/') || url.startsWith('blob:') || url.startsWith(location.origin)
    if (!isSameOrigin) image.crossOrigin = 'anonymous'
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error(`图片加载失败：${url}`))
    image.src = url
  })
}

/** 必须等字体真正可用再画，否则中文会先落到兜底字体上、排版全错 */
async function ensureFonts(template: PosterTemplate, W: number): Promise<void> {
  const fonts = (document as unknown as { fonts?: FontFaceSet }).fonts
  if (!fonts?.load) return
  const specs = new Set<string>()
  for (const layer of template.layers) {
    if (layer.kind !== 'text') continue
    const size = Math.max(8, Math.round((layer.size / 100) * W))
    const family = FONT_STACKS[layer.font ?? 'body']
    specs.add(`${layer.weight ?? 400} ${size}px ${family}`)
    // 字体源只提供 500 字重时，请求 400 会立刻返回空集，等于没等。
    // 显式把 500 也请求一次，避免正文先用系统字体排好再跳字体。
    specs.add(`500 ${size}px ${family}`)
  }
  try {
    await Promise.all([...specs].map((spec) => fonts.load(spec)))
  } catch {
    // 字体加载失败也要继续画，只是会落到兜底字体
  }
  try {
    await fonts.ready
  } catch {
    // 同上
  }
}

/**
 * 把模板 + 数据画到 canvas 上。
 * 调用方负责在 canvas 上通过 CSS 控制显示尺寸，这里只管分辨率。
 */
export async function renderPoster(
  canvas: HTMLCanvasElement,
  template: PosterTemplate,
  data: PosterData,
  options: RenderOptions = {},
): Promise<void> {
  const width = options.width ?? 900
  const pixelRatio = options.pixelRatio ?? 2
  const [ratioW, ratioH] = template.ratio
  const height = Math.round((width * ratioH) / ratioW)

  canvas.width = Math.round(width * pixelRatio)
  canvas.height = Math.round(height * pixelRatio)
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  ctx.clearRect(0, 0, width, height)

  const { palette } = template
  drawBackground(ctx, template, width, height)
  await ensureFonts(template, width)

  const needsImage = template.layers.some((layer) => layer.kind === 'product')
  const image = needsImage && data.imageUrl ? await loadImage(data.imageUrl).catch(() => null) : null

  for (const layer of template.layers) {
    if (layer.kind === 'shape') drawShape(ctx, layer, width, height, palette)
    else if (layer.kind === 'text') drawText(ctx, layer, data, width, height, palette)
    else drawProduct(ctx, layer, image, width, height, palette)
  }
}

/** 导出成 PNG Blob（按导出尺寸重新渲染一遍，保证清晰度） */
export async function exportPoster(
  template: PosterTemplate,
  data: PosterData,
  width = 1500,
): Promise<Blob | null> {
  const canvas = document.createElement('canvas')
  await renderPoster(canvas, template, data, { width, pixelRatio: 1 })
  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), 'image/png'))
}
