<script setup lang="ts">
import heroPhoto from '@/assets/images/hero-photo.jpg'
</script>

<template>
  <section class="relative flex min-h-[100svh] flex-col overflow-hidden">
    <!-- 海报背景（全屏铺满） -->
    <img
      :src="heroPhoto"
      alt="自然光下的静物摄影"
      class="absolute inset-0 h-full w-full object-cover object-center"
    />
    <!-- 顶部浅色过渡：让固定顶栏深色文字可读 -->
    <div
      class="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-paper/95 via-paper/45 to-transparent"
    ></div>
    <!-- 底部压暗：让浅色标题与按钮可读 -->
    <div
      class="absolute inset-0 bg-gradient-to-t from-ink/70 via-ink/30 to-transparent"
    ></div>

    <!-- 顶部刊头（叠在固定顶栏下方） -->
    <div class="absolute inset-x-0 top-24 z-10 px-6 md:top-28 md:px-10 lg:px-16">
      <div
        class="flex items-center justify-between border-b border-ink/25 pb-4 font-mono text-[10px] uppercase tracking-[0.22em] text-ink/70"
      >
        <span class="normal-case text-sm text-ink">SmartMerch — 在线创作工作室</span>
        <span>Est. 2026</span>
      </div>
    </div>

    <!-- 主内容组：水平与垂直居中 -->
    <div
      class="relative z-10 flex flex-1 flex-col items-center justify-center px-6 pt-32 pb-16 md:px-10 lg:px-16"
    >
      <h1
        v-reveal="60"
        class="font-serif text-[clamp(3rem,10vw,9rem)] leading-none tracking-[0.02em] text-paper"
      >
        SmartMerch
      </h1>

      <div v-reveal="120" class="mt-8 flex items-center justify-center gap-4 sm:gap-6">
        <span class="h-px w-10 bg-paper/40 sm:w-16"></span>
        <span
          class="font-sans text-sm font-medium uppercase tracking-[0.3em] text-paper/85 sm:text-base"
        >
          AI PRODUCT VISUAL STUDIO
        </span>
        <span class="h-px w-10 bg-paper/40 sm:w-16"></span>
      </div>

      <div v-reveal="180" class="mt-12">
        <RouterLink
          to="/studio"
          class="group inline-flex items-center gap-3 rounded-xl bg-sage px-12 py-4 font-display text-xl leading-none text-paper transition-colors duration-300 hover:bg-moss md:px-16 md:py-5 md:text-2xl"
        >
          开始创作
          <svg
            viewBox="0 0 24 24"
            class="h-6 w-6 transition-transform duration-300 group-hover:translate-x-1.5"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </RouterLink>
      </div>
    </div>

    <!-- 往下读 -->
    <div class="relative z-10 px-6 pb-7 md:px-10 lg:px-16">
      <div
        class="flex items-center justify-between border-t border-paper/25 pt-5 font-mono text-[10px] uppercase tracking-[0.2em] text-paper/70"
      >
        <span>往下读 — 看一件商品如何被重新想象</span>
        <span>↓</span>
      </div>
    </div>
  </section>
</template>
