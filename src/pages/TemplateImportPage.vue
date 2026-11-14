<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { FONT_OPTIONS } from '@/data/fonts'
import {
  analyzeReferencePoster,
  assetUrl,
  compilePosterTemplate,
  fetchPosterTemplate,
  listPosterTemplates,
  savePosterTemplate,
  type PosterAnalysis,
  type PosterObservation,
  type PosterTemplate,
  type PosterTemplateSummary,
} from '@/services/posterApi'

type ResizeDirection = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w'
type TextStyleKey = 'fontId' | 'fontSize' | 'fontWeight' | 'color' | 'textAlign'

const STORAGE_KEY = 'smartmerch:poster-analysis'
const roleOptions = [
  'title', 'productName', 'subtitle', 'sellingPoint', 'price', 'slogan',
  'footer', 'badge', 'product', 'logo', 'decoration', 'unknown',
]
const resizeDirections: ResizeDirection[] = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']
const handleClasses: Record<ResizeDirection, string> = {
  nw: '-left-1.5 -top-1.5 cursor-nwse-resize',
  n: 'left-1/2 -top-1.5 -translate-x-1/2 cursor-ns-resize',
  ne: '-right-1.5 -top-1.5 cursor-nesw-resize',
  e: '-right-1.5 top-1/2 -translate-y-1/2 cursor-ew-resize',
  se: '-right-1.5 -bottom-1.5 cursor-nwse-resize',
  s: 'left-1/2 -bottom-1.5 -translate-x-1/2 cursor-ns-resize',
  sw: '-left-1.5 -bottom-1.5 cursor-nesw-resize',
  w: '-left-1.5 top-1/2 -translate-y-1/2 cursor-ew-resize',
}

const file = ref<File | null>(null)
const localPreview = ref('')
const analysis = ref<PosterAnalysis | null>(null)
const template = ref<PosterTemplate | null>(null)
const savedTemplates = ref<PosterTemplateSummary[]>([])
const templateName = ref('我的参考海报模板')
const selectedId = ref<string | null>(null)
const draggingLayerId = ref<string | null>(null)
const dragOverLayerId = ref<string | null>(null)
const posterRef = ref<HTMLElement | null>(null)
const analyzing = ref(false)
const compiling = ref(false)
const error = ref('')
const savedMessage = ref('')

const previewUrl = computed(() => analysis.value?.sourceUrl
  ? assetUrl(analysis.value.sourceUrl)
  : localPreview.value)
const selected = computed(() => analysis.value?.observations.find(
  (item) => item.id === selectedId.value,
) ?? null)
const orderedObservations = computed(() => analysis.value
  ? [...analysis.value.observations].sort((a, b) => (b.zIndex || 0) - (a.zIndex || 0))
  : [])
const selectedFontId = computed(() => String(selected.value?.style?.fontId || 'sans'))

function replaceLocalPreview(url: string) {
  if (localPreview.value.startsWith('blob:')) URL.revokeObjectURL(localPreview.value)
  localPreview.value = url
}

function normalizeObservations() {
  if (!analysis.value) return
  analysis.value.observations.forEach((observation, index) => {
    observation.zIndex = Number(observation.zIndex || index + 1)
    observation.opacity = Number(observation.opacity ?? 1)
    observation.style = observation.style || {}
  })
}

function restoreAnalysis() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (!saved) return
    analysis.value = JSON.parse(saved) as PosterAnalysis
    normalizeObservations()
    templateName.value = `${analysis.value.style?.category || '参考海报'}模板`
    savedMessage.value = '已恢复上次保存的解析'
  } catch {
    localStorage.removeItem(STORAGE_KEY)
  }
}

function saveAnalysis() {
  if (!analysis.value) return
  localStorage.setItem(STORAGE_KEY, JSON.stringify(analysis.value))
  savedMessage.value = `已保存 ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`
}

