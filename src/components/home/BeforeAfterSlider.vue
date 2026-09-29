<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  before: string
  after: string
}>()

const container = ref<HTMLElement | null>(null)
/** 0–100：原图（左）占据的宽度百分比 */
const pos = ref(50)
let dragging = false

function clampPos(value: number) {
  return Math.min(100, Math.max(0, value))
}

function updateFromClientX(clientX: number) {
  const el = container.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  pos.value = clampPos(((clientX - rect.left) / rect.width) * 100)
}

function onPointerDown(e: PointerEvent) {
  dragging = true
  container.value?.setPointerCapture(e.pointerId)
  updateFromClientX(e.clientX)
}
function onPointerMove(e: PointerEvent) {
  if (!dragging) return
  updateFromClientX(e.clientX)
}
function onPointerUp() {
  dragging = false
}
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') pos.value = clampPos(pos.value - 4)
  if (e.key === 'ArrowRight') pos.value = clampPos(pos.value + 4)
}
</script>

<template>
  <div
    ref="container"
    role="slider"
    tabindex="0"
    aria-label="拖动对比原图与生成作品"
    aria-valuenow="50"
    class="relative mx-auto aspect-[3/4] w-full max-w-md touch-none select-none overflow-hidden"
    :style="{ boxShadow: '0 2px 40px rgba(60, 50, 40, 0.10)' }"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @keydown="onKeydown"
  >
    <!-- 后层：作品（右侧） -->
    <img
      :src="props.after"
      alt="AI 生成的宣传海报"
      class="absolute inset-0 h-full w-full object-cover"
      draggable="false"
    />
    <!-- 前层：原图（左侧，clip 裁剪） -->
    <div class="absolute inset-0" :style="{ clipPath: `inset(0 ${100 - pos}% 0 0)` }">
      <img
        :src="props.before"
        alt="原始商品图片"
        class="h-full w-full object-cover"
        draggable="false"
      />
    </div>

    <!-- 标签 -->
    <span class="absolute left-4 top-4 rounded bg-ink/60 px-2.5 py-1 font-mono text-[10px] tracking-[0.15em] text-paper">
      原图
    </span>
    <span class="absolute right-4 top-4 rounded bg-sage/80 px-2.5 py-1 font-mono text-[10px] tracking-[0.15em] text-paper">
      作品
    </span>

    <!-- 分割线 + 手柄 -->
    <div class="absolute inset-y-0" :style="{ left: pos + '%' }">
      <div class="absolute inset-y-0 w-px -translate-x-1/2 bg-paper/90"></div>
      <div
        class="absolute top-1/2 flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-paper text-ink shadow-md transition-transform"
        :class="dragging ? 'scale-110' : ''"
      >
        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 7l-5 5 5 5" />
          <path d="M15 7l5 5-5 5" />
        </svg>
      </div>
    </div>
  </div>
</template>
