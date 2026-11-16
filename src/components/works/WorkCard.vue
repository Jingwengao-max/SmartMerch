<script setup lang="ts">
import { assetUrl } from '@/services/posterApi'
import type { WorkSummary } from '@/services/worksApi'

defineProps<{ work: WorkSummary; deleting: boolean; opening: boolean }>()
const emit = defineEmits<{ open: []; delete: [] }>()
</script>

<template>
  <figure class="group break-inside-avoid">
    <button
      type="button"
      class="block w-full text-left"
      :disabled="opening"
      @click="emit('open')"
    >
      <div class="relative overflow-hidden border border-warm-300" style="aspect-ratio: 3 / 4">
        <img
          :src="assetUrl(work.previewUrl)"
          :alt="work.title"
          class="h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
          loading="lazy"
        />
        <span
          v-if="opening"
          class="absolute inset-0 flex items-center justify-center bg-paper/60 text-sm text-ink-soft"
        >
          <span class="dot-pulse"></span>
        </span>
      </div>
    </button>

    <figcaption class="mt-4">
      <div class="flex items-baseline justify-between gap-3">
        <h3 class="min-w-0 truncate font-display text-lg" :title="work.title">{{ work.title }}</h3>
        <button
          type="button"
          class="shrink-0 text-xs text-red-700 transition-colors hover:text-red-800 disabled:opacity-40"
          :disabled="deleting"
          @click="emit('delete')"
        >
          {{ deleting ? '删除中…' : '删除' }}
        </button>
      </div>
      <p class="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
        更新于 {{ (work.updatedAt || '').slice(0, 10) }}
      </p>
    </figcaption>
  </figure>
</template>
