export interface Work {
  id: number
  title: string
  en: string
  style: string
  bg: string // 海报底色
  fg: string // 海报文字/图形色
  shape: 'jar' | 'bottle' | 'cup' | 'box' | 'tube'
  ratio: string // 画幅比例，制造不规则节奏
  caption: string
}

/** 精选作品（示例数据，后续可替换为真实生成结果） */
export const works: Work[] = [
  {
    id: 1,
    title: '手工陶瓷',
    en: 'Handcrafted',
    style: '自然',
    bg: '#7b8a72',
    fg: '#f6f3ec',
    shape: 'jar',
    ratio: '3 / 4',
    caption: '手工陶瓷 · 自然风',
  },
  {
    id: 2,
    title: '冷萃咖啡',
    en: 'Cold Brew',
    style: '极简',
    bg: '#efe9de',
    fg: '#2b2723',
    shape: 'bottle',
    ratio: '4 / 5',
    caption: '冷萃咖啡 · 极简风',
  },
  {
    id: 3,
    title: '复古香皂',
    en: 'Vintage Soap',
    style: '复古',
    bg: '#a87e52',
    fg: '#f6f3ec',
    shape: 'box',
    ratio: '3 / 4',
    caption: '复古香皂 · 复古风',
  },
  {
    id: 4,
    title: '新春礼盒',
    en: 'Gift Box',
    style: '节日',
    bg: '#c08b62',
    fg: '#fff8ee',
    shape: 'box',
    ratio: '1 / 1',
    caption: '新春礼盒 · 节日风',
  },
  {
    id: 5,
    title: '极简水杯',
    en: 'Minimal Cup',
    style: '极简',
    bg: '#d6cec0',
    fg: '#2b2723',
    shape: 'cup',
    ratio: '4 / 5',
    caption: '极简水杯 · 极简风',
  },
  {
    id: 6,
    title: '植萃精华',
    en: 'Botanical',
    style: '科技',
    bg: '#4e5c46',
    fg: '#f6f3ec',
    shape: 'tube',
    ratio: '3 / 4',
    caption: '植萃精华 · 科技风',
  },
]
