import { computed, reactive, ref } from 'vue'
import {
  analyzeCopy,
  assetUrl,
  cutoutProduct,
  generatePosters,
  type CopywritingOption,
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
  if (step.value === 1) return state.name.trim().length > 0
  if (step.value === 2) return !!state.style
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
    analyzing: true,
    generated: false,
    candidates: [],
    error: '',
    aiWarning: '',
  })

  const cutoutTask = cutoutProduct(file)
    .then((result) => {
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

  const analysisTask = analyzeCopy(file)
    .then((result) => {
      state.copywriting = result.copywriting
      if (!state.name && result.category !== '待人工确认的商品') state.name = result.category
      if (!state.feature) state.feature = result.visible_features?.join('，') || result.copywriting[0]?.subtitle || ''
      state.aiWarning = result.warning
    })
    .catch(() => {
      state.aiWarning = ''
    })
    .finally(() => (state.analyzing = false))

  await Promise.allSettled([cutoutTask, analysisTask])
}

function next() { if (canNext.value && step.value < 3) step.value++ }
function back() { if (step.value > 0 && !state.generating) step.value-- }
function goTo(index: number) { if (index >= 0 && index <= step.value && !state.generating) step.value = index }
function selectStyle(key: string) { state.style = key }
function applyCopywriting(option: CopywritingOption) { state.name = option.title; state.feature = option.subtitle }
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
    bgRemoved: false, analyzing: false, name: '', feature: '', vibe: '', style: null,
    copywriting: [], aiWarning: '', generating: false, genStep: -1, generated: false,
    candidates: [], editorDocument: null, selectedCandidateIndex: 0, error: '',
  })
  step.value = 0
}

export function useStudio() {
  return {
    steps, styles, genSteps, state, step, selectedStyle, selectedCandidate, canNext,
    setFile, next, back, goTo, selectStyle, applyCopywriting, selectCandidate,
    updateEditorDocument, startGenerate, reset,
  }
}
