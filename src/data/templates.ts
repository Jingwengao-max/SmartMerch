/**
 * 版式模板。
 *
 * 设计要点：版式只引用「颜色角色」，不写死颜色——
 * 同一个版式套不同风格就得到不同配色的成品。
 * 所以 6 套版式 × 5 种风格 = 30 个可用模板，但只需要维护这 6 套版式。
 *
 * 坐标一律用 0~1 的相对值（相对画布宽高），字号是「画布宽度的百分比」，
 * 这样同一套模板在任何输出尺寸下都不会跑位。
 */
import { styles, type Style, type StyleKey } from './styles'
import { shade, withAlpha } from '@/utils/color'

/** 颜色角色 —— 版式里所有颜色都从这里取 */
export type ColorRole = 'bg' | 'fg' | 'accent' | 'soft' | 'deep' | 'none'

export interface Palette {
  bg: string
  fg: string
  accent: string
  /** fg 降透明度，用于次级文字 */
  soft: string
  /** bg 压暗，用于色块分区 */
  deep: string
}

/** 相对画布的位置与尺寸，取值 0~1 */
export interface Frame {
  x: number
  y: number
  w: number
  h: number
}

/** 文案来源：从用户填写的内容里取，fixed 则用模板自带的 text */
export type TextSource = 'name' | 'feature' | 'styleName' | 'styleEn' | 'vibe' | 'fixed'

export type PosterLayer =
  | {
      kind: 'product'
      frame: Frame
      /** > 0 时给商品加投影（按剪影画，抠图边缘会自然跟形） */
      shadow?: number
      /** 底部加一个椭圆接地阴影 */
      ground?: boolean
    }
  | {
      kind: 'text'
      frame: Frame
      source: TextSource
      /** source 为 fixed 时使用 */
      text?: string
      /** 字号 = 画布宽度 × size% */
      size: number
      color: ColorRole
      font?: 'display' | 'body' | 'mono'
      weight?: number
      align?: 'left' | 'center' | 'right'
      /** 字距，单位 em */
      tracking?: number
      lineHeight?: number
      upper?: boolean
      opacity?: number
      /** 最多几行，超出省略 */
      clamp?: number
    }
  | {
      kind: 'shape'
      shape: 'rect' | 'line' | 'circle'
      frame: Frame
      fill?: ColorRole
      stroke?: ColorRole
      /** 线宽 = 画布宽度 × strokeWidth% */
      strokeWidth?: number
      radius?: number
      opacity?: number
    }

export interface Background {
  /** 渐变方向，none 为纯色 */
  gradient?: 'up' | 'down' | 'none'
  texture?: 'grain' | 'grid' | 'none'
  textureOpacity?: number
}

export interface PosterLayout {
  id: string
  name: string
  /** 画幅 [宽, 高] */
  ratio: [number, number]
  background: Background
  layers: PosterLayer[]
}

/** 解析后的完整模板：版式 + 具体色板 */
export interface PosterTemplate {
  id: string
  name: string
  ratio: [number, number]
  background: Background
  layers: PosterLayer[]
  palette: Palette
}

// ────────────────────────────────────────────────────────────
// 6 套版式
// ────────────────────────────────────────────────────────────

