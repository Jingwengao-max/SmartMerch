import { computed, reactive, ref } from 'vue'
import {
  assetUrl,
  cutoutProduct,
  generateCopy,
  generatePosters,
  refineCopy,
  type CopyFeedback,
  type CopySet,
  type CopyVariant,
  type PosterCandidate,
  type PosterDocument,
} from '@/services/posterApi'

export interface Style { key: string; name: string; en: string; desc: string; bg: string; fg: string }

export const steps = [
  { no: '01', key: 'upload', title: '上传商品', en: 'Upload' },
  { no: '02', key: 'info', title: '商品信息', en: 'Info' },
  { no: '03', key: 'style', title: '设计风格', en: 'Style' },
  { no: '04', key: 'generate', title: '生成作品', en: 'Generate' },
]

export const styles: Style[] = [
  { key: 'natural', name: '自然', en: 'Natural', desc: '清新、有机、贴近自然', bg: '#7b8a72', fg: '#f6f3ec' },
  { key: 'minimal', name: '极简', en: 'Minimal', desc: '留白、克制、干净', bg: '#efe9de', fg: '#2b2723' },
  { key: 'retro', name: '复古', en: 'Retro', desc: '怀旧、温暖、有年代感', bg: '#a87e52', fg: '#f6f3ec' },
  { key: 'festive', name: '节日', en: 'Festive', desc: '喜庆、热闹、有氛围', bg: '#c08b62', fg: '#fff8ee' },
  { key: 'tech', name: '科技', en: 'Tech', desc: '简洁、未来、理性', bg: '#4e5c46', fg: '#f6f3ec' },
]

export const genSteps = ['识别商品主体', '寻找视觉方向', '生成场景', '完成排版']

const state = reactive({
  sourceFile: null as File | null,
  image: null as string | null,
  imageName: '',
  cutoutUrl: '',
  jobId: '',
  removing: false,
  bgRemoved: false,
  analyzing: false,
  name: '',
  feature: '',
  vibe: '',
  style: null as string | null,
  copyVariants: [] as CopyVariant[],
  copySource: '' as string,
  price: '',
  promo: '',
  sellingPoints: [] as string[],
  aiWarning: '',
  generating: false,
  genStep: -1,
  generated: false,
  candidates: [] as PosterCandidate[],
  skippedTemplates: [] as { templateId: string; reason: string }[],
  editorDocument: null as PosterDocument | null,
  selectedCandidateIndex: 0,
  error: '',
})

const step = ref(0)
const selectedStyle = computed<Style | null>(() => styles.find((item) => item.key === state.style) ?? null)
const selectedCandidate = computed<PosterCandidate | null>(() => state.candidates[state.selectedCandidateIndex] ?? null)
const canNext = computed(() => {
  if (step.value === 0) return !!state.sourceFile && state.bgRemoved && !state.removing
  if (step.value === 1) return state.name.trim().length > 0
  if (step.value === 2) return !!state.style
  return false
})

/** 等浏览器真的能把图解码出来再切换 src，避免中间出现空白。 */
function preloadImage(url: string) {
  return new Promise<void>((resolve) => {
    const image = new Image()
    image.onload = () => resolve()
    image.onerror = () => resolve()
    image.src = url
  })
}

async function setFile(file: File) {
  if (!file?.type.startsWith('image/')) return
  if (state.image?.startsWith('blob:')) URL.revokeObjectURL(state.image)
  Object.assign(state, {
    sourceFile: file,
    image: URL.createObjectURL(file),
    imageName: file.name,
    cutoutUrl: '',
    bgRemoved: false,
    removing: true,
    analyzing: false,
    generated: false,
    candidates: [],
    copyVariants: [],
    copySource: '',
    error: '',
    aiWarning: '',
  })

  const cutoutTask = cutoutProduct(file)
    .then(async (result) => {
      state.jobId = result.jobId
      const url = assetUrl(result.cutoutUrl)
      state.cutoutUrl = url
      await preloadImage(url)
      state.image = url
      state.bgRemoved = true
      return result.jobId
    })
    .catch((error: Error) => {
      state.error = error.message
      state.bgRemoved = false
      return ''
    })
    .finally(() => (state.removing = false))

  // 抠图完成后立刻基于图片出一版文案，用户再逐条提修改意见。
  const copyTask = cutoutTask.then(async (jobId) => {
    if (!jobId) return
    state.analyzing = true
    try {
      applyCopySet(await generateCopy({ jobId }))
    } catch (error) {
      state.error = error instanceof Error ? error.message : '文案生成失败。'
    } finally {
      state.analyzing = false
    }
  })

  await Promise.allSettled([cutoutTask, copyTask])
}

function next() { if (canNext.value && step.value < 3) step.value++ }
function back() { if (step.value > 0 && !state.generating) step.value-- }
function goTo(index: number) { if (index >= 0 && index <= step.value && !state.generating) step.value = index }
function selectStyle(key: string) { state.style = key }