async function loadTemplateLibrary() {
  try {
    savedTemplates.value = await listPosterTemplates()
  } catch {
    savedTemplates.value = []
  }
}

async function openSavedTemplate(templateId: string) {
  try {
    template.value = await fetchPosterTemplate(templateId)
    savedMessage.value = `已加载模板：${template.value.name}`
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '模板加载失败'
  }
}

function chooseFile(event: Event) {
  const selectedFile = (event.target as HTMLInputElement).files?.[0]
  if (!selectedFile) return
  file.value = selectedFile
  analysis.value = null
  template.value = null
  selectedId.value = null
  error.value = ''
  savedMessage.value = ''
  replaceLocalPreview(URL.createObjectURL(selectedFile))
}

async function analyze() {
  if (!file.value || analyzing.value) return
  analyzing.value = true
  error.value = ''
  template.value = null
  try {
    const result = await analyzeReferencePoster(file.value)
    result.generationPrompt = result.generationPrompt || ''
    analysis.value = result
    normalizeObservations()
    selectedId.value = result.observations[0]?.id ?? null
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '参考海报解析失败'
  } finally {
    analyzing.value = false
  }
}

function updateRole(id: string, role: string) {
  const target = analysis.value?.observations.find((item) => item.id === id)
  if (target) {
    target.roleCandidate = role
    saveAnalysis()
  }
}

function addObservation(type: 'text' | 'image') {
  if (!analysis.value) return
  const highestZ = Math.max(0, ...analysis.value.observations.map(
    (item) => Number(item.zIndex || 0),
  ))
  const id = `manual_${type}_${Date.now()}`
  const observation: PosterObservation = type === 'text'
    ? {
        id,
        type: 'text',
        roleCandidate: 'unknown',
        text: '新文字',
        bbox: [0.2, 0.2, 0.3, 0.1],
        rotation: 0,
        zIndex: highestZ + 1,
        opacity: 1,
        confidence: 1,
        reviewRequired: false,
        style: {
          fontId: 'sans',
          fontSize: 40,
          fontWeight: 700,
          color: '#222222',
          textAlign: 'left',
        },
      }
    : {
        id,
        type: 'image',
        roleCandidate: 'decoration',
        text: '',
        bbox: [0.2, 0.2, 0.3, 0.3],
        rotation: 0,
        zIndex: highestZ + 1,
        opacity: 1,
        confidence: 1,
        reviewRequired: false,
        style: {},
      }
  analysis.value.observations.push(observation)
  selectedId.value = id
  saveAnalysis()
}

function deleteSelected() {
  if (!analysis.value || !selectedId.value) return
  analysis.value.observations = analysis.value.observations.filter(
    (item) => item.id !== selectedId.value,
  )
  selectedId.value = orderedObservations.value[0]?.id ?? null
  template.value = null
  saveAnalysis()
}

function updateText(id: string, value: string) {
  updateObservation(id, (item) => {
    item.text = value
  })
}

function updateType(id: string, type: PosterObservation['type']) {
  updateObservation(id, (item) => {
    item.type = type
    if (type === 'text' && !item.style) {
      item.style = {
        fontId: 'sans',
        fontSize: 40,
        fontWeight: 700,
        color: '#222222',
        textAlign: 'left',
      }
    }
  })
}

function updateObservation(id: string, updater: (item: PosterObservation) => void) {
  const target = analysis.value?.observations.find((item) => item.id === id)
  if (!target) return
  updater(target)
  saveAnalysis()
}

function updateNumber(id: string, key: 'zIndex' | 'opacity' | 'rotation',
                      value: string) {
  updateObservation(id, (item) => {
    const parsed = Number(value)
    if (key === 'zIndex') item.zIndex = Math.round(parsed)
    if (key === 'opacity') item.opacity = Math.max(0, Math.min(1, parsed))
    if (key === 'rotation') item.rotation = parsed
  })
}

