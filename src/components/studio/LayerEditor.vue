<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { assetUrl, renderPoster, type PosterDocument, type PosterElement } from '@/services/posterApi'

const props = defineProps<{ document: PosterDocument }>()
const emit = defineEmits<{ 'update:document': [value: PosterDocument] }>()
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const working = ref<PosterDocument>(clone(props.document))
const selectedId = ref<string | null>(null)
const history = ref<PosterDocument[]>([])
const future = ref<PosterDocument[]>([])
const exporting = ref(false)
const error = ref('')
const scale = computed(() => Math.min(0.4, 540 / working.value.canvas.height))
const selected = computed(() => working.value.elements.find((item) => item.id === selectedId.value) ?? null)
const orderedLayers = computed(() => [...working.value.elements].sort((a, b) => b.zIndex - a.zIndex))

watch(() => props.document, (value) => {
  working.value = clone(value)
  selectedId.value = null
  history.value = []
  future.value = []
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
function selectLayer(id: string) { selectedId.value = id }

function startDrag(event: PointerEvent, element: PosterElement) {
  if ((event.target as HTMLElement).dataset.resize) return
  event.preventDefault()
  selectedId.value = element.id
  checkpoint()
  const startX = event.clientX
  const startY = event.clientY
  const originX = element.x
  const originY = element.y
  const move = (next: PointerEvent) => {
    element.x = Math.round(originX + (next.clientX - startX) / scale.value)
    element.y = Math.round(originY + (next.clientY - startY) / scale.value)
  }
  const end = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', end)
    publish()
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', end)
}

function startResize(event: PointerEvent, element: PosterElement) {
  event.preventDefault()
  event.stopPropagation()
  checkpoint()
  const startX = event.clientX
  const startY = event.clientY
  const originWidth = element.width
  const originHeight = element.height
  const move = (next: PointerEvent) => {
    element.width = Math.max(30, Math.round(originWidth + (next.clientX - startX) / scale.value))
    element.height = Math.max(30, Math.round(originHeight + (next.clientY - startY) / scale.value))
  }
  const end = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', end)
    publish()
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', end)
}

function editField(key: keyof PosterElement, value: string) {
  if (!selected.value) return
  checkpoint()
  const numeric = ['x', 'y', 'width', 'height', 'fontSize'].includes(key)
  ;(selected.value as Record<string, unknown>)[key] = numeric ? Number(value) : value
  publish()
}
function removeSelected() {
  if (!selected.value) return
  checkpoint()
  working.value.elements = working.value.elements.filter((item) => item.id !== selectedId.value)
  selectedId.value = null
  publish()
}

async function download() {
  exporting.value = true
  error.value = ''
  try {
    const blob = await renderPoster(working.value)
    const link = window.document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${working.value.name || 'SmartMerch海报'}.png`
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '导出失败'
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="grid w-full gap-5 xl:grid-cols-[1fr_250px]">
    <div class="min-w-0">
      <div class="mb-3 flex items-center justify-between">
        <p class="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">Layer Editor</p>
        <div class="flex gap-2">
          <button class="btn-rect px-3 py-1 text-xs" :disabled="!history.length" @click="undo">撤销</button>
          <button class="btn-rect px-3 py-1 text-xs" :disabled="!future.length" @click="redo">重做</button>
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
            <img v-if="element.type === 'image'" :src="assetUrl(element.src)" alt="图层" class="h-full w-full object-contain pointer-events-none" />
            <div
              v-else
              class="h-full w-full whitespace-nowrap leading-tight"
              :style="{ fontSize: `${(element.fontSize || 40) * scale}px`, fontWeight: element.fontWeight || 400, color: element.color || '#222' }"
            >{{ element.content }}</div>
            <button
              v-if="selectedId === element.id"
              data-resize="true"
              class="absolute -bottom-2 -right-2 h-4 w-4 rounded-full border-2 border-sage bg-white"
              aria-label="缩放图层"
              @pointerdown="startResize($event, element)"
            ></button>
          </div>
        </div>
      </div>
      <p v-if="error" class="mt-2 text-sm text-red-700">{{ error }}</p>
    </div>

    <aside class="border border-warm-300 bg-paper p-4">
      <template v-if="selected">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="font-display text-lg">图层属性</h3>
          <button class="text-xs text-red-700" @click="removeSelected">删除</button>
        </div>
        <label v-if="selected.type === 'text'" class="mb-3 block text-xs text-ink-soft">
          文字<input class="field-input mt-1" :value="selected.content" @change="editField('content', ($event.target as HTMLInputElement).value)" />
        </label>
        <label v-if="selected.type === 'text'" class="mb-3 block text-xs text-ink-soft">
          字号<input class="field-input mt-1" type="number" :value="selected.fontSize" @change="editField('fontSize', ($event.target as HTMLInputElement).value)" />
        </label>
        <label v-if="selected.type === 'text'" class="mb-3 block text-xs text-ink-soft">
          颜色<input class="mt-1 h-9 w-full" type="color" :value="selected.color?.slice(0, 7) || '#222222'" @change="editField('color', ($event.target as HTMLInputElement).value)" />
        </label>
        <div class="grid grid-cols-2 gap-2">
          <label v-for="key in (['x', 'y', 'width', 'height'] as const)" :key="key" class="text-xs text-ink-soft">
            {{ key }}<input class="field-input mt-1" type="number" :value="selected[key]" @change="editField(key, ($event.target as HTMLInputElement).value)" />
          </label>
        </div>
      </template>
      <p v-else class="text-sm text-ink-faint">点击画布或下方列表中的图层进行编辑。</p>
      <h3 class="mb-2 mt-6 font-display text-lg">图层</h3>
      <button
        v-for="element in orderedLayers"
        :key="element.id"
        class="mb-1 flex w-full justify-between border px-2 py-2 text-left text-xs"
        :class="selectedId === element.id ? 'border-ink bg-warm-100' : 'border-warm-300'"
        @click="selectLayer(element.id)"
      >
        <span>{{ element.role || (element.type === 'text' ? '文字' : '图片') }}</span>
        <span class="text-ink-faint">{{ element.type }}</span>
      </button>
    </aside>
  </div>
</template>
