<script setup lang="ts">
import beforeImg from '@/assets/images/before.svg'
import afterImg from '@/assets/images/after.svg'
import { works } from '@/data/works'
import ProductShape from '@/components/home/ProductShape.vue'
</script>

<template>
  <section id="process" class="border-t border-warm-300 px-6 py-24 md:px-10 md:py-40 lg:px-16">
    <!-- 标题 -->
    <div class="mb-16 md:mb-24">
      <p v-reveal class="font-mono text-xs uppercase tracking-[0.2em] text-ink-faint">
        The Creative Process
      </p>
      <h2 v-reveal="60" class="mt-6 max-w-2xl font-display text-4xl leading-tight md:text-5xl">
        从一张照片，<br />到一个完整的视觉世界。
      </h2>
    </div>

    <!-- 三个阶段 -->
    <div class="grid grid-cols-1 gap-14 md:grid-cols-3 md:gap-10">
      <!-- 01 上传 -->
      <article v-reveal class="flex flex-col">
        <div
          class="flex items-baseline justify-between border-t border-warm-300 pt-4 font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint"
        >
          <span>01</span>
          <span>Upload</span>
        </div>
        <figure class="group mt-6 overflow-hidden">
          <img
            :src="beforeImg"
            alt="上传一张普通的商品照片"
            class="aspect-[3/4] w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
          />
        </figure>
        <h3 class="mt-6 font-display text-2xl">上传</h3>
        <p class="mt-2 max-w-xs text-sm leading-relaxed text-ink-soft">选择你的商品照片。</p>
      </article>

      <!-- 02 探索 -->
      <article v-reveal="80" class="flex flex-col">
        <div
          class="flex items-baseline justify-between border-t border-warm-300 pt-4 font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint"
        >
          <span>02</span>
          <span>Explore</span>
        </div>
        <div class="mt-6 grid aspect-[3/4] grid-cols-2 grid-rows-3 gap-2">
          <div
            v-for="w in works"
            :key="w.id"
            class="flex flex-col justify-between p-3"
            :style="{ backgroundColor: w.bg }"
          >
            <span
              class="font-mono text-[10px] uppercase tracking-[0.14em]"
              :style="{ color: w.fg, opacity: 0.75 }"
            >
              {{ w.style }}
            </span>
            <ProductShape :type="w.shape" :fill="w.fg" class="mx-auto h-1/3 w-1/3 opacity-90" />
            <span class="font-display text-sm leading-tight" :style="{ color: w.fg }">
              {{ w.title }}
            </span>
          </div>
        </div>
        <h3 class="mt-6 font-display text-2xl">探索</h3>
        <p class="mt-2 max-w-xs text-sm leading-relaxed text-ink-soft">选择场景与视觉风格。</p>
      </article>

      <!-- 03 完成 -->
      <article v-reveal="160" class="flex flex-col">
        <div
          class="flex items-baseline justify-between border-t border-warm-300 pt-4 font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint"
        >
          <span>03</span>
          <span>Create</span>
        </div>
        <figure class="group mt-6 overflow-hidden">
          <img
            :src="afterImg"
            alt="AI 生成的成品宣传海报"
            class="aspect-[3/4] w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
          />
        </figure>
        <h3 class="mt-6 font-display text-2xl">完成</h3>
        <p class="mt-2 max-w-xs text-sm leading-relaxed text-ink-soft">生成并调整你的作品。</p>
      </article>
    </div>
  </section>
</template>