export const layouts: PosterLayout[] = [
  {
    id: 'centered',
    name: '居中留白',
    ratio: [3, 4],
    background: { gradient: 'down', texture: 'grain', textureOpacity: 0.05 },
    layers: [
      { kind: 'shape', shape: 'line', frame: { x: 0.38, y: 0.085, w: 0.24, h: 0.0025 }, fill: 'accent', opacity: 0.55 },
      { kind: 'text', frame: { x: 0.1, y: 0.103, w: 0.8, h: 0.04 }, source: 'styleEn', size: 3.1, color: 'accent', font: 'mono', tracking: 0.22, upper: true, align: 'center' },
      { kind: 'product', frame: { x: 0.12, y: 0.17, w: 0.76, h: 0.46 }, shadow: 0.035 },
      { kind: 'text', frame: { x: 0.08, y: 0.665, w: 0.84, h: 0.13 }, source: 'name', size: 9, color: 'fg', font: 'display', align: 'center', lineHeight: 1.25, clamp: 2 },
      { kind: 'text', frame: { x: 0.14, y: 0.805, w: 0.72, h: 0.1 }, source: 'feature', size: 3.3, color: 'soft', font: 'body', align: 'center', lineHeight: 1.7, clamp: 3 },
      { kind: 'shape', shape: 'line', frame: { x: 0.42, y: 0.93, w: 0.16, h: 0.0025 }, fill: 'accent', opacity: 0.45 },
    ],
  },
  {
    id: 'split',
    name: '上下分栏',
    ratio: [4, 5],
    background: { gradient: 'none', texture: 'none' },
    layers: [
      { kind: 'shape', shape: 'rect', frame: { x: 0, y: 0.6, w: 1, h: 0.4 }, fill: 'deep' },
      { kind: 'product', frame: { x: 0.16, y: 0.09, w: 0.68, h: 0.48 }, shadow: 0.03 },
      { kind: 'shape', shape: 'line', frame: { x: 0.1, y: 0.645, w: 0.8, h: 0.0015 }, fill: 'accent', opacity: 0.35 },
      { kind: 'text', frame: { x: 0.1, y: 0.665, w: 0.8, h: 0.035 }, source: 'styleEn', size: 2.9, color: 'accent', font: 'mono', tracking: 0.2, upper: true, align: 'left' },
      { kind: 'text', frame: { x: 0.1, y: 0.715, w: 0.8, h: 0.1 }, source: 'name', size: 8.2, color: 'fg', font: 'display', align: 'left', lineHeight: 1.2, clamp: 2 },
      { kind: 'text', frame: { x: 0.1, y: 0.835, w: 0.8, h: 0.09 }, source: 'feature', size: 3.1, color: 'soft', font: 'body', align: 'left', lineHeight: 1.6, clamp: 3 },
    ],
  },
  {
    id: 'frame',
    name: '内框',
    ratio: [3, 4],
    background: { gradient: 'none', texture: 'grid', textureOpacity: 0.05 },
    layers: [
      { kind: 'shape', shape: 'rect', frame: { x: 0.055, y: 0.04, w: 0.89, h: 0.92 }, fill: 'none', stroke: 'soft', strokeWidth: 0.16, opacity: 0.55 },
      { kind: 'product', frame: { x: 0.16, y: 0.12, w: 0.68, h: 0.52 }, shadow: 0.03 },
      { kind: 'text', frame: { x: 0.1, y: 0.675, w: 0.8, h: 0.035 }, source: 'styleEn', size: 3, color: 'accent', font: 'mono', tracking: 0.22, upper: true, align: 'center' },
      { kind: 'text', frame: { x: 0.12, y: 0.72, w: 0.76, h: 0.1 }, source: 'name', size: 8.5, color: 'fg', font: 'display', align: 'center', lineHeight: 1.2, clamp: 2 },
      { kind: 'text', frame: { x: 0.18, y: 0.835, w: 0.64, h: 0.07 }, source: 'feature', size: 3.1, color: 'soft', font: 'body', align: 'center', lineHeight: 1.6, clamp: 2 },
    ],
  },
  {
    id: 'editorial',
    name: '杂志左对齐',
    ratio: [3, 4],
    background: { gradient: 'down', texture: 'none' },
    layers: [
      { kind: 'text', frame: { x: 0.07, y: 0.045, w: 0.86, h: 0.11 }, source: 'styleName', size: 12.5, color: 'accent', font: 'display', align: 'left', opacity: 0.3, clamp: 1 },
      { kind: 'product', frame: { x: 0.2, y: 0.19, w: 0.66, h: 0.48 }, shadow: 0.03 },
      { kind: 'text', frame: { x: 0.08, y: 0.695, w: 0.84, h: 0.11 }, source: 'name', size: 8.6, color: 'fg', font: 'display', align: 'left', lineHeight: 1.2, clamp: 2 },
      { kind: 'shape', shape: 'line', frame: { x: 0.08, y: 0.835, w: 0.28, h: 0.0025 }, fill: 'accent' },
      { kind: 'text', frame: { x: 0.08, y: 0.86, w: 0.72, h: 0.07 }, source: 'feature', size: 3.1, color: 'soft', font: 'body', align: 'left', lineHeight: 1.6, clamp: 2 },
    ],
  },
  {
    id: 'square',
    name: '方形',
    ratio: [1, 1],
    background: { gradient: 'down', texture: 'grain', textureOpacity: 0.06 },
    layers: [
      { kind: 'product', frame: { x: 0.14, y: 0.1, w: 0.72, h: 0.56 }, shadow: 0.035 },
      { kind: 'text', frame: { x: 0.08, y: 0.7, w: 0.84, h: 0.11 }, source: 'name', size: 8.4, color: 'fg', font: 'display', align: 'center', lineHeight: 1.2, clamp: 2 },
      { kind: 'text', frame: { x: 0.08, y: 0.845, w: 0.84, h: 0.04 }, source: 'styleEn', size: 3, color: 'accent', font: 'mono', tracking: 0.24, upper: true, align: 'center' },
    ],
  },
  {
    id: 'banner',
    name: '大标题压图',
    ratio: [4, 5],
    background: { gradient: 'down', texture: 'none' },
    layers: [
      { kind: 'product', frame: { x: 0.07, y: 0.04, w: 0.86, h: 0.6 }, shadow: 0.03 },
      { kind: 'shape', shape: 'rect', frame: { x: 0.055, y: 0.585, w: 0.89, h: 0.33 }, fill: 'deep', radius: 0.015, opacity: 0.94 },
      { kind: 'text', frame: { x: 0.11, y: 0.625, w: 0.78, h: 0.11 }, source: 'name', size: 8.6, color: 'fg', font: 'display', align: 'left', lineHeight: 1.2, clamp: 2 },
      { kind: 'text', frame: { x: 0.11, y: 0.765, w: 0.78, h: 0.09 }, source: 'feature', size: 3.1, color: 'soft', font: 'body', align: 'left', lineHeight: 1.6, clamp: 2 },
      { kind: 'text', frame: { x: 0.11, y: 0.865, w: 0.78, h: 0.035 }, source: 'styleEn', size: 2.8, color: 'accent', font: 'mono', tracking: 0.2, upper: true, align: 'left' },
    ],
  },
]

// ────────────────────────────────────────────────────────────
// 版式 × 风格 → 可用模板
// ────────────────────────────────────────────────────────────

export function paletteOf(style: Style): Palette {
  return {
    bg: style.bg,
    fg: style.fg,
    accent: style.accent,
    soft: withAlpha(style.fg, 0.62),
    deep: shade(style.bg, -0.18),
  }
}

/** 取某个风格下的全部模板（每个版式一个） */
export function templatesForStyle(key: string | null): PosterTemplate[] {
  const style = styles.find((s) => s.key === key)
  if (!style) return []
  const palette = paletteOf(style)
  return layouts.map((layout) => ({
    id: `${style.key}-${layout.id}`,
    name: `${style.name} · ${layout.name}`,
    ratio: layout.ratio,
    background: layout.background,
    layers: layout.layers,
    palette,
  }))
}

/** 预览用：风格未选定前拿第一套版式兜底 */
export function fallbackTemplate(): PosterTemplate {
  return templatesForStyle(styles[0].key)[0]
}

export type { Style, StyleKey }
