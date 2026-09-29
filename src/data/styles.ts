/**
 * 设计风格。
 *
 * 一个风格就是一组色板：bg 是海报底色，fg 是文字与主体色（保证与 bg 有对比），
 * accent 是装饰色（线条、色块、强调）。
 *
 * 关键约定：版式模板只引用「颜色角色」而不写死色值，
 * 所以同一套版式能套出 5 种风格，见 data/templates.ts。
 */

export type StyleKey = 'natural' | 'minimal' | 'retro' | 'festive' | 'tech'

export interface Style {
  key: StyleKey
  name: string
  en: string
  desc: string
  /** 海报底色 */
  bg: string
  /** 文字与主体色 */
  fg: string
  /** 装饰色 */
  accent: string
}

export const styles: Style[] = [
  { key: 'natural', name: '自然', en: 'Natural', desc: '清新、有机、贴近自然', bg: '#7b8a72', fg: '#f6f3ec', accent: '#b6c2a8' },
  { key: 'minimal', name: '极简', en: 'Minimal', desc: '留白、克制、干净', bg: '#efe9de', fg: '#2b2723', accent: '#b3a894' },
  { key: 'retro', name: '复古', en: 'Retro', desc: '怀旧、温暖、有年代感', bg: '#a87e52', fg: '#f8f2e6', accent: '#e0c393' },
  { key: 'festive', name: '节日', en: 'Festive', desc: '喜庆、热闹、有氛围', bg: '#c08b62', fg: '#fff8ee', accent: '#8f3f2e' },
  { key: 'tech', name: '科技', en: 'Tech', desc: '简洁、未来、理性', bg: '#4e5c46', fg: '#f2f5ee', accent: '#a9c396' },
]

export function findStyle(key: string | null): Style | null {
  return styles.find((s) => s.key === key) ?? null
}