function applyCopySet(result: CopySet) {
  state.copyVariants = result.variants ?? []
  state.copySource = result.source
  const identification = result.identification
  if (!state.name && identification?.category && identification.category !== '待人工确认的商品') {
    state.name = identification.category
  }
  if (!state.feature && identification?.visible_features?.length) {
    state.feature = identification.visible_features.join('，')
  }
  state.aiWarning = identification?.warning || ''
}

/** 用户填完名称/特点/卖点/价格/活动之后，结合抠图生成按块拆好的文案。 */
async function generateCopySuggestions() {
  if (state.analyzing) return
  if (!state.jobId) {
    state.error = '图片还没处理完，请等抠图完成后再生成文案。'
    return
  }
  state.analyzing = true
  state.error = ''
  try {
    applyCopySet(await generateCopy({
      jobId: state.jobId,
      name: state.name,
      feature: state.feature,
      sellingPoints: state.sellingPoints,
      vibe: state.vibe,
      style: state.style ?? '',
      price: state.price,
      promo: state.promo,
    }))
  } catch (error) {
    state.error = error instanceof Error ? error.message : '文案生成失败。'
  } finally {
    state.analyzing = false
  }
}

/** 针对某一组文案逐条提意见后改写；只替换这一组，其他方案不动。 */
async function refineVariant(index: number, feedback: CopyFeedback) {
  const target = state.copyVariants[index]
  if (!target || state.analyzing) return
  if (!state.jobId) {
    state.error = '图片还没处理完，请稍后再试。'
    return
  }
  state.analyzing = true
  state.error = ''
  try {
    const result = await refineCopy({
      jobId: state.jobId,
      current: target,
      feedback,
      context: {
        name: state.name,
        feature: state.feature,
        sellingPoints: state.sellingPoints,
        vibe: state.vibe,
        style: state.style ?? '',
        price: state.price,
        promo: state.promo,
      },
    })
    const refined = result.variants[0]
    if (refined) state.copyVariants[index] = refined
    if (result.identification?.warning) state.aiWarning = result.identification.warning
  } catch (error) {
    state.error = error instanceof Error ? error.message : '按意见修改失败，请稍后重试。'
  } finally {
    state.analyzing = false
  }
}

function applyCopywriting(variant: CopyVariant) {
  if (variant.title) state.name = variant.title
  if (variant.subtitle) state.feature = variant.subtitle
  state.price = variant.price_text
  state.promo = variant.promo_text
  state.sellingPoints = [...variant.selling_points]
}

function selectCandidate(index: number) {
  if (index >= 0 && index < state.candidates.length) {
    state.selectedCandidateIndex = index
    state.editorDocument = JSON.parse(JSON.stringify(state.candidates[index])) as PosterDocument
  }
}
function updateEditorDocument(document: PosterDocument) { state.editorDocument = document }

async function startGenerate() {
  if (state.generating || !state.sourceFile || !state.style) return
  state.generating = true
  state.generated = false
  state.genStep = 0
  state.error = ''
  const progress = window.setInterval(() => {
    if (state.genStep < genSteps.length - 1) state.genStep++
  }, 900)
  try {
    const result = await generatePosters({
      image: state.sourceFile,
      name: state.name,
      feature: state.feature,
      vibe: state.vibe,
      style: state.style,
      price: state.price,
      promo: state.promo,
      sellingPoints: state.sellingPoints,
    })
    state.jobId = result.jobId
    state.candidates = result.candidates.map((item) => ({ ...item, previewUrl: assetUrl(item.previewUrl) }))
    state.skippedTemplates = result.skippedTemplates ?? []
    state.selectedCandidateIndex = 0
    state.editorDocument = state.candidates[0]
      ? JSON.parse(JSON.stringify(state.candidates[0])) as PosterDocument
      : null
    state.generated = true
    state.genStep = genSteps.length - 1
  } catch (error) {
    state.error = error instanceof Error ? error.message : '生成失败，请稍后重试。'
  } finally {
    window.clearInterval(progress)
    state.generating = false
  }
}

function reset() {
  if (state.image?.startsWith('blob:')) URL.revokeObjectURL(state.image)
  Object.assign(state, {
    sourceFile: null, image: null, imageName: '', cutoutUrl: '', jobId: '', removing: false,
    bgRemoved: false, analyzing: false, name: '', feature: '', vibe: '', style: null,
    copyVariants: [], copySource: '', price: '', promo: '', sellingPoints: [],
    aiWarning: '', generating: false, genStep: -1, generated: false,
    candidates: [], skippedTemplates: [], editorDocument: null, selectedCandidateIndex: 0, error: '',
  })
  step.value = 0
}

export function useStudio() {
  return {
    steps, styles, genSteps, state, step, selectedStyle, selectedCandidate, canNext,
    setFile, next, back, goTo, selectStyle, applyCopywriting, generateCopySuggestions, selectCandidate,
    updateEditorDocument, startGenerate, reset, refineVariant,
  }
}
