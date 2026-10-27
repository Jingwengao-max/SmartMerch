<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { assetUrl, renderPoster, type PosterDocument, type PosterElement } from '@/services/posterApi'
import { FONT_OPTIONS, fontStack, resolveFontId } from '@/data/fonts'

const props = defineProps<{ document: PosterDocument }>()
const emit = defineEmits<{ 'update:document': [value: PosterDocument] }>()
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

type Guide = { axis: 'x' | 'y'; position: number }
type GeometryField = { key: 'x' | 'y' | 'width' | 'height'; label: string }

const SNAP_THRESHOLD = 8
const ROLE_LABELS: Record<string, string> = {
  product: '商品主体',
  heroTitle: '主标题',
  title: '标题',
  subtitle: '中文标题',
  label: '标签',
  badge: '徽章',
  footer: '底部品牌语',
  sellingPoint: '卖点',
  sellingPointEn: '英文卖点',
  name: '商品名',
  slogan: '品牌口号',
  intro: '商品介绍',
  price: '价格',
  panel: '文字底板',
  icon: '装饰图标',
  glow: '文字光晕',
  background: '背景',
}
const TYPE_LABELS: Record<PosterElement['type'], string> = {
  text: '文字',
  image: '图片',
  shape: '形状',
}
const geometryFields: GeometryField[] = [
  { key: 'x', label: '横向位置' },
  { key: 'y', label: '纵向位置' },
  { key: 'width', label: '宽度' },
  { key: 'height', label: '高度' },
]

const working = ref<PosterDocument>(clone(props.document))
const selectedId = ref<string | null>(null)
const history = ref<PosterDocument[]>([])
const future = ref<PosterDocument[]>([])
const guides = ref<Guide[]>([])
const layersOpen = ref(false)
const draggingLayerId = ref<string | null>(null)
const dragOverLayerId = ref<string | null>(null)
const exporting = ref(false)
const error = ref('')
const scale = computed(() => Math.min(0.4, 540 / working.value.canvas.height))
const selected = computed(() => working.value.elements.find((item) => item.id === selectedId.value) ?? null)
const selectedFontId = computed(() => resolveFontId(selected.value?.fontFamily))
const orderedLayers = computed(() => [...working.value.elements].sort((a, b) => b.zIndex - a.zIndex))

watch(() => props.document, (value) => {
  // Our own edits are also emitted back through the parent. Only replace local
  // state when the parent supplied a genuinely different document.
  if (JSON.stringify(value) === JSON.stringify(working.value)) return
  working.value = clone(value)
  selectedId.value = null
  history.value = []
  future.value = []
  guides.value = []
})

function publish() { emit('update:document', clone(working.value)) }
function checkpoint() {
  history.value.push(clone(working.value))
  if (history.value.length > 40) history.value.shift()
  future.value = []
}
function undo() {
  const previous = history.value.pop()
  if (!previous) return
  future.value.push(clone(working.value))
  working.value = previous
  publish()
}
function redo() {
  const next = future.value.pop()
  if (!next) return
  history.value.push(clone(working.value))
  working.value = next
  publish()
}

function selectLayer(id: string) {
  selectedId.value = id
}

function layerLabel(element: PosterElement) {
  const role = element.role || ''
  const suffixMatch = role.match(/^(.*)-(shadow|emboss)$/)
  const baseRole = suffixMatch?.[1] ?? role
  const suffix = suffixMatch?.[2] === 'shadow' ? '阴影' : suffixMatch?.[2] === 'emboss' ? '投影' : ''
  const base = ROLE_LABELS[baseRole] || (element.type === 'text' ? '文字' : element.type === 'image' ? '图片' : '形状')
  const content = element.type === 'text' ? String(element.content || '').replace(/\s+/g, ' ').trim() : ''
  const detail = content ? ` · ${content.length > 12 ? `${content.slice(0, 12)}…` : content}` : ''
  return `${base}${suffix}${detail}`
}

function layerTypeLabel(type: PosterElement['type']) {
  return TYPE_LABELS[type]
}

function isJustifiedLine(element: PosterElement, index: number) {
  if (element.lineAlignments) return element.lineAlignments[index] === 'justify'
  return !!element.lineSpacings
}

