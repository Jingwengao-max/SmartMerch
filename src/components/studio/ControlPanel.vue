<script setup lang="ts">
import { ref } from 'vue'
import { useStudio } from '@/composables/useStudio'
import CopyVariantCard from './CopyVariantCard.vue'

const {
  state,
  step,
  steps,
  styles,
  selectedStyle,
  selectStyle,
  genSteps,
  canNext,
  next,
  back,
  applyCopywriting,
  generateCopySuggestions,
  translateName,
  refineCopywriting,
  selectCandidate,
  startGenerate,
  reset,
  setFile,
  textValue,
  setText,
  listValue,
  setList,
  previewTitle,
} = useStudio()

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
        <p class="text-sm leading-relaxed text-ink-soft">上传一张主体清晰的商品照片。</p>
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
        <p v-if="state.error" class="text-sm text-red-700">{{ state.error }}</p>
      </div>

      <!-- 1 风格 -->
      <div v-else-if="step === 1" class="space-y-5">
        <p class="text-sm leading-relaxed text-ink-soft">
          选择海报的视觉风格。灰色项为尚未导入的风格，暂时不可选。
        </p>
        <button
          v-for="item in styles"
          :key="item.key"
          type="button"
          class="flex w-full items-start gap-4 border px-4 py-3.5 text-left transition-colors"
          :class="[
            state.style === item.key ? 'border-ink' : 'border-warm-300',
            item.available ? 'hover:border-ink/50' : 'cursor-not-allowed opacity-40',
          ]"
          :disabled="!item.available"
          @click="selectStyle(item.key)"
        >
          <span class="mt-0.5 flex gap-1.5">
            <span class="h-5 w-5 rounded-full border border-black/10" :style="{ background: item.bg }"></span>
            <span class="h-5 w-5 rounded-full border border-black/10" :style="{ background: item.fg }"></span>
          </span>
          <span class="flex-1">
            <span class="block font-display text-lg leading-tight">{{ item.name }}</span>
            <span class="mt-0.5 block text-sm text-ink-soft">{{ item.desc }}</span>
          </span>
          <span class="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
            {{ item.available ? item.en : '即将导入' }}
          </span>
        </button>
        <p v-if="selectedStyle" class="text-xs text-ink-faint">当前选择：{{ selectedStyle.name }}</p>
      </div>

      <!-- 2 信息与文案 -->
      <div v-else-if="step === 2" class="space-y-6">
        <div class="flex items-center justify-between gap-3 border-b border-warm-300 pb-4">
          <div>
            <p class="font-display text-lg leading-snug">AI 宣传文案推荐</p>
            <p class="mt-1 text-xs text-ink-faint">视觉模型会结合商品图片，按当前风格的条目生成文案。</p>
          </div>
          <button
            type="button"
            class="btn-rect whitespace-nowrap px-3 py-2 text-xs"
            :disabled="state.analyzing || !state.jobId"
            @click="generateCopySuggestions()"
          >{{ state.analyzing ? '推荐中…' : 'AI 推荐' }}</button>
        </div>
        <p v-if="state.aiWarning" class="text-xs leading-relaxed text-red-700">{{ state.aiWarning }}</p>
        <div v-if="state.copywriting.length" class="space-y-3">
          <p class="text-sm text-ink-soft">AI 文案建议（可逐条提意见，或一键应用）</p>
          <CopyVariantCard
            v-for="(item, index) in state.copywriting"
            :key="index"
            :variant="item"
            :fields="state.fields"
            :index="index"
            :busy="state.refiningIndex >= 0"
            @apply="applyCopywriting(item)"
            @refine="refineCopywriting(index, $event)"
          />
        </div>
        <p v-if="state.error" class="text-sm text-red-700">{{ state.error }}</p>
        <div class="space-y-5">
          <p class="text-sm text-ink-soft">也可以直接修改下面的内容：</p>
          <p v-if="!state.fields.length" class="text-xs text-ink-faint">正在加载当前风格的文案条目…</p>
          <label v-for="field in state.fields" :key="field.key" class="block">
            <div class="flex items-center justify-between gap-3">
              <p class="font-display text-lg leading-snug">{{ field.label }}</p>
              <button
                v-if="field.key === 'title'"
                type="button"
                class="text-xs text-sage disabled:opacity-40"
                :disabled="state.translating || !textValue('subtitle').trim()"
                @click="translateName"
              >{{ state.translating ? '生成中…' : '生成英文名' }}</button>
            </div>
            <template v-if="field.kind === 'text'">
              <input
                class="field-input mt-2"
                :value="textValue(field.key)"
                :maxlength="field.maxChars"
                :placeholder="field.key === 'title' ? '例如：Strawberry Danish' : field.label"
                @input="setText(field.key, ($event.target as HTMLInputElement).value)"
              />
            </template>
            <template v-else>
              <input
                v-for="index in field.maxItems"
                :key="index"
                class="field-input mt-2"
                :value="listValue(field.key, index - 1)"
                :maxlength="field.maxChars"
                :placeholder="`${field.label} ${index}`"
                @input="setList(field.key, index - 1, ($event.target as HTMLInputElement).value)"
              />
            </template>
          </label>
        </div>
      </div>

      <!-- 2 生成 -->
      <div v-else class="space-y-5">
        <template v-if="!state.generating && !state.generated">
          <p class="text-sm leading-relaxed text-ink-soft">一切就绪，让 AI 开始为它创作。</p>
          <div class="space-y-1.5 border-t border-warm-300 pt-4 text-sm text-ink-soft">
            <p>商品：{{ previewTitle || '—' }}</p>
            <p>风格：{{ selectedStyle?.name ?? '—' }}</p>
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
            <span>生成完成，共 {{ state.candidates.length }} 个方案</span>
          </div>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="(candidate, index) in state.candidates"
              :key="candidate.id"
              type="button"
              class="overflow-hidden border p-1"
              :class="index === state.selectedCandidateIndex ? 'border-ink' : 'border-warm-300'"
              @click="selectCandidate(index)"
            >
              <img :src="candidate.previewUrl" :alt="candidate.name" class="aspect-[4/5] w-full object-cover" />
              <span class="mt-1 block truncate text-[10px]">{{ index === 0 ? '推荐 · ' : '' }}{{ candidate.name }}</span>
            </button>
          </div>
        </template>
        <p v-if="state.error" class="text-sm text-red-700">{{ state.error }}</p>
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
          <button type="button" class="btn-rect min-w-0 flex-1 whitespace-nowrap px-4" @click="startGenerate">重新生成</button>
          <button type="button" class="btn-cta min-w-0 flex-1 whitespace-nowrap px-4 text-[1.15rem]" @click="reset">重新开始</button>
        </div>
        <div v-else class="text-center text-sm text-ink-faint">创作中…</div>
      </div>
    </div>
  </aside>
</template>