function updateBox(id: string, index: number, percentage: string) {
  updateObservation(id, (item) => {
    const value = Math.max(0, Math.min(100, Number(percentage))) / 100
    const bbox = [...item.bbox]
    if (index < 2) {
      bbox[index] = Math.min(value, 1 - bbox[index + 2])
    } else {
      bbox[index] = Math.max(0.02, Math.min(value, 1 - bbox[index - 2]))
    }
    item.bbox = bbox as [number, number, number, number]
  })
}

function updateStyle(id: string, key: TextStyleKey, value: string | number) {
  updateObservation(id, (item) => {
    item.style = item.style || {}
    item.style[key] = key === 'fontSize' || key === 'fontWeight'
      ? Number(value)
      : value
  })
}

function selectObservation(id: string) {
  selectedId.value = id
}

function startMove(event: PointerEvent, observation: PosterObservation) {
  if (event.button !== 0 || !posterRef.value) return
  event.preventDefault()
  event.stopPropagation()
  selectedId.value = observation.id
  const bounds = posterRef.value.getBoundingClientRect()
  const startX = event.clientX
  const startY = event.clientY
  const origin = [...observation.bbox]
  const move = (next: PointerEvent) => {
    const dx = (next.clientX - startX) / bounds.width
    const dy = (next.clientY - startY) / bounds.height
    observation.bbox = [
      Math.max(0, Math.min(1 - origin[2], origin[0] + dx)),
      Math.max(0, Math.min(1 - origin[3], origin[1] + dy)),
      origin[2],
      origin[3],
    ]
  }
  const end = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', end)
    saveAnalysis()
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', end)
}

function startResize(event: PointerEvent, observation: PosterObservation,
                     direction: ResizeDirection) {
  if (!posterRef.value) return
  event.preventDefault()
  event.stopPropagation()
  selectedId.value = observation.id
  const bounds = posterRef.value.getBoundingClientRect()
  const startX = event.clientX
  const startY = event.clientY
  const origin = [...observation.bbox]
  let left = origin[0]
  let top = origin[1]
  let right = origin[0] + origin[2]
  let bottom = origin[1] + origin[3]
  const move = (next: PointerEvent) => {
    const dx = (next.clientX - startX) / bounds.width
    const dy = (next.clientY - startY) / bounds.height
    let nextLeft = left
    let nextTop = top
    let nextRight = right
    let nextBottom = bottom
    if (direction.includes('w')) nextLeft = Math.max(0, Math.min(right - 0.02, origin[0] + dx))
    if (direction.includes('e')) nextRight = Math.min(1, Math.max(left + 0.02, origin[0] + origin[2] + dx))
    if (direction.includes('n')) nextTop = Math.max(0, Math.min(bottom - 0.02, origin[1] + dy))
    if (direction.includes('s')) nextBottom = Math.min(1, Math.max(top + 0.02, origin[1] + origin[3] + dy))
    observation.bbox = [
      nextLeft,
      nextTop,
      nextRight - nextLeft,
      nextBottom - nextTop,
    ]
  }
  const end = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', end)
    saveAnalysis()
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', end)
}

function startLayerDrag(event: DragEvent, id: string) {
  draggingLayerId.value = id
  selectedId.value = id
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', id)
  }
}

function dropLayer(event: DragEvent, targetId: string) {
  event.preventDefault()
  const sourceId = draggingLayerId.value
  draggingLayerId.value = null
  dragOverLayerId.value = null
  if (!sourceId || sourceId === targetId || !analysis.value) return
  const layers = [...orderedObservations.value]
  const sourceIndex = layers.findIndex((item) => item.id === sourceId)
  const [moved] = layers.splice(sourceIndex, 1)
  const targetIndex = layers.findIndex((item) => item.id === targetId)
  layers.splice(targetIndex, 0, moved)
  layers.forEach((item, index) => {
    item.zIndex = layers.length - index
  })
  saveAnalysis()
}

