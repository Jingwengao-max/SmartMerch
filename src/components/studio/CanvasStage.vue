<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStudio } from '@/composables/useStudio'
import PosterCanvas from './PosterCanvas.vue'

const { state, step, selectedStyle, previewTemplate, setFile, selectVariant } = useStudio()

const dragging = ref(false)

/** 传给 PosterCanvas 的渲染数据，网格里的每张图共用 */
const canvasData = computed(() => ({
  imageUrl: state.image,
  name: state.name,
  feature: state.feature,
  vibe: state.vibe,
  styleName: selectedStyle.value?.name ?? '',
  styleEn: selectedStyle.value?.en ?? '',
}))

function onDragOver(e: DragEvent) {
  e.preventDefault()
  dragging.value = true
}
function onDragLeave() {
  dragging.value = false
}
function onDrop(e: DragEvent) {
  e.preventDefault()
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) setFile(file)
}
</script>

<template>
  <div class="h-full overflow-y-auto p-8 md:p-12">
    <!-- 步骤 0：上传 -->
    <div v-if="step === 0" class="mx-auto flex h-full w-full max-w-xl items-center justify-center">
      <div
        v-if="!state.image"
        class="flex flex-col items-center justify-center border border-dashed px-8 py-20 text-center transition-colors"
        :class="dragging ? 'border-sage bg-sage/5' : 'border-warm-300'"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
      >
        <svg
          viewBox="0 0 24 24"
          class="h-10 w-10 text-ink-faint"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <path d="M21 15l-5-5L5 21" />
        </svg>
        <p class="mt-6 font-display text-2xl">把商品放到画布上</p>
        <p class="mt-3 text-sm text-ink-faint">拖入图片，或点击右侧「选择图片」</p>
      </div>

      <div v-else>
        <div v-if="state.removing || state.error" class="relative overflow-hidden border border-warm-300">
          <img :src="state.image" alt="商品" class="w-full" />
          <div class="absolute inset-0 flex items-center justify-center bg-paper/70">
            <p v-if="state.removing" class="flex items-center gap-2 text-sm text-ink-soft">
              <span class="dot-pulse"></span> 正在识别商品主体…
            </p>
            <p v-else class="mx-6 text-center text-sm text-umber">{{ state.error }}</p>
          </div>
        </div>
        <figure v-else>
          <div class="relative overflow-hidden border border-warm-300">
            <img :src="state.image" alt="商品" class="w-full" />
          </div>
          <figcaption class="mt-3 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.18em]">
            <span class="text-sage">✓ 已去除背景</span>
            <span class="text-ink-faint">{{ state.imageName }}</span>
          </figcaption>
        </figure>
      </div>
    </div>

    <!-- 步骤 3 且已生成：方案网格 -->
    <div v-else-if="step === 3 && state.generated" class="mx-auto w-full max-w-5xl">
      <div class="mb-6 flex items-baseline justify-between gap-4">
        <p class="font-display text-xl">共 {{ state.variants.length }} 个方案</p>
        <p class="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
          {{ selectedStyle?.name }} · {{ selectedStyle?.en }} — 点选切换
        </p>
      </div>

      <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <button
          v-for="(tpl, i) in state.variants"
          :key="tpl.id"
          type="button"
          class="group text-left"
          @click="selectVariant(i)"
        >
          <div
            class="relative overflow-hidden border shadow-sm transition-colors"
            :class="i === state.activeVariant ? 'border-ink' : 'border-warm-300 group-hover:border-ink/40'"
          >
            <PosterCanvas :template="tpl" v-bind="canvasData" :width="520" :pixel-ratio="1.5" />
            <span
              v-if="i === state.activeVariant"
              class="absolute right-3 top-3 bg-ink px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.15em] text-paper"
            >
              已选
            </span>
          </div>
          <p class="mt-2 font-mono text-[10px] uppercase tracking-[0.15em] text-ink-faint">
            {{ tpl.name }}
          </p>
        </button>
      </div>
    </div>

    <!-- 步骤 1 / 2，以及步骤 3 未生成时：单张实时预览 -->
    <div v-else class="flex h-full items-center justify-center">
      <div class="w-full max-w-md">
        <div class="relative overflow-hidden shadow-sm">
          <PosterCanvas :template="previewTemplate" v-bind="canvasData" :width="900" :pixel-ratio="2" />
          <div
            v-if="state.generating"
            class="absolute inset-0 flex items-center justify-center bg-paper/75"
          >
            <p class="flex items-center gap-2 text-sm text-ink-soft">
              <span class="dot-pulse"></span> 正在生成…
            </p>
          </div>
        </div>
        <p class="mt-5 text-center font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
          <template v-if="step === 1">Fig. 01 — 预览</template>
          <template v-else-if="step === 2">Fig. 02 — {{ selectedStyle?.name }} · {{ previewTemplate.name }}</template>
          <template v-else-if="state.generating">Fig. 03 — 生成中</template>
          <template v-else>Fig. 03 — 准备就绪</template>
        </p>
      </div>
    </div>
  </div>
</template>
