<script setup lang="ts">
import { useStudio } from '@/composables/useStudio'
const { step } = useStudio()
</script>

<template>
  <header class="flex h-16 shrink-0 items-center justify-between border-b border-warm-300 px-6">
    <RouterLink to="/" class="btn-link text-sm">← 返回</RouterLink>

    <div class="text-center">
      <p class="font-display text-lg leading-tight">未命名作品 01</p>
      <p class="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">已自动保存</p>
    </div>

    <p class="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-faint">
      Step {{ step + 1 }} / 4
    </p>
  </header>
</template>