function snapTargets(axis: Guide['axis'], ignoredId: string) {
  const values = axis === 'x'
    ? [0, working.value.canvas.width / 2, working.value.canvas.width]
    : [0, working.value.canvas.height / 2, working.value.canvas.height]
  for (const element of working.value.elements) {
    if (element.id === ignoredId) continue
    if (axis === 'x') {
      values.push(element.x, element.x + element.width / 2, element.x + element.width)
    } else {
      values.push(element.y, element.y + element.height / 2, element.y + element.height)
    }
  }
  return values
}

function snapCoordinate(start: number, size: number, targets: number[]) {
  const anchors = [start, start + size / 2, start + size]
  let bestDelta = SNAP_THRESHOLD + 1
  let guidePosition: number | null = null
  for (const target of targets) {
    for (const anchor of anchors) {
      const delta = target - anchor
      if (Math.abs(delta) < Math.abs(bestDelta)) {
        bestDelta = delta
        guidePosition = target
      }
    }
  }
  return Math.abs(bestDelta) <= SNAP_THRESHOLD && guidePosition !== null
    ? { value: start + bestDelta, guide: guidePosition }
    : { value: start, guide: null }
}

function snapSize(start: number, size: number, maxSize: number, targets: number[]) {
  let bestDelta = SNAP_THRESHOLD + 1
  let guidePosition: number | null = null
  for (const target of targets) {
    const delta = target - (start + size)
    if (Math.abs(delta) < Math.abs(bestDelta)) {
      bestDelta = delta
      guidePosition = target
    }
  }
  if (Math.abs(bestDelta) > SNAP_THRESHOLD || guidePosition === null) {
    return { value: size, guide: null }
  }
  return {
    value: Math.max(30, Math.min(maxSize - start, size + bestDelta)),
    guide: guidePosition,
  }
}

function syncGuides(xGuide: number | null, yGuide: number | null) {
  guides.value = [
    ...(xGuide === null ? [] : [{ axis: 'x' as const, position: xGuide }]),
    ...(yGuide === null ? [] : [{ axis: 'y' as const, position: yGuide }]),
  ]
}

function guideStyle(guide: Guide) {
  const canvasWidth = working.value.canvas.width * scale.value
  const canvasHeight = working.value.canvas.height * scale.value
  if (guide.axis === 'x') {
    return {
      left: `${Math.min(canvasWidth - 1, guide.position * scale.value)}px`,
      top: '0',
      width: '1px',
      height: `${canvasHeight}px`,
    }
  }
  return {
    left: '0',
    top: `${Math.min(canvasHeight - 1, guide.position * scale.value)}px`,
    width: `${canvasWidth}px`,
    height: '1px',
  }
}

function startDrag(event: PointerEvent, element: PosterElement) {
  if ((event.target as HTMLElement).dataset.resize) return
  event.preventDefault()
  selectedId.value = element.id
  const startX = event.clientX
  const startY = event.clientY
  const originX = element.x
  const originY = element.y
  let changed = false
  const move = (next: PointerEvent) => {
    const rawX = originX + (next.clientX - startX) / scale.value
    const rawY = originY + (next.clientY - startY) / scale.value
    const snappedX = snapCoordinate(
      rawX, element.width, snapTargets('x', element.id),
    )
    const snappedY = snapCoordinate(
      rawY, element.height, snapTargets('y', element.id),
    )
    const x = Math.round(Math.max(0, Math.min(
      working.value.canvas.width - element.width,
      snappedX.value,
    )))
    const y = Math.round(Math.max(0, Math.min(
      working.value.canvas.height - element.height,
      snappedY.value,
    )))
    if (!changed && (x !== originX || y !== originY)) {
      checkpoint()
      changed = true
    }
    if (!changed) return
    element.x = x
    element.y = y
    syncGuides(snappedX.guide, snappedY.guide)
  }
  const end = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', end)
    window.removeEventListener('pointercancel', end)
    guides.value = []
    if (changed) publish()
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', end)
  window.addEventListener('pointercancel', end)
}

