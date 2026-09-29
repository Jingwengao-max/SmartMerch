<script setup lang="ts">
import { useStudio } from '@/composables/useStudio'
const { steps, step, goTo } = useStudio()
</script>

<template>
  <nav class="hidden w-52 shrink-0 flex-col border-r border-warm-300 p-6 md:flex">
    <p class="mb-7 font-mono text-[10px] uppercase tracking-[0.22em] text-ink-faint">Steps — 步骤</p>

    <ol class="space-y-1">
      <li v-for="(s, i) in steps" :key="s.key">
        <button
          type="button"
          class="flex w-full items-baseline gap-3 px-3 py-2.5 text-left transition-colors"
          :class="i === step ? 'bg-paper-deep' : i > step ? 'opacity-40' : 'hover:bg-paper-deep/60'"
          :disabled="i > step"
          @click="goTo(i)"
        >
          <span class="font-mono text-xs" :class="i === step ? 'text-sage' : 'text-ink-faint'">{{ s.no }}</span>
          <span class="flex-1">
            <span class="block font-display text-base leading-tight" :class="i === step ? 'text-ink' : 'text-ink-soft'">
              {{ s.title }}
            </span>
            <span class="mt-0.5 block font-mono text-[9px] uppercase tracking-[0.15em] text-ink-faint">{{ s.en }}</span>
          </span>
          <span v-if="i < step" class="font-mono text-xs text-sage">✓</span>
        </button>
      </li>
    </ol>
  </nav>
</template>
