<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { CopyFeedback, CopyVariant, StyleField } from '@/services/posterApi'

const props = defineProps<{
  variant: CopyVariant
  fields: StyleField[]
  index: number
  busy?: boolean
}>()
const emit = defineEmits<{ apply: []; refine: [feedback: CopyFeedback] }>()

const open = ref(false)
const hint = ref('')
const feedback = reactive<CopyFeedback>({})

function reset() {
  for (const key of Object.keys(feedback)) delete feedback[key]
  for (const field of props.fields) {
    feedback[field.key] = field.kind === 'list' ? [] : ''
  }
}

function toggle() {
  open.value = !open.value
  hint.value = ''
  if (open.value) reset()
}

function textOf(key: string): string {
  const value = props.variant[key]
  if (typeof value === 'string') return value
  return Array.isArray(value) ? value.join(' / ') : ''
}

function listOf(key: string): string[] {
  const value = props.variant[key]
  return Array.isArray(value) ? value : []
}

function feedbackText(key: string): string {
  const value = feedback[key]
  return typeof value === 'string' ? value : ''
}

function feedbackList(key: string, index: number): string {
  const value = feedback[key]
  return Array.isArray(value) ? value[index] ?? '' : ''
}

function setFeedbackText(key: string, value: string) {
  feedback[key] = value
}

function setFeedbackList(key: string, index: number, value: string) {
  const current = feedback[key]
  const list = Array.isArray(current) ? [...current] : []
  while (list.length <= index) list.push('')
  list[index] = value
  feedback[key] = list
}

function submit() {
  const hasAny = Object.values(feedback).some((value) => (
    Array.isArray(value) ? value.some((item) => item.trim()) : String(value ?? '').trim()
  ))
  if (!hasAny) {
    hint.value = '先在至少一个条目下面填写修改意见'
    return
  }
  hint.value = ''
  emit('refine', JSON.parse(JSON.stringify(feedback)) as CopyFeedback)
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
        <button type="button" class="text-xs text-ink-soft underline hover:text-ink" @click="toggle">
          {{ open ? '收起意见' : '逐条提意见' }}
        </button>
        <button type="button" class="btn-rect px-2 py-1 text-xs" @click="$emit('apply')">
          一键应用
        </button>
      </div>
    </div>

    <!-- 每一块后面就是一个独立图层，所以按风格字段逐条列出 -->
    <dl class="mt-2.5 space-y-2">
      <template v-for="field in fields" :key="field.key">
        <div v-if="field.kind === 'text'">
          <div class="flex gap-3">
            <dt class="w-16 shrink-0 pt-0.5 text-[11px] text-ink-faint">{{ field.label }}</dt>
            <dd class="flex-1 text-sm leading-snug whitespace-pre-line">{{ textOf(field.key) || '—' }}</dd>
          </div>
          <input
            v-if="open"
            class="feedback"
            :value="feedbackText(field.key)"
            placeholder="例如：再简洁一点"
            @input="setFeedbackText(field.key, ($event.target as HTMLInputElement).value)"
          />
        </div>

        <div v-else>
          <div v-for="(item, itemIndex) in listOf(field.key)" :key="itemIndex">
            <div class="flex gap-3">
              <dt class="w-16 shrink-0 pt-0.5 text-[11px] text-ink-faint">
                {{ field.label }} {{ itemIndex + 1 }}
              </dt>
              <dd class="flex-1 text-sm leading-snug">{{ item }}</dd>
            </div>
            <input
              v-if="open"
              class="feedback"
              :value="feedbackList(field.key, itemIndex)"
              placeholder="例如：再短一点"
              @input="setFeedbackList(field.key, itemIndex, ($event.target as HTMLInputElement).value)"
            />
          </div>
        </div>
      </template>
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
