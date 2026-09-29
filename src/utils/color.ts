/** 颜色小工具：只处理 #RGB / #RRGGBB，够用且无依赖。 */

function parseHex(hex: string): [number, number, number] {
  let text = String(hex).trim().replace(/^#/, '')
  if (text.length === 3) text = text.split('').map((c) => c + c).join('')
  const value = Number.parseInt(text.slice(0, 6), 16)
  if (!Number.isFinite(value)) return [0, 0, 0]
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

function toHex(rgb: [number, number, number]): string {
  return '#' + rgb.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('')
}

/** 加透明度，返回 rgba() */
export function withAlpha(hex: string, alpha: number): string {
  const [r, g, b] = parseHex(hex)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/** amount > 0 提亮，< 0 压暗（-1 ~ 1） */
export function shade(hex: string, amount: number): string {
  const rgb = parseHex(hex)
  const target = amount < 0 ? 0 : 255
  const ratio = Math.abs(amount)
  return toHex(rgb.map((v) => v + (target - v) * ratio) as [number, number, number])
}

