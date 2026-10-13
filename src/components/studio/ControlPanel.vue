<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useStudio } from '@/composables/useStudio'

const {
  state,
  step,
  steps,
  genSteps,
  canNext,
  next,
  back,
  applyCopywriting,
  generateCopySuggestions,
  refineCopywriting,
  selectCandidate,
  startGenerate,
  reset,
  setFile,
} = useStudio()

const fileInput = ref<HTMLInputElement | null>(null)
const copyFeedback = reactive<Record<number, string>>({})
function openPicker() {
  fileInput.value?.click()
}
function onPick(e: Event) {
  const target = e.target as HTMLInputElement
  const f = target.files?.[0]
  if (f) setFile(f)
  target.value = ''
}
function onChineseBlur() {
  if (state.feature.trim()) generateCopySuggestions(true)
}
async function onRefine(index: number) {
  const instruction = copyFeedback[index]?.trim()
  if (!instruction) return
  await refineCopywriting(index, instruction)
  copyFeedback[index] = ''
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

      <!-- 1 信息 -->
      <div v-else-if="step === 1" class="space-y-6">
        <label class="block">
          <p class="font-display text-lg leading-snug">中文商品名</p>
          <input
            v-model="state.feature"
            class="field-input mt-3"
            placeholder="例如：草莓奶油丹麦"
            @blur="onChineseBlur"
          />
        </label>
        <label class="block">
          <div class="flex items-center justify-between gap-3">
            <p class="font-display text-lg leading-snug">英文商品名</p>
            <button
              type="button"
              class="text-xs text-sage disabled:opacity-40"
              :disabled="state.analyzing || !state.feature.trim()"
              @click="generateCopySuggestions(true)"
            >{{ state.analyzing ? '生成中…' : 'AI 翻译并推荐' }}</button>
          </div>
          <input v-model="state.name" class="field-input mt-3" placeholder="例如：Strawberry Danish" />
        </label>
        <div v-if="state.copywriting.length" class="space-y-3">
          <p class="text-sm text-ink-soft">AI 文案建议（选择后仍可修改）</p>
          <div
            v-for="(item, index) in state.copywriting"
            :key="`${index}-${item.title}-${item.subtitle}`"
            class="border border-warm-300 p-3"
          >
            <button type="button" class="w-full text-left" @click="applyCopywriting(item)">
              <strong class="block text-sm">{{ item.title }}</strong>
              <span class="mt-1 block text-xs text-ink-soft">{{ item.subtitle }}</span>
              <span v-if="item.sellingPoints?.length" class="mt-2 block text-[11px] leading-relaxed text-ink-faint">
                {{ item.sellingPoints.join(' · ') }}
              </span>
            </button>
            <div class="mt-3 flex gap-2 border-t border-warm-300 pt-3">
              <input
                v-model="copyFeedback[index]"
                class="field-input min-w-0 flex-1 text-xs"
                placeholder="例如：英文名短一些"
                @keyup.enter="onRefine(index)"
              />
              <button
                type="button"
                class="btn-rect whitespace-nowrap px-2 py-1 text-xs"
                :disabled="state.refiningIndex >= 0"
                @click="onRefine(index)"
              >{{ state.refiningIndex === index ? '修改中…' : '按意见修改' }}</button>
            </div>
          </div>
        </div>
        <div class="space-y-3">
          <div>
            <p class="font-display text-lg leading-snug">商品卖点</p>
            <p class="mt-1 text-xs text-ink-faint">最多填写 3 条，系统会根据实际数量自动调整位置。</p>
          </div>
          <label v-for="(_, index) in state.sellingPoints" :key="index" class="block">
            <span class="text-xs text-ink-soft">卖点 {{ index + 1 }}</span>
            <textarea
              v-model="state.sellingPoints[index]"
              class="field-textarea mt-1"
              :placeholder="index === 0 ? '例如：精选新鲜草莓，搭配香滑奶油' : index === 1 ? '例如：层层起酥，外脆内软' : '选填第三条卖点'"
              maxlength="60"
            ></textarea>
          </label>
        </div>
        <label class="block">
          <p class="font-display text-lg leading-snug">底部品牌口号</p>
          <input v-model="state.footer" class="field-input mt-3" placeholder="例如：现做现卖 · 美味看得见" />
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="block">
            <p class="text-sm text-ink-soft">右上标签</p>
            <input v-model="state.launchText" class="field-input mt-2" placeholder="新品上市" />
          </label>
          <label class="block">
            <p class="text-sm text-ink-soft">徽章文字</p>
            <input v-model="state.badgeText" class="field-input mt-2" placeholder="NEW!" />
          </label>
        </div>
      </div>

      <!-- 2 生成 -->
      <div v-else class="space-y-5">
        <template v-if="!state.generating && !state.generated">
          <p class="text-sm leading-relaxed text-ink-soft">一切就绪，让 AI 开始为它创作。</p>
          <div class="space-y-1.5 border-t border-warm-300 pt-4 text-sm text-ink-soft">
            <p>商品：{{ state.name || '—' }}</p>
            <p>核心文案：{{ state.feature || '未填写' }}</p>
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
      <div v-if="step < 2" class="flex items-center gap-3">
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
