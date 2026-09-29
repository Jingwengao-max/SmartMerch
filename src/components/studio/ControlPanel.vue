<script setup lang="ts">
import { ref } from 'vue'
import { useStudio } from '@/composables/useStudio'

const {
  state,
  step,
  steps,
  styles,
  genSteps,
  canNext,
  selectedStyle,
  next,
  back,
  selectStyle,
  startGenerate,
  reset,
  setFile,
} = useStudio()

const vibeOptions = ['上新', '节日', '品牌', '种草', '清仓']

const fileInput = ref<HTMLInputElement | null>(null)
function openPicker() {
  fileInput.value?.click()
}
function onPick(e: Event) {
  const target = e.target as HTMLInputElement
  const f = target.files?.[0]
  if (f) setFile(f)
  target.value = ''
}
</script>

<template>
  <aside
    class="flex h-full min-h-[340px] w-full flex-col border-t border-warm-300 md:w-[380px] md:border-l md:border-t-0"
  >
    <!-- 头部 -->
    <div class="shrink-0 border-b border-warm-300 px-7 py-5">
      <p class="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-faint">
        {{ steps[step].no }} · {{ steps[step].en }}
      </p>
      <h2 class="mt-1 font-display text-2xl">{{ steps[step].title }}</h2>
    </div>

    <!-- 内容 -->
    <div class="flex-1 overflow-y-auto px-7 py-6">
      <!-- 0 上传 -->
      <div v-if="step === 0" class="space-y-5">
        <p class="text-sm leading-relaxed text-ink-soft">
          把商品照片放到画布上，AI 会自动识别主体并去除背景。
        </p>
        <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onPick" />
        <button type="button" class="btn-rect" @click="openPicker">
          {{ state.image ? '更换图片' : '选择图片' }}
        </button>
        <ul class="space-y-2 text-sm text-ink-faint">
          <li>· 支持 JPG / PNG，可直接粘贴（Cmd+V）</li>
          <li>· 商品越清晰，效果越好</li>
        </ul>
        <div v-if="state.image && state.removing" class="flex items-center gap-2 text-sm text-ink-soft">
          <span class="dot-pulse"></span> 正在识别商品主体…
        </div>
        <div v-else-if="state.bgRemoved" class="flex items-center gap-2 text-sm text-sage">
          <span class="font-mono">✓</span> 已识别商品主体 · 背景已去除
        </div>
      </div>

      <!-- 1 信息 -->
      <div v-else-if="step === 1" class="space-y-8">
        <label class="block">
          <p class="font-display text-lg leading-snug">这件商品叫什么？</p>
          <input v-model="state.name" class="field-input mt-3" placeholder="例如：手工陶瓷杯" />
        </label>
        <label class="block">
          <p class="font-display text-lg leading-snug">它最特别的地方是什么？</p>
          <textarea
            v-model="state.feature"
            class="field-textarea mt-3"
            placeholder="例如：手工拉坯，每一只都独一无二"
          ></textarea>
        </label>
        <div>
          <p class="font-display text-lg leading-snug">你希望它传达什么感觉？</p>
          <div class="mt-4 flex flex-wrap gap-2">
            <button
              v-for="v in vibeOptions"
              :key="v"
              type="button"
              class="border px-3 py-1.5 text-sm transition-colors"
              :class="state.vibe === v ? 'border-ink bg-ink text-paper' : 'border-warm-300 text-ink-soft hover:border-ink'"
              @click="state.vibe = state.vibe === v ? '' : v"
            >
              {{ v }}
            </button>
          </div>
        </div>
      </div>

      <!-- 2 风格 -->
      <div v-else-if="step === 2" class="space-y-3">
        <p class="text-sm leading-relaxed text-ink-soft">为这件商品选一种气质。</p>
        <button
          v-for="s in styles"
          :key="s.key"
          type="button"
          class="flex w-full items-center gap-4 border px-4 py-3.5 text-left transition-colors"
          :class="state.style === s.key ? 'border-ink' : 'border-warm-300 hover:border-ink/50'"
          @click="selectStyle(s.key)"
        >
          <span class="flex gap-1.5">
            <span class="h-5 w-5 rounded-full border border-black/10" :style="{ background: s.bg }"></span>
            <span class="h-5 w-5 rounded-full border border-black/10" :style="{ background: s.fg }"></span>
          </span>
          <span class="flex-1">
            <span class="block font-display text-lg leading-tight">{{ s.name }}</span>
            <span class="mt-0.5 block text-sm text-ink-soft">{{ s.desc }}</span>
          </span>
          <span class="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">{{ s.en }}</span>
        </button>
      </div>

      <!-- 3 生成 -->
      <div v-else class="space-y-5">
        <template v-if="!state.generating && !state.generated">
          <p class="text-sm leading-relaxed text-ink-soft">一切就绪，让 AI 开始为它创作。</p>
          <div class="space-y-1.5 border-t border-warm-300 pt-4 text-sm text-ink-soft">
            <p>商品：{{ state.name || '—' }}</p>
            <p>风格：{{ selectedStyle?.name ?? '—' }}</p>
            <p>方向：{{ state.vibe || '未指定' }}</p>
          </div>
        </template>

        <template v-else-if="state.generating">
          <p class="text-sm text-ink-soft">作品正在被创造…</p>
          <ul class="space-y-4 pt-2">
            <li v-for="(g, i) in genSteps" :key="g" class="flex items-center gap-3 text-sm">
              <span
                class="w-4 font-mono"
                :class="i < state.genStep ? 'text-sage' : i === state.genStep ? 'text-ink' : 'text-ink-faint'"
              >
                {{ i < state.genStep ? '✓' : i === state.genStep ? '·' : '' }}
              </span>
              <span :class="i <= state.genStep ? 'text-ink' : 'text-ink-faint'">{{ g }}</span>
              <span v-if="state.generating && i === state.genStep" class="text-sage animate-pulse">…</span>
            </li>
          </ul>
        </template>

        <template v-else>
          <div class="flex items-center gap-2 text-sage">
            <span class="font-mono">✓</span>
            <span>生成完成，共 4 个方案</span>
          </div>
          <p class="text-sm leading-relaxed text-ink-faint">（方案展示与编辑器将在下一步实现）</p>
        </template>
      </div>
    </div>

    <!-- 底部操作 -->
    <div class="shrink-0 border-t border-warm-300 px-7 py-5">
      <div v-if="step < 3" class="flex items-center gap-3">
        <button v-if="step > 0" type="button" class="btn-rect" @click="back">上一步</button>
        <button type="button" class="btn-cta flex-1" :disabled="!canNext" :class="{ 'opacity-40': !canNext }" @click="next">
          下一步
        </button>
      </div>

      <div v-else>
        <button
          v-if="!state.generating && !state.generated"
          type="button"
          class="btn-cta w-full"
          @click="startGenerate"
        >
          开始生成
        </button>
        <div v-else-if="state.generated" class="flex gap-3">
          <button type="button" class="btn-rect flex-1" @click="startGenerate">重新生成</button>
          <button type="button" class="btn-cta flex-1" @click="reset">重新开始</button>
        </div>
        <div v-else class="text-center text-sm text-ink-faint">创作中…</div>
      </div>
    </div>
  </aside>
</template>
