export interface FontOption {
  id: string
  label: string
  description: string
  category: 'handwriting' | 'sans' | 'serif' | 'editorial' | 'display' | 'calligraphy'
  stack: string
}

export const FONT_OPTIONS: FontOption[] = [
  {
    id: 'wenkai',
    label: '霞鹜文楷',
    description: '亲和、人文，适合食品与生活方式品牌',
    category: 'handwriting',
    stack: '"LXGW WenKai", "Noto Sans SC", serif',
  },
  {
    id: 'sans',
    label: '思源黑体',
    description: '清晰、现代，适合信息型海报与正文',
    category: 'sans',
    stack: '"Noto Sans SC", "Microsoft YaHei", sans-serif',
  },
  {
    id: 'serif',
    label: '思源宋体',
    description: '克制、正式，适合杂志感和精品商品',
    category: 'serif',
    stack: '"Noto Serif SC", "Songti SC", serif',
  },
  {
    id: 'xiaowei',
    label: '站酷小薇',
    description: '纤细、有编辑感的标题字体',
    category: 'editorial',
    stack: '"ZCOOL XiaoWei", "Noto Serif SC", serif',
  },
  {
    id: 'kuaile',
    label: '站酷快乐体',
    description: '轻松、活泼，适合零食、活动与节日海报',
    category: 'display',
    stack: '"ZCOOL KuaiLe", "Noto Sans SC", sans-serif',
  },
  {
    id: 'qingke',
    label: '站酷庆科黄油体',
    description: '厚重、复古，适合大标题和促销信息',
    category: 'display',
    stack: '"ZCOOL QingKe HuangYou", "Noto Sans SC", sans-serif',
  },
  {
    id: 'brush',
    label: '马善政毛笔楷书',
    description: '毛笔书写感，适合东方、传统与节庆主题',
    category: 'calligraphy',
    stack: '"Ma Shan Zheng", "STKaiti", serif',
  },
  {
    id: 'hand',
    label: '龙藏体',
    description: '随性手写感，适合个性化短标题',
    category: 'handwriting',
    stack: '"Long Cang", "LXGW WenKai", serif',
  },
]

const FONT_ALIASES: Record<string, string> = {
  hei: 'sans',
}

export function resolveFontId(fontFamily?: string) {
  const candidate = fontFamily || 'wenkai'
  if (FONT_OPTIONS.some((font) => font.id === candidate)) return candidate
  return FONT_ALIASES[candidate] ?? 'wenkai'
}

export function fontStack(fontFamily?: string) {
  const fontId = resolveFontId(fontFamily)
  return FONT_OPTIONS.find((font) => font.id === fontId)?.stack ?? FONT_OPTIONS[0].stack
}