function startResize(event: PointerEvent, element: PosterElement) {
  event.preventDefault()
  event.stopPropagation()
  selectedId.value = element.id
  const startX = event.clientX
  const startY = event.clientY
  const originWidth = element.width
  const originHeight = element.height
  let changed = false
  const move = (next: PointerEvent) => {
    const rawWidth = Math.max(30, originWidth + (next.clientX - startX) / scale.value)
    const rawHeight = Math.max(30, originHeight + (next.clientY - startY) / scale.value)
    const snappedWidth = snapSize(
      element.x, rawWidth, working.value.canvas.width, snapTargets('x', element.id),
    )
    const snappedHeight = snapSize(
      element.y, rawHeight, working.value.canvas.height, snapTargets('y', element.id),
    )
    const width = Math.round(snappedWidth.value)
    const height = Math.round(snappedHeight.value)
    if (!changed && (width !== originWidth || height !== originHeight)) {
      checkpoint()
      changed = true
    }
    if (!changed) return
    element.width = width
    element.height = height
    syncGuides(snappedWidth.guide, snappedHeight.guide)
  }
  const end = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', end)
    window.removeEventListener('pointercancel', end)
    guides.value = []
    if (changed) publish()
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', end)
  window.addEventListener('pointercancel', end)
}

function editField(key: keyof PosterElement, value: string) {
  if (!selected.value) return
  const numeric = ['x', 'y', 'width', 'height', 'fontSize'].includes(key)
  const nextValue = numeric ? Number(value) : value
  if ((selected.value as Record<string, unknown>)[key] === nextValue) return
  if (numeric && (!Number.isFinite(nextValue) || Number(nextValue) < 0)) return
  checkpoint()
  ;(selected.value as Record<string, unknown>)[key] = nextValue
  publish()
}
function removeSelected() {
  if (!selected.value) return
  checkpoint()
  working.value.elements = working.value.elements.filter((item) => item.id !== selectedId.value)
  selectedId.value = null
  publish()
}

function startLayerDrag(event: DragEvent, id: string) {
  draggingLayerId.value = id
  dragOverLayerId.value = null
  selectedId.value = id
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', id)
  }
}

function dragOverLayer(event: DragEvent, id: string) {
  if (!draggingLayerId.value || draggingLayerId.value === id) return
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
  dragOverLayerId.value = id
}

function dropLayer(event: DragEvent, targetId: string) {
  event.preventDefault()
  const sourceId = draggingLayerId.value
  draggingLayerId.value = null
  dragOverLayerId.value = null
  if (!sourceId || sourceId === targetId) return

  const layers = [...orderedLayers.value]
  const sourceIndex = layers.findIndex((item) => item.id === sourceId)
  if (sourceIndex < 0) return
  const [moved] = layers.splice(sourceIndex, 1)
  const targetIndex = layers.findIndex((item) => item.id === targetId)
  if (!moved || targetIndex < 0) return

  checkpoint()
  layers.splice(targetIndex, 0, moved)
  const highest = layers.length
  layers.forEach((item, index) => {
    item.zIndex = highest - index
  })
  publish()
}

function finishLayerDrag() {
  draggingLayerId.value = null
  dragOverLayerId.value = null
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target
  if (target instanceof HTMLElement && target.matches('input, textarea, select, [contenteditable="true"]')) return
  if (!(event.ctrlKey || event.metaKey)) return
  if (event.key.toLowerCase() === 'z') {
    event.preventDefault()
    if (event.shiftKey) redo()
    else undo()
  } else if (event.key.toLowerCase() === 'y') {
    event.preventDefault()
    redo()
  }
}

