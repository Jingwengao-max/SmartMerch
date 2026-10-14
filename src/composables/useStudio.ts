import { computed, reactive, ref } from 'vue'
import {
  assetUrl,
  cutoutProduct,
  generateCopy,
  generatePosters,
  refineCopy,
  translateProductName,
  type CopywritingOption,
  type PosterCandidate,
  type PosterDocument,
} from '@/services/posterApi'

export const steps = [
  { no: '01', key: 'upload', title: '上传商品', en: 'Upload' },
  { no: '02', key: 'copy', title: '确认文案', en: 'Copy' },
  { no: '03', key: 'generate', title: '生成作品', en: 'Generate' },
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
const selectedCandidate = computed<PosterCandidate | null>(() => state.candidates[state.selectedCandidateIndex] ?? null)
const canNext = computed(() => {
  if (step.value === 0) return !!state.sourceFile && state.bgRemoved && !state.removing
  if (step.value === 1) return state.name.trim().length > 0 && state.feature.trim().length > 0
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

function next() { if (canNext.value && step.value < 2) step.value++ }
function back() { if (step.value > 0 && !state.generating) step.value-- }
function goTo(index: number) { if (index >= 0 && index <= step.value && !state.generating) step.value = index }
function applyCopywriting(option: CopywritingOption) {
  if (!state.feature.trim()) state.feature = option.subtitle
  if (option.sellingPoints?.length) {
    state.sellingPoints = [...option.sellingPoints.slice(0, 3), '', ''].slice(0, 3)
  }
  state.footer = option.footer || state.footer
  state.launchText = option.launchText || state.launchText
  state.badgeText = option.badgeText || state.badgeText
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

async function refineCopywriting(index: number, instruction: string) {
  const current = state.copywriting[index]
  if (!current || !instruction.trim() || state.refiningIndex >= 0) return
  state.refiningIndex = index
  state.error = ''
  try {
    const result = await refineCopy({ jobId: state.jobId, current, instruction })
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
    sellingPoints: ['', '', ''], footer: '', launchText: '新品上市', badgeText: 'NEW!',
    copywriting: [], aiWarning: '', generating: false, genStep: -1, generated: false,
    candidates: [], editorDocument: null, selectedCandidateIndex: 0, error: '',
  })
  step.value = 0
}

export function useStudio() {
  return {
    steps, genSteps, state, step, selectedCandidate, canNext,
    setFile, next, back, goTo, applyCopywriting, generateCopySuggestions, translateName,
    refineCopywriting, selectCandidate,
    updateEditorDocument, startGenerate, reset,
  }
}
