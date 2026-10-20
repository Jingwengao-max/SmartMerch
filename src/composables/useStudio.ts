import { computed, reactive, ref } from 'vue'
import {
  assetUrl,
  cutoutProduct,
  generateCopy,
  generatePosters,
  refineCopy,
  translateProductName,
  type CopyFeedback,
  type CopywritingOption,
  type PosterCandidate,
  type PosterDocument,
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
    key: 'editorial', name: '杂志编辑', en: 'Editorial',
    desc: '暖纸底色、超大标题、手作感装饰（当前学习版式）',
    available: true, bg: '#faf5ed', fg: '#2b2723',
  },
  { key: 'natural', name: '自然', en: 'Natural', desc: '清新、有机、贴近自然', available: false, bg: '#7b8a72', fg: '#f6f3ec' },
  { key: 'minimal', name: '极简', en: 'Minimal', desc: '留白、克制、干净', available: false, bg: '#efe9de', fg: '#2b2723' },
  { key: 'retro', name: '复古', en: 'Retro', desc: '怀旧、温暖、有年代感', available: false, bg: '#a87e52', fg: '#f6f3ec' },
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
  name: '',
  feature: '',
  sellingPoints: ['', '', ''] as string[],
  footer: '',
  launchText: '新品上市',
  badgeText: 'NEW!',
  copywriting: [] as CopywritingOption[],
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
const selectedCandidate = computed<PosterCandidate | null>(() => state.candidates[state.selectedCandidateIndex] ?? null)
const canNext = computed(() => {
  if (step.value === 0) return !!state.sourceFile && state.bgRemoved && !state.removing
  if (step.value === 1) return !!selectedStyle.value
  if (step.value === 2) return state.name.trim().length > 0 && state.feature.trim().length > 0
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
function selectStyle(key: string) {
  const target = styles.find((item) => item.key === key)
  if (target?.available) state.style = key
}
function applyCopywriting(option: CopywritingOption) {
  // 一键应用：整组覆盖，避免上一组的卖点残留。
  if (option.subtitle) state.feature = option.subtitle
  state.sellingPoints = [...(option.sellingPoints ?? []).slice(0, 3), '', ''].slice(0, 3)
  if (option.footer) state.footer = option.footer
  if (option.launchText) state.launchText = option.launchText
  if (option.badgeText) state.badgeText = option.badgeText
}

async function generateCopySuggestions() {
  if (!state.jobId || state.analyzing) return
  state.analyzing = true
  state.error = ''
  try {
    const result = await generateCopy({
      jobId: state.jobId,
      name: state.name,
      feature: state.feature,
      sellingPoints: state.sellingPoints,
      footer: state.footer,
      launchText: state.launchText,
      badgeText: state.badgeText,
    })
    state.copywriting = result.copywriting
    state.aiWarning = result.warning
    const first = result.copywriting[0]
    if (first) {
      if (!state.feature.trim()) state.feature = first.subtitle
    }
  } catch (error) {
    state.aiWarning = error instanceof Error ? error.message : '文案生成失败。'
  } finally {
    state.analyzing = false
  }
}

async function translateName() {
  const chineseName = state.feature.trim()
  if (!chineseName || state.translating) return
  state.translating = true
  state.aiWarning = ''
  try {
    state.name = await translateProductName(chineseName)
  } catch (error) {
    state.aiWarning = error instanceof Error ? error.message : '英文名生成失败，请稍后重试。'
  } finally {
    state.translating = false
  }
}

async function refineCopywriting(index: number, feedback: CopyFeedback) {
  const current = state.copywriting[index]
  const hasFeedback = [
    feedback.subtitle, feedback.footer, feedback.launchText, feedback.badgeText,
    ...feedback.sellingPoints,
  ].some((item) => item.trim())
  if (!current || !hasFeedback || state.refiningIndex >= 0) return
  state.refiningIndex = index
  state.error = ''
  try {
    const result = await refineCopy({ jobId: state.jobId, current, feedback })
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
  if (state.generating || !state.sourceFile || !state.name.trim()) return
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
      sellingPoints: state.sellingPoints,
      footer: state.footer,
      launchText: state.launchText,
      badgeText: state.badgeText,
      style: state.style ?? 'editorial',
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
    bgRemoved: false, analyzing: false, translating: false, refiningIndex: -1, name: '', feature: '',
    style: null,
    sellingPoints: ['', '', ''], footer: '', launchText: '新品上市', badgeText: 'NEW!',
    copywriting: [], aiWarning: '', generating: false, genStep: -1, generated: false,
    candidates: [], editorDocument: null, selectedCandidateIndex: 0, error: '',
  })
  step.value = 0
}

export function useStudio() {
  return {
    steps, genSteps, state, step, selectedCandidate, canNext,
    styles, selectedStyle, selectStyle,
    setFile, next, back, goTo, applyCopywriting, generateCopySuggestions, translateName,
    refineCopywriting, selectCandidate,
    updateEditorDocument, startGenerate, reset,
  }
}
