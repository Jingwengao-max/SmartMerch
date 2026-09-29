<script setup lang="ts">
import ProductShape from '@/components/home/ProductShape.vue'
import type { Work } from '@/data/works'

defineProps<{ work: Work }>()
</script>

<template>
  <figure class="group break-inside-avoid">
    <div class="relative overflow-hidden" :style="{ backgroundColor: work.bg }">
      <div class="relative w-full" :style="{ aspectRatio: work.ratio }">
        <!-- 内框 -->
        <div class="absolute inset-5 border" :style="{ borderColor: work.fg, opacity: 0.35 }"></div>

        <!-- 顶部标签 -->
        <div
          class="absolute left-9 top-9 font-mono text-[11px] uppercase tracking-[0.2em]"
          :style="{ color: work.fg, opacity: 0.75 }"
        >
          {{ work.style }} · N° 0{{ work.id }}
        </div>

        <!-- 产品图形 -->
        <div class="absolute inset-0 flex items-center justify-center px-16 pt-4">
          <ProductShape
            :type="work.shape"
            :fill="work.fg"
            class="h-2/5 w-2/5 opacity-90 transition-transform duration-700 ease-out group-hover:scale-105"
          />
        </div>

        <!-- 底部标题 -->
        <div class="absolute bottom-9 left-9 right-9">
          <h3 class="font-display text-2xl leading-snug" :style="{ color: work.fg }">
            {{ work.title }}
          </h3>
          <p class="mt-2 font-mono text-[10px] uppercase tracking-[0.18em]" :style="{ color: work.fg, opacity: 0.6 }">
            {{ work.en }}
          </p>
        </div>
      </div>
    </div>

    <!-- 图版说明 -->
    <figcaption class="mt-4">
      <div class="flex items-baseline justify-between font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
        <span>Plate {{ String(work.id).padStart(3, '0') }}</span>
        <span>{{ work.style }}</span>
      </div>
      <p class="mt-1 text-sm text-ink-soft">{{ work.caption }}</p>
    </figcaption>
  </figure>
</template>
