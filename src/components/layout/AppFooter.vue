<template>
  <footer class="border-t border-warm-300 px-6 py-16 md:px-10 lg:px-16">
    <div class="grid grid-cols-12 gap-8">
      <div class="col-span-12 md:col-span-4">
        <p class="font-display text-xl">智绘商品</p>
        <p class="mt-3 max-w-xs text-sm leading-relaxed text-ink-faint">
          基于生成式 AI 的商品宣传图智能生成平台。让每一件商品，都值得被好好介绍。
        </p>
      </div>

      <div class="col-span-6 md:col-span-2 md:col-start-6">
        <p class="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-faint">Index</p>
        <a href="#original" class="mt-4 block text-sm text-ink-soft transition-colors hover:text-ink">原物</a>
        <a href="#works" class="mt-2 block text-sm text-ink-soft transition-colors hover:text-ink">作品</a>
        <a href="#about" class="mt-2 block text-sm text-ink-soft transition-colors hover:text-ink">关于</a>
      </div>

      <div class="col-span-6 md:col-span-2">
        <p class="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-faint">Start</p>
        <RouterLink to="/studio" class="mt-4 block text-sm text-ink-soft transition-colors hover:text-ink">
          进入创作
        </RouterLink>
      </div>
    </div>

    <p
      class="mt-16 flex flex-col gap-2 border-t border-warm-100 pt-6 font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint sm:flex-row sm:items-center sm:justify-between"
    >
      <span>© 2026 智绘商品 · 大学生创新项目</span>
      <span>Set in Noto Serif &amp; Noto Sans</span>
    </p>
  </footer>
</template>
