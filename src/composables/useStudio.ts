import { computed, reactive, ref } from 'vue'
import {
  assetUrl,
  cutoutProduct,
  fetchStyleSpecs,
  generateCopy,
  generatePosters,
  refineCopy,
  translateProductName,
  type CopyFeedback,
  type CopyVariant,
  type PosterCandidate,
  type PosterDocument,
  type StyleField,
  type StyleSpec,
} from '@/services/posterApi'

export const steps = [
  { no: '01', key: 'upload', title: '上传商品', en: 'Upload' },
  { no: '02', key: 'style', title: '设计风格', en: 'Style' },
  { no: '03', key: 'copy', title: '确认文案', en: 'Copy' },
  { no: '04', key: 'generate', title: '生成作品', en: 'Generate' },
]

export interface Style {
  key: string
  name: string
  en: string
  desc: string
  /** 目前只有学习版式可用，其余风格尚未导入。 */
  available: boolean
  bg: string
  fg: string
}

export const styles: Style[] = [
  {
    key: 'editorial', name: '杂志', en: 'Editorial',
    desc: '暖纸底色、超大标题与手作感装饰',
    available: true, bg: '#faf5ed', fg: '#2b2723',
  },
  { key: 'natural', name: '自然', en: 'Natural', desc: '清新、有机、贴近自然', available: false, bg: '#7b8a72', fg: '#f6f3ec' },
  {
    key: 'style2', name: '简约', en: 'Simple',
    desc: '清晰留白、重点突出、信息层级简洁',
    available: true, bg: '#f5f5f5', fg: '#2b2723',
  },
  {
    key: 'retro', name: '复古', en: 'Retro',
    desc: '复古杂志排版、斜切构图与商品轮廓纹样',
    available: true, bg: '#f7f0df', fg: '#6f2416',
  },
  { key: 'festive', name: '节日', en: 'Festive', desc: '喜庆、热闹、有氛围', available: false, bg: '#c08b62', fg: '#fff8ee' },
  { key: 'tech', name: '科技', en: 'Tech', desc: '简洁、未来、理性', available: false, bg: '#4e5c46', fg: '#f6f3ec' },
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
  translating: false,
  refiningIndex: -1,
  style: null as string | null,
  styleSpecs: {} as Record<string, StyleSpec>,
  fields: [] as StyleField[],
  copy: {} as CopyVariant,
  copyByStyle: {} as Record<string, CopyVariant>,
  copywriting: [] as CopyVariant[],
  aiWarning: '',
  generating: false,
  genStep: -1,
  generated: false,
  candidates: [] as PosterCandidate[],
  editorDocument: null as PosterDocument | null,
  selectedCandidateIndex: 0,
  error: '',
})

const step = ref(0)
const selectedStyle = computed<Style | null>(() => styles.find((item) => item.key === state.style) ?? null)
const hasCopy = computed(() => Object.values(state.copy).some((value) => (
  Array.isArray(value) ? value.some((item) => item.trim()) : String(value ?? '').trim()
)))
const previewTitle = computed(() => {
  const source = state.copy.title || state.copy.name || state.copy.subtitle || ''
  return String(source)
})
const selectedCandidate = computed<PosterCandidate | null>(() => state.candidates[state.selectedCandidateIndex] ?? null)
const canNext = computed(() => {
  if (step.value === 0) return !!state.sourceFile && state.bgRemoved && !state.removing
  if (step.value === 1) return !!selectedStyle.value
  if (step.value === 2) return hasCopy.value
  return false
})

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
    refiningIndex: -1,
    copywriting: [],
    generated: false,
    candidates: [],
    error: '',
    aiWarning: '',
  })

  const cutoutTask = cutoutProduct(file)
    .then(async (result) => {
      state.jobId = result.jobId
      state.cutoutUrl = assetUrl(result.cutoutUrl)
      state.image = state.cutoutUrl
      state.bgRemoved = true
    })
    .catch((error: Error) => {
      state.error = error.message
      state.bgRemoved = false
    })
    .finally(() => (state.removing = false))

  await cutoutTask
}

function next() { if (canNext.value && step.value < 3) step.value++ }
function back() { if (step.value > 0 && !state.generating) step.value-- }
function goTo(index: number) { if (index >= 0 && index <= step.value && !state.generating) step.value = index }

let specsLoaded = false
async function loadStyleSpecs() {
  if (specsLoaded) return
  specsLoaded = true
  try {
    state.styleSpecs = await fetchStyleSpecs()
  } catch {
    specsLoaded = false
  }
}

