<script setup lang="ts">
import heroPhoto from '@/assets/images/hero-photo.jpg'
</script>

<template>
  <section class="relative flex min-h-[100svh] flex-col justify-end overflow-hidden">
    <!-- 海报背景（全屏铺满） -->
    <img
      :src="heroPhoto"
      alt="自然光下的静物摄影"
      class="absolute inset-0 h-full w-full object-cover object-center"
    />
    <!-- 顶部浅色过渡：让固定顶栏深色文字可读 -->
    <div
      class="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-paper/95 via-paper/30 to-transparent"
    ></div>
    <!-- 底部压暗：让浅色标题与按钮可读 -->
    <div
      class="absolute inset-0 bg-gradient-to-t from-ink/70 via-ink/20 to-transparent"
    ></div>

    <!-- 顶部刊头（叠在固定顶栏下方） -->
    <div class="absolute inset-x-0 top-24 z-10 px-6 md:top-28 md:px-10 lg:px-16">
      <div
        class="flex items-center justify-between border-b border-ink/25 pb-4 font-mono text-[10px] uppercase tracking-[0.22em] text-ink/70"
      >
        <span>智绘商品 — 在线创作工作室</span>
        <span class="hidden sm:block">第 01 期 · 创作实录</span>
        <span>Est. 2026</span>
      </div>
    </div>

    <!-- 主内容：浮于海报之上 -->
    <div class="relative z-10 px-6 pt-40 md:px-10 lg:px-16">
      <span
        v-reveal
        class="mb-7 inline-flex items-center gap-2.5 font-mono text-[11px] uppercase tracking-[0.2em] text-paper/80"
      >
        <span class="inline-block h-2 w-2 rounded-full bg-clay"></span>
        N° 001 — 人与 AI 的共同创作
      </span>

      <h1 class="font-display leading-[0.98] tracking-tight text-paper">
        <span v-reveal class="block text-[clamp(2.5rem,8vw,6.5rem)]">一件商品，</span>
        <span v-reveal="90" class="block text-[clamp(2.5rem,8vw,6.5rem)] md:pl-[6vw]">一件作品。</span>
      </h1>

      <p v-reveal="120" class="mt-7 max-w-md text-lg leading-loose text-paper/85">
        把一张普通的商品照片，交给一场人与 AI 的共同创作——它负责想象，你负责审美。
      </p>

      <div v-reveal="180" class="mt-10">
        <RouterLink
          to="/studio"
          class="group inline-flex items-center gap-3 bg-paper px-8 py-4 font-display text-xl leading-none text-ink transition-colors hover:bg-ink hover:text-paper"
        >
          开始创作
          <svg
            viewBox="0 0 24 24"
            class="h-5 w-5 transition-transform group-hover:translate-x-1"
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

      <!-- 往下读 -->
      <div
        class="mt-16 mb-7 flex items-center justify-between border-t border-paper/25 pt-5 font-mono text-[10px] uppercase tracking-[0.2em] text-paper/70"
      >
        <span>往下读 — 看一件商品如何被重新想象</span>
        <span>↓</span>
      </div>
    </div>
  </section>
</template>
