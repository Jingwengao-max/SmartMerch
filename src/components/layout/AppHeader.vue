<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const scrolled = ref(false)
const onScroll = () => {
  scrolled.value = window.scrollY > 24
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-50 border-b transition-colors duration-300"
    :class="scrolled ? 'border-warm-300 bg-paper/90 backdrop-blur' : 'border-transparent bg-transparent'"
  >
    <div class="mx-auto flex h-16 items-center justify-between px-6 md:h-[72px] md:px-10 lg:px-16">
      <RouterLink to="/" class="flex items-center gap-2.5">
        <span class="inline-block h-2.5 w-2.5 rounded-full bg-sage"></span>
        <span class="font-display text-xl tracking-wide">智绘商品</span>
      </RouterLink>

      <nav class="hidden items-center gap-8 font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft md:flex">
        <a href="#original" class="transition-colors hover:text-ink">原物</a>
        <a href="#works" class="transition-colors hover:text-ink">作品</a>
        <a href="#about" class="transition-colors hover:text-ink">关于</a>
      </nav>

      <div class="flex items-center gap-6">
        <span class="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-ink-faint lg:block">
          Vol. 01
        </span>
        <RouterLink to="/studio" class="btn-link text-sm">进入创作<span class="arrow">→</span></RouterLink>
      </div>
    </div>
  </header>
</template>
