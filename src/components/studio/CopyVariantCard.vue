<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { CopyFeedback, CopyVariant } from '@/services/posterApi'

const props = defineProps<{ variant: CopyVariant; index: number; busy?: boolean }>()
const emit = defineEmits<{ apply: []; refine: [feedback: CopyFeedback] }>()

const open = ref(false)
const feedback = reactive<CopyFeedback>({
  title: '',
  subtitle: '',
  selling_points: [],
  price_text: '',
  promo_text: '',
})

function reset() {
  feedback.title = ''
  feedback.subtitle = ''
  feedback.selling_points = props.variant.selling_points.map(() => '')
  feedback.price_text = ''
  feedback.promo_text = ''
}

function toggle() {
  open.value = !open.value
  if (open.value) reset()
}

function submit() {
  emit('refine', {
    title: feedback.title,
    subtitle: feedback.subtitle,
    selling_points: props.variant.selling_points.map((_, i) => feedback.selling_points[i] ?? ''),
    price_text: feedback.price_text,
    promo_text: feedback.promo_text,
  })
}

// 修改成功后这一组会被替换，届时清空意见输入，避免残留。
watch(() => props.variant, () => {
  if (open.value) reset()
})
</script>

<template>
  <div class="border border-warm-300 p-3" :class="{ 'opacity-60': busy }">
    <div class="flex items-center justify-between gap-2">
      <p class="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
        方案 {{ index + 1 }}
      </p>
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="text-xs text-ink-soft underline hover:text-ink"
          @click="toggle"
        >
          {{ open ? '收起意见' : '逐条提意见' }}
        </button>
        <button
          type="button"
          class="text-xs text-ink-soft underline hover:text-ink"
          @click="$emit('apply')"
        >
          应用这组
        </button>
      </div>
    </div>

    <!-- 每一块后面就是一个独立图层，所以这里也按块列出来 -->
    <dl class="mt-2.5 space-y-2">
      <div>
        <div class="flex gap-3">
          <dt class="w-12 shrink-0 pt-0.5 text-[11px] text-ink-faint">主标题</dt>
          <dd class="flex-1 text-sm leading-snug">{{ variant.title || '—' }}</dd>
        </div>
        <input v-if="open" v-model="feedback.title" class="feedback" placeholder="例如：再活泼一点" />
      </div>

      <div>
        <div class="flex gap-3">
          <dt class="w-12 shrink-0 pt-0.5 text-[11px] text-ink-faint">副标题</dt>
          <dd class="flex-1 text-sm leading-snug">{{ variant.subtitle || '—' }}</dd>
        </div>
        <input v-if="open" v-model="feedback.subtitle" class="feedback" placeholder="例如：更口语一些" />
      </div>

      <div v-for="(point, pointIndex) in variant.selling_points" :key="pointIndex">
        <div class="flex gap-3">
          <dt class="w-12 shrink-0 pt-0.5 text-[11px] text-ink-faint">卖点 {{ pointIndex + 1 }}</dt>
          <dd class="flex-1 text-sm leading-snug">{{ point }}</dd>
        </div>
        <input
          v-if="open"
          v-model="feedback.selling_points[pointIndex]"
          class="feedback"
          placeholder="例如：太长了，缩到 10 字以内"
        />
      </div>

      <div>
        <div class="flex gap-3">
          <dt class="w-12 shrink-0 pt-0.5 text-[11px] text-ink-faint">价格</dt>
          <dd class="flex-1 text-sm leading-snug">
            {{ variant.price_text || '—' }}
            <span v-if="variant.price_estimated" class="ml-1 font-mono text-[10px] text-ink-faint">
              参考价 · 请核对
            </span>
          </dd>
        </div>
        <input v-if="open" v-model="feedback.price_text" class="feedback" placeholder="例如：价格偏高，调低一些" />
      </div>

      <div>
        <div class="flex gap-3">
          <dt class="w-12 shrink-0 pt-0.5 text-[11px] text-ink-faint">活动</dt>
          <dd class="flex-1 text-sm leading-snug">{{ variant.promo_text || '—' }}</dd>
        </div>
        <input v-if="open" v-model="feedback.promo_text" class="feedback" placeholder="例如：换一句更有吸引力的说法" />
      </div>
    </dl>

    <button
      v-if="open"
      type="button"
      class="btn-rect mt-3 w-full py-1.5 text-xs"
      :disabled="busy"
      @click="submit"
    >
      {{ busy ? '正在修改…' : '按这些意见修改这一组' }}
    </button>
  </div>
</template>

<style scoped>
.feedback {
  margin: 5px 0 0 60px;
  width: calc(100% - 60px);
  border-bottom: 1px solid var(--color-warm-300);
  background: transparent;
  padding: 2px 0;
  font-size: 12px;
  color: inherit;
}

.feedback:focus {
  outline: none;
  border-color: #2b2723;
}

.feedback::placeholder {
  color: #b6ada0;
}
</style>
