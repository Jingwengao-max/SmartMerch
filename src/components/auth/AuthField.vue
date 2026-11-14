<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    modelValue: string
    type?: 'text' | 'email' | 'password'
    placeholder?: string
    error?: string
    autocomplete?: string
  }>(),
  { type: 'text', placeholder: '', error: '', autocomplete: 'off' }
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const visible = ref(false)
const inputType = computed(() => (props.type === 'password' && !visible.value ? 'password' : 'text'))

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <label class="block">
    <span class="mb-1.5 block text-xs text-ink-soft">{{ label }}</span>
    <span class="relative block">
      <input
        :type="inputType"
        :value="modelValue"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        class="input-box"
        @input="onInput"
      />
      <button
        v-if="type === 'password'"
        type="button"
        class="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint transition-colors hover:text-ink"
        :aria-label="visible ? '隐藏密码' : '显示密码'"
        @click="visible = !visible"
      >
        <!-- 密码已显示 → 点击隐藏 -->
        <svg
          v-if="visible"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-5 w-5"
        >
          <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
          <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
          <path d="M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
          <line x1="2" y1="2" x2="22" y2="22" />
        </svg>
        <!-- 密码已隐藏 → 点击显示 -->
        <svg
          v-else
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-5 w-5"
        >
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </button>
    </span>
    <span v-if="error" class="mt-1.5 block text-xs text-red-700">{{ error }}</span>
  </label>
</template>