async function download() {
  exporting.value = true
  error.value = ''
  try {
    const blob = await renderPoster(working.value)
    const link = window.document.createElement('a')
    link.href = URL.createObjectURL(blob)
    const productName = (working.value.productName || '商品').trim()
      .replace(/[\\/:*?"<>|]/g, '-')
      .replace(/\s+/g, ' ')
    link.download = `智绘商品-${productName}.png`
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '导出失败'
  } finally {
    exporting.value = false
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="grid w-full gap-5 xl:grid-cols-[minmax(0,1fr)_280px]">
    <div class="min-w-0">
      <div class="mb-3 flex items-center justify-between">
        <p class="font-mono text-[10px] tracking-[0.16em] text-ink-faint">图层编辑器</p>
        <div class="flex gap-2">
          <button class="btn-rect px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-35" :disabled="!history.length" title="撤销（Ctrl+Z）" @click="undo">撤销</button>
          <button class="btn-rect px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-35" :disabled="!future.length" title="重做（Ctrl+Shift+Z）" @click="redo">重做</button>
          <button class="btn-cta px-3 py-1 text-xs" :disabled="exporting" @click="download">
            {{ exporting ? '导出中…' : '导出 PNG' }}
          </button>
        </div>
      </div>
      <div class="flex justify-center overflow-auto bg-warm-100 p-4">
        <div
          class="relative shrink-0 overflow-hidden bg-white shadow-lg"
          :style="{
            width: `${working.canvas.width * scale}px`,
            height: `${working.canvas.height * scale}px`,
            backgroundColor: working.canvas.backgroundColor || '#fff',
            backgroundImage: working.canvas.backgroundImage ? `url(${assetUrl(working.canvas.backgroundImage)})` : 'none',
            backgroundSize: 'cover',
          }"
          @pointerdown.self="selectedId = null"
        >
          <div
            v-for="element in working.elements"
            :key="element.id"
            class="absolute cursor-move select-none"
            :class="selectedId === element.id ? 'outline outline-2 outline-sage' : ''"
            :style="{
              left: `${element.x * scale}px`, top: `${element.y * scale}px`,
              width: `${element.width * scale}px`, height: `${element.height * scale}px`,
              zIndex: element.zIndex, transform: `rotate(${element.rotation || 0}deg)`,
            }"
            @pointerdown="startDrag($event, element)"
          >
            <div
              v-if="element.type === 'shape' && element.shape === 'tech-corner'"
              class="relative pointer-events-none h-full w-full"
              :style="{ opacity: element.opacity ?? 1 }"
            >
              <span class="absolute left-0 top-0 h-1/3 w-1/3 border-l-2 border-t-2" :style="{ borderColor: element.fill }"></span>
              <span class="absolute right-0 top-0 h-1/3 w-1/3 border-r-2 border-t-2" :style="{ borderColor: element.fill }"></span>
              <span class="absolute bottom-0 left-0 h-1/3 w-1/3 border-b-2 border-l-2" :style="{ borderColor: element.fill }"></span>
              <span class="absolute bottom-0 right-0 h-1/3 w-1/3 border-b-2 border-r-2" :style="{ borderColor: element.fill }"></span>
              <span class="absolute left-1/2 top-1/2 h-[3px] w-[3px] -translate-x-1/2 -translate-y-1/2 rounded-full" :style="{ background: element.fill }"></span>
            </div>
            <div
              v-else-if="element.type === 'shape' && element.shape === 'soft-shadow'"
              class="pointer-events-none h-full w-full"
              :style="{
                background: element.fill || '#ffffff',
                opacity: element.opacity ?? 0.2,
                borderRadius: '50%',
                filter: `blur(${(element.blur || 20) * scale}px)`,
              }"
            ></div>
            <div
              v-else-if="element.type === 'shape'"
              class="pointer-events-none h-full w-full"
              :style="{
                background: element.fill || '#ffffff',
                opacity: element.opacity ?? 0.5,
                borderRadius: `${(element.radius || 0) * scale}px`,
              }"
            ></div>
            <img v-else-if="element.type === 'image'" :src="assetUrl(element.src)" alt="图层" class="h-full w-full object-contain pointer-events-none" />
            <div
              v-else
              class="flex h-full w-full flex-col leading-[1.18]"
              :style="{
                fontSize: `${(element.fontSize || 40) * scale}px`,
                fontWeight: element.fontWeight || 400,
                fontFamily: fontStack(element.fontFamily),
                color: element.color || '#222',
                opacity: element.opacity ?? 1,
                alignItems: element.textAlign === 'center' ? 'center' : element.textAlign === 'right' ? 'flex-end' : 'flex-start',
                justifyContent: element.verticalAlign === 'middle' ? 'center' : element.verticalAlign === 'bottom' ? 'flex-end' : 'flex-start',
              }"
            >
              <div
                v-for="(line, index) in (element.content || '').split('\n')"
                :key="index"
                class="w-full whitespace-pre"
                :class="isJustifiedLine(element, index)
                  ? (line.length > 1 ? 'flex justify-between' : 'flex justify-center')
                  : ''"
                :style="{
                  textAlign: element.textAlign || 'left',
                  letterSpacing: isJustifiedLine(element, index)
                    ? undefined
                    : `${(element.lineSpacings?.[index] ?? element.letterSpacing ?? 0) * scale}px`,
                  lineHeight: element.lineHeight ? `${element.lineHeight * scale}px` : undefined,
                }"
              >
                <template v-if="isJustifiedLine(element, index)">
                  <span v-for="(character, characterIndex) in line.split('')" :key="characterIndex">{{ character }}</span>
                </template>
                <template v-else>{{ line }}</template>
              </div>
            </div>
            <button
              v-if="selectedId === element.id"
              data-resize="true"
              class="absolute -bottom-2 -right-2 z-50 h-3.5 w-3.5 rounded-full border-2 border-sage bg-white"
              aria-label="缩放图层"
              @pointerdown="startResize($event, element)"
            ></button>
          </div>
          <div
            v-for="(guide, index) in guides"
            :key="`${guide.axis}-${index}`"
            class="pointer-events-none absolute z-[9999] bg-sage/90"
            :style="guideStyle(guide)"
          ></div>
        </div>
      </div>
      <p v-if="error" class="mt-2 text-sm text-red-700">{{ error }}</p>
    </div>

    <aside class="border border-warm-300 bg-paper p-4">
      <template v-if="selected">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h3 class="font-display text-lg">图层属性</h3>
            <p class="mt-1 max-w-[210px] truncate text-[11px] text-ink-faint">{{ layerLabel(selected) }}</p>
          </div>
          <button class="text-xs text-red-700" @click="removeSelected">删除图层</button>
        </div>
        <label v-if="selected.type === 'text'" class="mb-3 block text-xs text-ink-soft">
          文字<input class="field-input mt-1" :value="selected.content" @change="editField('content', ($event.target as HTMLInputElement).value)" />
        </label>
        <label v-if="selected.type === 'text'" class="mb-3 block text-xs text-ink-soft">
          字号<input class="field-input mt-1" type="number" :value="selected.fontSize" @change="editField('fontSize', ($event.target as HTMLInputElement).value)" />
        </label>
        <label v-if="selected.type === 'text'" class="mb-3 block text-xs text-ink-soft">
          字体
          <select
            class="field-input mt-1"
            :value="selectedFontId"
            @change="editField('fontFamily', ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="font in FONT_OPTIONS" :key="font.id" :value="font.id">
              {{ font.label }} · {{ font.description }}
            </option>
          </select>
        </label>
        <label v-if="selected.type === 'text'" class="mb-3 block text-xs text-ink-soft">
          颜色<input class="mt-1 h-9 w-full" type="color" :value="selected.color?.slice(0, 7) || '#222222'" @change="editField('color', ($event.target as HTMLInputElement).value)" />
        </label>
        <div class="grid grid-cols-2 gap-2">
          <label v-for="field in geometryFields" :key="field.key" class="text-xs text-ink-soft">
            {{ field.label }}<input class="field-input mt-1" type="number" :value="selected[field.key]" @change="editField(field.key, ($event.target as HTMLInputElement).value)" />
          </label>
        </div>
      </template>
      <p v-else class="text-sm text-ink-faint">点击画布中的对象，或展开图层列表进行编辑。</p>

      <div class="mt-6 border-t border-warm-300 pt-4">
        <button
          class="flex w-full items-center justify-between text-left"
          :aria-expanded="layersOpen"
          @click="layersOpen = !layersOpen"
        >
          <span class="font-display text-lg">图层</span>
          <span class="flex items-center gap-2 text-xs text-ink-faint">
            {{ orderedLayers.length }}
            <span class="transition-transform" :class="layersOpen ? 'rotate-180' : ''">⌄</span>
          </span>
        </button>
        <div v-if="layersOpen" class="mt-3 space-y-1">
          <p class="pb-1 text-[10px] text-ink-faint">按住图层上下拖动可调整前后顺序</p>
          <button
            v-for="element in orderedLayers"
            :key="element.id"
            draggable="true"
            class="group flex w-full cursor-grab items-center gap-2 border px-2 py-2 text-left text-xs active:cursor-grabbing"
            :class="[
              selectedId === element.id ? 'border-ink bg-warm-100' : 'border-warm-300 bg-paper',
              dragOverLayerId === element.id ? 'border-t-2 border-t-sage' : '',
              draggingLayerId === element.id ? 'opacity-45' : '',
            ]"
            @click="selectLayer(element.id)"
            @dragstart="startLayerDrag($event, element.id)"
            @dragover="dragOverLayer($event, element.id)"
            @drop="dropLayer($event, element.id)"
            @dragend="finishLayerDrag"
          >
            <span class="shrink-0 text-ink-faint" aria-hidden="true">⋮⋮</span>
            <span class="min-w-0 flex-1 truncate" :title="layerLabel(element)">{{ layerLabel(element) }}</span>
            <span class="shrink-0 text-[10px] text-ink-faint">{{ layerTypeLabel(element.type) }}</span>
          </button>
        </div>
      </div>
    </aside>
  </div>
</template>
