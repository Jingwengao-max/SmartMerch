<script setup lang="ts">
import { works } from '@/data/works'
import WorkCard from '@/components/home/WorkCard.vue'
</script>

<template>
  <section id="works" class="px-6 py-24 md:px-10 md:py-40 lg:px-16">
    <div class="mb-16 flex flex-col gap-6 md:mb-24 md:flex-row md:items-end md:justify-between">
      <div>
        <p v-reveal class="font-mono text-xs uppercase tracking-[0.2em] text-ink-faint">
          Portfolio — 精选作品
        </p>
        <h2 v-reveal="60" class="mt-6 font-display text-5xl leading-none md:text-7xl">作品集</h2>
      </div>
      <p v-reveal="120" class="max-w-xs text-sm leading-relaxed text-ink-faint">
        同一件商品，也能拥有不同的气质与表达。
      </p>
    </div>

    <div class="columns-1 gap-12 sm:columns-2 lg:columns-3 [&>*]:mb-16">
      <WorkCard v-for="w in works" :key="w.id" :work="w" v-reveal />
    </div>
  </section>
</template>
