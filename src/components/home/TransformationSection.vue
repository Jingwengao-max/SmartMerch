<script setup lang="ts">
import BeforeAfterSlider from '@/components/home/BeforeAfterSlider.vue'
import beforeImg from '@/assets/images/before.svg'
import afterImg from '@/assets/images/after.svg'
</script>

<template>
  <section class="bg-paper-deep px-6 py-24 md:px-10 md:py-40 lg:px-16">
    <div class="grid grid-cols-12 items-center gap-10">
      <div class="col-span-12 md:col-span-4">
        <p v-reveal class="font-mono text-xs uppercase tracking-[0.2em] text-ink-faint">Fig. 02 — 再想象</p>
        <h2 v-reveal="60" class="mt-6 font-display text-4xl leading-tight md:text-5xl">
          同一件商品，<br />两种命运。
        </h2>
        <p v-reveal="120" class="mt-6 max-w-xs text-base leading-loose text-ink-soft">
          拖动中间的线，看看 AI 如何为它重新想象一个世界。
        </p>
      </div>

      <div class="col-span-12 md:col-span-7 md:col-start-6">
        <div v-reveal>
          <BeforeAfterSlider :before="beforeImg" :after="afterImg" />
        </div>
      </div>
    </div>
  </section>
</template>
