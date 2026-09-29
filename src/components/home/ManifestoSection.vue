<template>
  <section id="about" class="border-t border-warm-300 px-6 py-28 md:px-10 md:py-44 lg:px-16">
    <div class="grid grid-cols-12 gap-8">
      <div class="col-span-12 md:col-span-3">
        <p v-reveal class="font-mono text-xs uppercase tracking-[0.2em] text-ink-faint">Colophon</p>
      </div>

      <div class="col-span-12 md:col-span-8 md:col-start-4">
        <blockquote v-reveal class="font-display text-3xl leading-[1.5] md:text-5xl">
          “AI 负责降低设计门槛，<br />人负责创造审美。”
        </blockquote>
        <p v-reveal="80" class="mt-8 max-w-lg text-base leading-loose text-ink-soft">
          我们不是把设计交给机器，而是让机器成为你手边的另一位设计师——它提供方向与可能，你来做出选择。
        </p>
        <div v-reveal="140" class="mt-12">
          <RouterLink to="/studio" class="btn-cta">
            进入创作
            <svg
              viewBox="0 0 24 24"
              class="arrow h-5 w-5"
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
    </div>
  </section>
</template>
