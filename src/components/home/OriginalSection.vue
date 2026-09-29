<script setup lang="ts">
import beforeImg from '@/assets/images/before.svg'
</script>

<template>
  <section id="original" class="px-6 py-24 md:px-10 md:py-40 lg:px-16">
    <div class="grid grid-cols-12 gap-8 md:gap-10">
      <div class="col-span-12 md:col-span-2">
        <p v-reveal class="font-mono text-xs uppercase tracking-[0.2em] text-ink-faint">Fig. 01</p>
      </div>

      <div class="col-span-12 md:col-span-6 md:col-start-3">
        <figure v-reveal>
          <div class="overflow-hidden">
            <img :src="beforeImg" alt="一张普通的商品照片" class="w-full" />
          </div>
          <figcaption class="mt-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">
            一张普通的商品照片
          </figcaption>
        </figure>
      </div>

      <div class="col-span-12 flex flex-col justify-end md:col-span-3 md:col-start-10">
        <p v-reveal="60" class="font-display text-2xl leading-snug md:text-3xl">
          一开始，<br />它只是一张照片。
        </p>
        <p v-reveal="120" class="mt-5 max-w-xs text-base leading-loose text-ink-soft">
          没有场景，没有文案，也没有被设计过的样子。它需要一个被好好介绍的机会。
        </p>
      </div>
    </div>
  </section>
</template>
