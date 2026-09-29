import { reactive, ref, computed } from 'vue'
import { cutout, resolveAssetUrl } from '@/api/client'
import { styles, type Style } from '@/data/styles'
import { fallbackTemplate, templatesForStyle, type PosterTemplate } from '@/data/templates'
import { exportPoster, type PosterData } from '@/utils/renderPoster'

export { styles }
export type { Style }

export const steps = [
  { no: '01', key: 'upload', title: '上传商品', en: 'Upload' },
  { no: '02', key: 'info', title: '商品信息', en: 'Info' },
  { no: '03', key: 'style', title: '设计风格', en: 'Style' },
  { no: '04', key: 'generate', title: '生成作品', en: 'Generate' },
]

/** 每一步都对应真实发生的事，别写成做不到的承诺 */
export const genSteps = ['匹配版式', '套用配色', '排版文案', '渲染成图']

const state = reactive({
  image: null as string | null,
  /** 上传的原始图（本地 blob），抠图失败时回退用，也方便做前后对比 */
  originalImage: null as string | null,
  imageName: '',
  removing: false,
  bgRemoved: false,
  error: '',
  name: '',
  feature: '',
  vibe: '',
  style: null as string | null,
  generating: false,
  genStep: -1,
  generated: false,
  /** 生成结果：当前风格下的全部版式 */
  variants: [] as PosterTemplate[],
  activeVariant: 0,
  downloading: false,
})

const step = ref(0)

let timers: ReturnType<typeof setTimeout>[] = []
/** 抠图请求序号：连续换图时用来丢弃过期响应 */
let cutoutSeq = 0

function clearTimers() {
  timers.forEach((t) => clearTimeout(t))
  timers = []
}

const selectedStyle = computed<Style | null>(
  () => styles.find((s) => s.key === state.style) ?? null
)

/** 渲染用的数据：模板里的文案占位从这里取值 */
const posterData = computed<PosterData>(() => ({
  imageUrl: state.image,
  name: state.name,
  feature: state.feature,
  vibe: state.vibe,
  styleName: selectedStyle.value?.name ?? '',
  styleEn: selectedStyle.value?.en ?? '',
}))

/** 步骤 1/2 的实时预览：选了风格就用该风格的第一套版式 */
const previewTemplate = computed<PosterTemplate>(
  () => templatesForStyle(state.style)[0] ?? fallbackTemplate(),
)

const activeTemplate = computed<PosterTemplate | null>(
  () => state.variants[state.activeVariant] ?? null,
)

const canNext = computed(() => {
  switch (step.value) {
    case 0:
      return !!state.image && state.bgRemoved
    case 1:
      return state.name.trim().length > 0
    case 2:
      return !!state.style
    default:
      return false
  }
})

/**
 * 能否开始生成。
 * 注意别复用 canNext：它是「进入下一步」的闸门，在第 3 步恒为 false，
 * 早期版本的 startGenerate 用它做守卫，导致点「开始生成」直接静默 return。
 */
const canGenerate = computed(
  () =>
    !!state.image &&
    state.bgRemoved &&
    state.name.trim().length > 0 &&
    !!state.style,
)

/** 释放上一张原图的 blob URL，避免内存泄漏 */
function releaseOriginal() {
  const prev = state.originalImage
  if (prev && prev.startsWith('blob:')) URL.revokeObjectURL(prev)
  state.originalImage = null
}

/** 调后端抠图；seq 不匹配说明用户已经换了图，直接丢弃这次结果 */
async function runCutout(file: File, seq: number) {
  try {
    const result = await cutout(file)
    if (seq !== cutoutSeq) return
    state.image = resolveAssetUrl(result.url)
    state.bgRemoved = true
  } catch (err) {
    if (seq !== cutoutSeq) return
    state.error = err instanceof Error ? err.message : '抠图失败，请重试'
    state.bgRemoved = false
    // 失败时退回原图，用户仍可继续往下走
    state.image = state.originalImage
  } finally {
    if (seq === cutoutSeq) state.removing = false
  }
}

function setFile(file: File) {
  if (!file || !file.type.startsWith('image/')) return
  clearTimers()
  releaseOriginal()

  // 先本地显示原图，等后端抠完再替换成结果
  const localUrl = URL.createObjectURL(file)
  state.originalImage = localUrl
  state.image = localUrl
  state.imageName = file.name
  state.bgRemoved = false
  state.error = ''
  state.removing = true

  cutoutSeq += 1
  void runCutout(file, cutoutSeq)
}

function next() {
  if (canNext.value && step.value < 3) step.value++
}

function back() {
  if (step.value > 0) {
    clearTimers()
    state.generating = false
    state.genStep = -1
    step.value--
  }
}

function goTo(i: number) {
  if (i < 0 || i > step.value) return
  clearTimers()
  state.generating = false
  state.genStep = -1
  step.value = i
}

function selectStyle(key: string) {
  state.style = key
  // 风格换了，之前生成的方案作废
  state.variants = []
  state.generated = false
  state.activeVariant = 0
}

function selectVariant(index: number) {
  if (index < 0 || index >= state.variants.length) return
  state.activeVariant = index
}

function startGenerate() {
  if (state.generating || !canGenerate.value) return
  state.generating = true
  state.generated = false
  state.genStep = 0
  state.error = ''
  clearTimers()

  // 真正的生成是确定性的：取出该风格下的全部版式当作方案。
  // 动画只是给过程感，并保证结果不会在用户眼前"闪"一下才出来。
  state.variants = templatesForStyle(state.style)
  state.activeVariant = 0

  timers.push(setTimeout(() => (state.genStep = 1), 360))
  timers.push(setTimeout(() => (state.genStep = 2), 720))
  timers.push(setTimeout(() => (state.genStep = 3), 1080))
  timers.push(
    setTimeout(() => {
      state.generating = false
      state.generated = true
    }, 1400),
  )
}

/** 导出当前选中的方案：按导出尺寸重渲染一遍，保证清晰度 */
async function downloadActive() {
  const template = activeTemplate.value
  if (!template || state.downloading) return
  state.downloading = true
  state.error = ''
  try {
    const blob = await exportPoster(template, posterData.value, 1500)
    if (!blob) throw new Error('导出失败，请重试')
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${(state.name || '海报').trim()}-${template.id}.png`
    document.body.appendChild(link)
    link.click()
    link.remove()
    // 交给浏览器读完再释放
    setTimeout(() => URL.revokeObjectURL(url), 10000)
  } catch (err) {
    state.error = err instanceof Error ? err.message : '导出失败'
  } finally {
    state.downloading = false
  }
}

function reset() {
  clearTimers()
  // 让在途的抠图响应失效，避免回来后又把图放上画布
  cutoutSeq += 1
  releaseOriginal()
  Object.assign(state, {
    image: null,
    originalImage: null,
    imageName: '',
    removing: false,
    bgRemoved: false,
    error: '',
    name: '',
    feature: '',
    vibe: '',
    style: null,
    generating: false,
    genStep: -1,
    generated: false,
    variants: [],
    activeVariant: 0,
    downloading: false,
  })
  step.value = 0
}

export function useStudio() {
  return {
    steps,
    styles,
    genSteps,
    state,
    step,
    selectedStyle,
    posterData,
    previewTemplate,
    activeTemplate,
    canNext,
    canGenerate,
    setFile,
    next,
    back,
    goTo,
    selectStyle,
    selectVariant,
    startGenerate,
    downloadActive,
    reset,
  }
}
