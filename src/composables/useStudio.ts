import { reactive, ref, computed } from 'vue'

export interface Style {
  key: string
  name: string
  en: string
  desc: string
  bg: string
  fg: string
}

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
  image: null as string | null,
  imageName: '',
  removing: false,
  bgRemoved: false,
  name: '',
  feature: '',
  vibe: '',
  style: null as string | null,
  generating: false,
  genStep: -1,
  generated: false,
})

const step = ref(0)

let timers: ReturnType<typeof setTimeout>[] = []

function clearTimers() {
  timers.forEach((t) => clearTimeout(t))
  timers = []
}

const selectedStyle = computed<Style | null>(
  () => styles.find((s) => s.key === state.style) ?? null
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

function setFile(file: File) {
  if (!file || !file.type.startsWith('image/')) return
  clearTimers()
  const reader = new FileReader()
  reader.onload = () => {
    state.image = reader.result as string
    state.imageName = file.name
    state.bgRemoved = false
    state.removing = true
    // 模拟抠图（前端演示，实际由后端 AI 完成）
    timers.push(
      setTimeout(() => {
        state.removing = false
        state.bgRemoved = true
      }, 1200)
    )
  }
  reader.readAsDataURL(file)
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
}

function startGenerate() {
  if (state.generating || !canNext.value) return
  state.generating = true
  state.generated = false
  state.genStep = 0
  clearTimers()
  timers.push(setTimeout(() => (state.genStep = 1), 700))
  timers.push(setTimeout(() => (state.genStep = 2), 1500))
  timers.push(setTimeout(() => (state.genStep = 3), 2300))
  timers.push(
    setTimeout(() => {
      state.generating = false
      state.generated = true
    }, 3200)
  )
}

function reset() {
  clearTimers()
  Object.assign(state, {
    image: null,
    imageName: '',
    removing: false,
    bgRemoved: false,
    name: '',
    feature: '',
    vibe: '',
    style: null,
    generating: false,
    genStep: -1,
    generated: false,
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
    canNext,
    setFile,
    next,
    back,
    goTo,
    selectStyle,
    startGenerate,
    reset,
  }
}