async function copyGenerationPrompt() {
  const prompt = analysis.value?.generationPrompt?.trim()
  if (prompt) await navigator.clipboard.writeText(prompt)
}

async function compileTemplate() {
  if (!analysis.value || compiling.value) return
  compiling.value = true
  error.value = ''
  saveAnalysis()
  try {
    const compiled = await compilePosterTemplate(analysis.value, {
      templateId: `reference-${Date.now()}`,
      name: templateName.value.trim() || '参考海报模板',
    })
    template.value = await savePosterTemplate(compiled)
    savedMessage.value = '模板已保存到后端模板库'
    await loadTemplateLibrary()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '模板编译失败'
  } finally {
    compiling.value = false
  }
}

onMounted(() => {
  restoreAnalysis()
  loadTemplateLibrary()
})
onBeforeUnmount(() => {
  if (localPreview.value.startsWith('blob:')) URL.revokeObjectURL(localPreview.value)
})
</script>

<template>
  <div class="min-h-screen bg-paper text-ink">
    <header class="flex h-16 items-center justify-between border-b border-warm-300 px-5 md:px-8">
      <RouterLink to="/" class="btn-link text-sm">← 返回</RouterLink>
      <div class="text-center">
        <p class="font-display text-xl">参考海报结构化校正</p>
        <p class="font-mono text-[10px] tracking-[0.18em] text-ink-faint">POSTER → ANALYSIS → TEMPLATE</p>
      </div>
      <RouterLink to="/studio" class="btn-link text-sm">商品生成 →</RouterLink>
    </header>

    <main class="mx-auto grid max-w-[1640px] gap-5 px-4 py-5 lg:grid-cols-[270px_minmax(0,1fr)] xl:grid-cols-[270px_minmax(0,1fr)_310px] md:px-6">
      <aside class="space-y-4">
        <section class="border border-warm-300 bg-paper p-4">
          <p class="font-mono text-[10px] tracking-[0.16em] text-ink-faint">REFERENCE POSTER</p>
          <h1 class="mt-1 font-display text-2xl">上传已有海报</h1>
          <p class="mt-2 text-xs leading-relaxed text-ink-soft">不是商品照片。上传需要学习的成品海报。</p>
          <label class="mt-4 block">
            <span class="btn-rect w-full justify-center text-xs">{{ file ? '重新选择海报' : '选择参考海报' }}</span>
            <input class="hidden" type="file" accept="image/png,image/jpeg,image/webp" @change="chooseFile" />
          </label>
          <p v-if="file" class="mt-2 truncate text-[11px] text-ink-faint">{{ file.name }}</p>
          <button class="btn-cta mt-3 w-full text-lg" :disabled="!file || analyzing" @click="analyze">
            {{ analyzing ? 'AI 解析中…' : '重新解析' }}
          </button>
          <p v-if="error" class="mt-2 text-xs text-red-700">{{ error }}</p>
          <p v-if="savedMessage" class="mt-2 text-xs text-sage">{{ savedMessage }}</p>
        </section>

        <section v-if="analysis" class="border border-warm-300 bg-paper p-4">
          <div class="flex items-center justify-between">
            <h2 class="font-display text-xl">图层</h2>
            <span class="text-[10px] text-ink-faint">{{ orderedObservations.length }} 个</span>
          </div>
          <p class="mt-1 text-[10px] text-ink-faint">拖动调整前后层级</p>
          <div class="mt-3 grid grid-cols-2 gap-2">
            <button class="btn-rect justify-center px-2 py-1 text-[11px]" @click="addObservation('text')">
              + 文字框
            </button>
            <button class="btn-rect justify-center px-2 py-1 text-[11px]" @click="addObservation('image')">
              + 图片框
            </button>
          </div>
          <div class="mt-3 max-h-[420px] space-y-1 overflow-auto">
            <button
              v-for="observation in orderedObservations"
              :key="observation.id"
              draggable="true"
              class="flex w-full cursor-grab items-center gap-2 border px-2 py-2 text-left text-xs active:cursor-grabbing"
              :class="[
                selectedId === observation.id ? 'border-ink bg-warm-100' : 'border-warm-300',
                dragOverLayerId === observation.id ? 'border-t-2 border-t-sage' : '',
              ]"
              @click="selectObservation(observation.id)"
              @dragstart="startLayerDrag($event, observation.id)"
              @dragover.prevent="dragOverLayerId = observation.id"
              @drop="dropLayer($event, observation.id)"
              @dragend="draggingLayerId = null; dragOverLayerId = null"
            >
              <span class="text-ink-faint">⋮⋮</span>
              <span class="min-w-0 flex-1 truncate">{{ observation.roleCandidate }}</span>
              <span class="font-mono text-[9px] text-ink-faint">z{{ observation.zIndex }}</span>
            </button>
          </div>
          <label class="mt-4 block text-xs text-ink-soft">
            模板名称
            <input v-model="templateName" class="field-input mt-1" maxlength="40" />
          </label>
          <button class="btn-cta mt-3 w-full text-base" :disabled="compiling" @click="compileTemplate">
            {{ compiling ? '编译并保存中…' : '编译并保存模板' }}
          </button>
        </section>

        <section class="border border-warm-300 bg-paper p-4">
          <div class="flex items-center justify-between">
            <h2 class="font-display text-xl">已保存模板</h2>
            <span class="text-[10px] text-ink-faint">{{ savedTemplates.length }} 个</span>
          </div>
          <p v-if="!savedTemplates.length" class="mt-3 text-xs text-ink-faint">还没有保存模板</p>
          <div v-else class="mt-3 max-h-[300px] space-y-2 overflow-auto">
            <button
              v-for="item in savedTemplates"
              :key="item.templateId"
              class="w-full border border-warm-300 p-2 text-left transition-colors hover:border-ink"
              @click="openSavedTemplate(item.templateId)"
            >
              <span class="block truncate text-sm">{{ item.name }}</span>
              <span class="mt-1 block text-[10px] text-ink-faint">
                {{ item.layerCount }} 图层 · {{ item.fieldCount }} 字段
              </span>
            </button>
            <RouterLink
              v-if="template && savedTemplates.length"
              :to="{ path: '/template-generate', query: { template: template.templateId } }"
              class="btn-cta mt-3 flex w-full justify-center text-base"
            >
              使用此模板生成商品海报
            </RouterLink>
          </div>
        </section>
      </aside>

      <section class="min-w-0 space-y-4">
        <div v-if="previewUrl" class="overflow-auto border border-warm-300 bg-warm-100 p-3">
          <div ref="posterRef" class="relative mx-auto max-w-[880px] select-none overflow-hidden">
            <img :src="previewUrl" alt="参考海报" class="block h-auto w-full" draggable="false" />
            <div
              v-for="observation in analysis?.observations || []"
              :key="observation.id"
              class="absolute cursor-move border-2"
              :class="selectedId === observation.id
                ? 'border-ink bg-ink/10'
                : observation.reviewRequired
                  ? 'border-red-500 bg-red-500/10'
                  : 'border-sage bg-sage/10'"
              :style="{
                left: `${observation.bbox[0] * 100}%`,
                top: `${observation.bbox[1] * 100}%`,
                width: `${observation.bbox[2] * 100}%`,
                height: `${observation.bbox[3] * 100}%`,
              }"
              @pointerdown="startMove($event, observation)"
            >
              <span class="pointer-events-none absolute left-0 top-0 max-w-full truncate bg-ink px-1 py-0.5 text-[9px] text-paper">
                {{ observation.roleCandidate }} · 识别置信度 {{ Math.round((observation.confidence || 0) * 100) }}%
              </span>
              <button
                v-for="direction in resizeDirections"
                v-if="selectedId === observation.id"
                :key="direction"
                data-resize="true"
                class="absolute h-3 w-3 rounded-full border border-ink bg-white"
                :class="handleClasses[direction]"
                :aria-label="`调整 ${direction}`"
                @pointerdown.stop="startResize($event, observation, direction)"
              ></button>
            </div>
          </div>
        </div>
        <div v-else class="flex min-h-[520px] items-center justify-center border border-dashed border-warm-300 text-sm text-ink-faint">
          请选择一张参考海报
        </div>

        <section v-if="analysis" class="border border-warm-300 bg-paper p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="font-mono text-[10px] tracking-[0.16em] text-ink-faint">AI VISUAL PROMPT</p>
              <h2 class="mt-1 font-display text-xl">图像生成提示词</h2>
            </div>
            <button class="btn-rect px-3 py-1 text-xs" @click="copyGenerationPrompt">复制提示词</button>
          </div>
          <textarea
            v-model="analysis.generationPrompt"
            class="field-textarea mt-3 min-h-28 border border-warm-300 p-3 text-sm"
            maxlength="2000"
            @change="saveAnalysis"
          ></textarea>
        </section>

        <div v-if="template" class="border border-sage bg-sage/5 p-4">
          <p class="font-mono text-[10px] tracking-[0.16em] text-sage">TEMPLATE READY</p>
          <h2 class="mt-1 font-display text-2xl">{{ template.name }}</h2>
          <p class="mt-1 text-sm text-ink-soft">
            已完成结构化编译：{{ template.layers.length }} 个图层、{{ template.fields.length }} 个可填写字段。
          </p>
          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <div class="border border-warm-300 bg-paper p-3">
              <p class="text-[10px] text-ink-faint">可填写内容</p>
              <p class="mt-1 text-sm">
                {{ template.fields.map((field) => String(field.label || field.key)).join('、') }}
              </p>
            </div>
            <div class="border border-warm-300 bg-paper p-3">
              <p class="text-[10px] text-ink-faint">画布尺寸</p>
              <p class="mt-1 font-mono text-sm">
                {{ template.canvas.width }} × {{ template.canvas.height }}
              </p>
            </div>
          </div>
          <p class="mt-3 text-xs text-ink-faint">
            模板已经保存到后端模板库；后续商品生成页可以直接读取。
          </p>
        </div>
      </section>

      <aside class="border border-warm-300 bg-paper p-4 xl:sticky xl:top-4 xl:max-h-[calc(100vh-32px)] xl:overflow-auto">
        <template v-if="selected">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="font-mono text-[10px] tracking-[0.16em] text-ink-faint">SELECTED LAYER</p>
              <h2 class="mt-1 truncate font-display text-xl">{{ selected.id }}</h2>
            </div>
            <button class="shrink-0 text-xs text-red-700" @click="deleteSelected">删除框</button>
          </div>
          <div class="mt-4 space-y-3">
            <label class="block text-xs text-ink-soft">
              元素类型
              <select class="field-input mt-1" :value="selected.type" @change="updateType(selected.id, ($event.target as HTMLSelectElement).value as PosterObservation['type'])">
                <option value="text">文字</option>
                <option value="image">图片</option>
                <option value="shape">形状</option>
              </select>
            </label>
            <label class="block text-xs text-ink-soft">
              语义角色
              <select class="field-input mt-1" :value="selected.roleCandidate" @change="updateRole(selected.id, ($event.target as HTMLSelectElement).value)">
                <option v-for="role in roleOptions" :key="role" :value="role">{{ role }}</option>
              </select>
            </label>
            <label v-if="selected.type === 'text'" class="block text-xs text-ink-soft">
              文字内容
              <textarea
                class="field-textarea mt-1 min-h-20 border border-warm-300 p-2"
                :value="selected.text"
                @change="updateText(selected.id, ($event.target as HTMLTextAreaElement).value)"
              ></textarea>
            </label>
            <div class="grid grid-cols-2 gap-2">
              <label v-for="(label, index) in ['X', 'Y', '宽', '高']" :key="label" class="text-xs text-ink-soft">
                {{ label }} %
                <input
                  class="field-input mt-1"
                  type="number"
                  step="0.1"
                  :value="Math.round(selected.bbox[index] * 1000) / 10"
                  @change="updateBox(selected.id, index, ($event.target as HTMLInputElement).value)"
                />
              </label>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <label class="text-xs text-ink-soft">
                zIndex
                <input class="field-input mt-1" type="number" :value="selected.zIndex" @change="updateNumber(selected.id, 'zIndex', ($event.target as HTMLInputElement).value)" />
              </label>
              <label class="text-xs text-ink-soft">
                旋转
                <input class="field-input mt-1" type="number" :value="selected.rotation || 0" @change="updateNumber(selected.id, 'rotation', ($event.target as HTMLInputElement).value)" />
              </label>
            </div>
            <label class="block text-xs text-ink-soft">
              透明度 {{ Math.round((selected.opacity ?? 1) * 100) }}%
              <input
                class="mt-2 w-full"
                type="range"
                min="0"
                max="1"
                step="0.01"
                :value="selected.opacity ?? 1"
                @input="updateNumber(selected.id, 'opacity', ($event.target as HTMLInputElement).value)"
              />
            </label>

            <template v-if="selected.type === 'text'">
              <div class="border-t border-warm-300 pt-3">
                <p class="font-display text-lg">文字样式</p>
                <label class="mt-2 block text-xs text-ink-soft">
                  字体
                  <select class="field-input mt-1" :value="selectedFontId" @change="updateStyle(selected.id, 'fontId', ($event.target as HTMLSelectElement).value)">
                    <option v-for="font in FONT_OPTIONS" :key="font.id" :value="font.id">{{ font.label }}</option>
                  </select>
                </label>
                <div class="mt-2 grid grid-cols-2 gap-2">
                  <label class="text-xs text-ink-soft">
                    字号
                    <input class="field-input mt-1" type="number" min="8" max="320" :value="selected.style?.fontSize || 40" @change="updateStyle(selected.id, 'fontSize', ($event.target as HTMLInputElement).value)" />
                  </label>
                  <label class="text-xs text-ink-soft">
                    字重
                    <select class="field-input mt-1" :value="selected.style?.fontWeight || 700" @change="updateStyle(selected.id, 'fontWeight', ($event.target as HTMLSelectElement).value)">
                      <option v-for="weight in [300, 400, 500, 600, 700, 800, 900]" :key="weight" :value="weight">{{ weight }}</option>
                    </select>
                  </label>
                </div>
                <div class="mt-2 grid grid-cols-2 gap-2">
                  <label class="text-xs text-ink-soft">
                    颜色
                    <input class="mt-1 h-9 w-full" type="color" :value="String(selected.style?.color || '#222222')" @change="updateStyle(selected.id, 'color', ($event.target as HTMLInputElement).value)" />
                  </label>
                  <label class="text-xs text-ink-soft">
                    对齐
                    <select class="field-input mt-1" :value="selected.style?.textAlign || 'left'" @change="updateStyle(selected.id, 'textAlign', ($event.target as HTMLSelectElement).value)">
                      <option value="left">左</option>
                      <option value="center">中</option>
                      <option value="right">右</option>
                    </select>
                  </label>
                </div>
              </div>
            </template>

            <button class="btn-rect w-full justify-center text-xs" @click="saveAnalysis">保存解析结果</button>
          </div>
        </template>
        <p v-else class="text-sm text-ink-faint">点击海报中的框或左侧图层进行编辑。</p>
      </aside>
    </main>
  </div>
</template>
