<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStudio } from '@/composables/useStudio'
import PosterPreview from './PosterPreview.vue'
import LayerEditor from './LayerEditor.vue'

const { state, step, selectedStyle, selectedCandidate, setFile, updateEditorDocument } = useStudio()

const dragging = ref(false)

const posterStyle = computed(() =>
  selectedStyle.value ?? { bg: '#f3efe6', fg: '#2b2723', name: '预览', en: 'Preview' }
)

const buildStep = computed(() => {
  if (step.value !== 3) return 3
  return state.generating ? state.genStep : 3
})

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
  <div class="flex h-full items-center justify-center overflow-y-auto p-8 md:p-12">
    <!-- 步骤 0：上传 -->
    <div v-if="step === 0" class="w-full max-w-xl">
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
        <div v-if="state.removing" class="relative overflow-hidden border border-warm-300">
          <img :src="state.image" alt="商品" class="w-full" />
          <div class="absolute inset-0 flex items-center justify-center bg-paper/70">
            <p class="flex items-center gap-2 text-sm text-ink-soft">
              <span class="dot-pulse"></span> 正在识别商品主体…
            </p>
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

    <LayerEditor
      v-else-if="state.generated && state.editorDocument"
      :document="state.editorDocument"
      @update:document="updateEditorDocument"
    />

    <!-- 步骤 1 / 2 / 3：海报预览 -->
    <div v-else class="w-full max-w-md">
      <PosterPreview
        :bg="posterStyle.bg"
        :fg="posterStyle.fg"
        :title="state.name"
        :tag="posterStyle.en"
        :image="state.image"
        :generated-image="selectedCandidate?.previewUrl"
        :build-step="buildStep"
      />
      <p class="mt-5 text-center font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
        <template v-if="step === 1">Fig. 01 — 预览</template>
        <template v-else-if="step === 2">Fig. 02 — {{ posterStyle.name }} 方向</template>
        <template v-else-if="state.generated">Fig. 03 — 已完成 · 共 {{ state.candidates.length }} 个方案</template>
        <template v-else-if="state.generating">Fig. 03 — 生成中</template>
        <template v-else>Fig. 03 — 准备就绪</template>
      </p>
    </div>
  </div>
</template>
