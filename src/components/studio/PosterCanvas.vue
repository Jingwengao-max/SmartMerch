<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { renderPoster, type PosterData } from '@/utils/renderPoster'
import type { PosterTemplate } from '@/data/templates'

const props = withDefaults(
  defineProps<{
    template: PosterTemplate
    imageUrl?: string | null
    name?: string
    feature?: string
    vibe?: string
    styleName?: string
    styleEn?: string
    /** 渲染逻辑宽度；缩略图可以调小，省内存 */
    width?: number
    pixelRatio?: number
  }>(),
  { width: 900, pixelRatio: 2 },
)

const canvas = ref<HTMLCanvasElement | null>(null)
const ready = ref(false)

/** 连续改数据时会有多次渲染并发，用序号丢弃过期的那些 */
let renderSeq = 0

function currentData(): PosterData {
  return {
    imageUrl: props.imageUrl ?? null,
    name: props.name ?? '',
    feature: props.feature ?? '',
    vibe: props.vibe ?? '',
    styleName: props.styleName ?? '',
    styleEn: props.styleEn ?? '',
  }
}

async function draw() {
  if (!canvas.value) return
  const seq = ++renderSeq
  try {
    await renderPoster(canvas.value, props.template, currentData(), {
      width: props.width,
      pixelRatio: props.pixelRatio,
    })
    if (seq === renderSeq) ready.value = true
  } catch (err) {
    console.error('[PosterCanvas] 渲染失败', err)
  }
}

onMounted(draw)
watch(
  () => [
    props.template,
    props.imageUrl,
    props.name,
    props.feature,
    props.vibe,
    props.styleName,
    props.styleEn,
    props.width,
    props.pixelRatio,
  ],
  draw,
)
</script>

<template>
  <canvas
    ref="canvas"
    class="block h-auto w-full transition-opacity duration-500"
    :class="ready ? 'opacity-100' : 'opacity-0'"
  />
</template>