function selectStyle(key: string) {
  const target = styles.find((item) => item.key === key)
  if (!target?.available) return
  if (state.style && state.style !== key) {
    state.copyByStyle[state.style] = { ...state.copy }
  }
  state.style = key
  state.fields = state.styleSpecs[key]?.fields ?? []
  state.copy = { ...(state.copyByStyle[key] ?? {}) }
  state.copywriting = []
  state.aiWarning = ''
}

function textValue(key: string): string {
  const value = state.copy[key]
  return typeof value === 'string' ? value : ''
}

function setText(key: string, value: string) {
  state.copy[key] = value
}

function listValue(key: string, index: number): string {
  const value = state.copy[key]
  return Array.isArray(value) ? value[index] ?? '' : ''
}

function setList(key: string, index: number, value: string) {
  const current = state.copy[key]
  const list = Array.isArray(current) ? [...current] : []
  while (list.length <= index) list.push('')
  list[index] = value
  state.copy[key] = list
}

function applyCopywriting(option: CopyVariant) {
  const next: CopyVariant = { ...state.copy }
  for (const [key, value] of Object.entries(option)) {
    next[key] = Array.isArray(value) ? [...value] : String(value)
  }
  state.copy = next
}

async function generateCopySuggestions() {
  if (!state.jobId || state.analyzing || !state.style) return
  state.analyzing = true
  state.error = ''
  try {
    const result = await generateCopy({
      jobId: state.jobId,
      style: state.style,
      context: { ...state.copy },
    })
    state.copywriting = result.copywriting
    state.aiWarning = result.warning
  } catch (error) {
    state.aiWarning = error instanceof Error ? error.message : '文案生成失败。'
  } finally {
    state.analyzing = false
  }
}

async function translateName() {
  const chineseName = String(state.copy.subtitle || '').trim()
  if (!chineseName || state.translating) return
  state.translating = true
  state.aiWarning = ''
  try {
    state.copy.title = await translateProductName(chineseName)
  } catch (error) {
    state.aiWarning = error instanceof Error ? error.message : '英文名生成失败，请稍后重试。'
  } finally {
    state.translating = false
  }
}

async function refineCopywriting(index: number, feedback: CopyFeedback) {
  const current = state.copywriting[index]
  const hasFeedback = Object.values(feedback).some((value) => (
    Array.isArray(value) ? value.some((item) => item.trim()) : String(value ?? '').trim()
  ))
  if (!current || !hasFeedback || state.refiningIndex >= 0 || !state.style) return
  state.refiningIndex = index
  state.error = ''
  try {
    const result = await refineCopy({
      jobId: state.jobId, style: state.style, current, feedback,
    })
    const refined = result.copywriting[0]
    if (refined) state.copywriting[index] = refined
    state.aiWarning = result.warning
  } catch (error) {
    state.error = error instanceof Error ? error.message : '按意见修改失败。'
  } finally {
    state.refiningIndex = -1
  }
}
function selectCandidate(index: number) {
  if (index >= 0 && index < state.candidates.length) {
    state.selectedCandidateIndex = index
    state.editorDocument = JSON.parse(JSON.stringify(state.candidates[index])) as PosterDocument
  }
}
function updateEditorDocument(document: PosterDocument) { state.editorDocument = document }

async function startGenerate() {
  if (state.generating || !state.sourceFile || !state.style || !hasCopy.value) return
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
      style: state.style,
      copy: { ...state.copy },
    })
    state.jobId = result.jobId
    state.candidates = result.candidates.map((item) => ({ ...item, previewUrl: assetUrl(item.previewUrl) }))
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
    bgRemoved: false, analyzing: false, translating: false, refiningIndex: -1,
    style: null, fields: [], copy: {}, copyByStyle: {}, copywriting: [],
    aiWarning: '', generating: false, genStep: -1, generated: false,
    candidates: [], editorDocument: null, selectedCandidateIndex: 0, error: '',
  })
  step.value = 0
  loadStyleSpecs()
}

export function useStudio() {
  return {
    steps, genSteps, state, step, selectedCandidate, canNext, previewTitle, hasCopy,
    styles, selectedStyle, selectStyle,
    setFile, next, back, goTo, applyCopywriting, generateCopySuggestions, translateName,
    refineCopywriting, selectCandidate, textValue, setText, listValue, setList,
    updateEditorDocument, startGenerate, reset,
  }
}
