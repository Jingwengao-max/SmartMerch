<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { CopyFeedback, CopywritingOption } from '@/services/posterApi'

const props = defineProps<{
  variant: CopywritingOption
  index: number
  busy?: boolean
}>()
const emit = defineEmits<{ apply: []; refine: [feedback: CopyFeedback] }>()

const open = ref(false)
const hint = ref('')
const feedback = reactive<CopyFeedback>({
  subtitle: '',
  sellingPoints: [],
  footer: '',
  launchText: '',
  badgeText: '',
})

function reset() {
  feedback.subtitle = ''
  feedback.sellingPoints = (props.variant.sellingPoints ?? []).map(() => '')
  feedback.footer = ''
  feedback.launchText = ''
  feedback.badgeText = ''
}

function toggle() {
  open.value = !open.value
  hint.value = ''
  if (open.value) reset()
}

function submit() {
  const payload: CopyFeedback = {
    subtitle: feedback.subtitle,
    sellingPoints: (props.variant.sellingPoints ?? []).map((_, i) => feedback.sellingPoints[i] ?? ''),
    footer: feedback.footer,
    launchText: feedback.launchText,
    badgeText: feedback.badgeText,
  }
  const hasAny = [
    payload.subtitle, payload.footer, payload.launchText, payload.badgeText,
    ...payload.sellingPoints,
  ].some((item) => item.trim())
  if (!hasAny) {
    hint.value = '先在至少一个条目下面填写修改意见'
    return
  }
  hint.value = ''
  emit('refine', payload)
}

// 修改成功后这一组会被替换，届时清空意见输入。
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
          class="btn-rect px-2 py-1 text-xs"
          @click="$emit('apply')"
        >
          一键应用
        </button>
      </div>
    </div>

    <!-- 每一块后面就是一个独立图层，所以这里也按块列出来 -->
    <dl class="mt-2.5 space-y-2">
      <div>
        <div class="flex gap-3">
          <dt class="w-16 shrink-0 pt-0.5 text-[11px] text-ink-faint">中文商品名</dt>
          <dd class="flex-1 text-sm leading-snug">{{ variant.subtitle || '—' }}</dd>
        </div>
        <input v-if="open" v-model="feedback.subtitle" class="feedback" placeholder="例如：再简洁一点" />
      </div>

      <div v-for="(point, pointIndex) in (variant.sellingPoints ?? [])" :key="pointIndex">
        <div class="flex gap-3">
          <dt class="w-16 shrink-0 pt-0.5 text-[11px] text-ink-faint">卖点 {{ pointIndex + 1 }}</dt>
          <dd class="flex-1 text-sm leading-snug">{{ point }}</dd>
        </div>
        <input
          v-if="open"
          v-model="feedback.sellingPoints[pointIndex]"
          class="feedback"
          placeholder="例如：更突出保温效果"
        />
      </div>

      <div>
        <div class="flex gap-3">
          <dt class="w-16 shrink-0 pt-0.5 text-[11px] text-ink-faint">品牌口号</dt>
          <dd class="flex-1 text-sm leading-snug">{{ variant.footer || '—' }}</dd>
        </div>
        <input v-if="open" v-model="feedback.footer" class="feedback" placeholder="例如：更像品牌广告语" />
      </div>

      <div>
        <div class="flex gap-3">
          <dt class="w-16 shrink-0 pt-0.5 text-[11px] text-ink-faint">右上标签</dt>
          <dd class="flex-1 text-sm leading-snug">{{ variant.launchText || '—' }}</dd>
        </div>
        <input v-if="open" v-model="feedback.launchText" class="feedback" placeholder="例如：改成限时新品" />
      </div>

      <div>
        <div class="flex gap-3">
          <dt class="w-16 shrink-0 pt-0.5 text-[11px] text-ink-faint">徽章</dt>
          <dd class="flex-1 text-sm leading-snug">{{ variant.badgeText || '—' }}</dd>
        </div>
        <input v-if="open" v-model="feedback.badgeText" class="feedback" placeholder="例如：改成 HOT" />
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
    <p v-if="hint" class="mt-2 text-xs text-red-700">{{ hint }}</p>
  </div>
</template>

<style scoped>
.feedback {
  margin: 5px 0 0 76px;
  width: calc(100% - 76px);
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
