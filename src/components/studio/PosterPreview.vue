<script setup lang="ts">
withDefaults(
  defineProps<{
    bg: string
    fg: string
    title: string
    tag: string
    image?: string | null
    generatedImage?: string | null
    /** 0-3 控制海报逐层构建，3 = 完整 */
    buildStep?: number
  }>(),
  { buildStep: 3 }
)
</script>

<template>
  <div
    class="relative aspect-[3/4] w-full overflow-hidden shadow-sm transition-colors duration-500"
    :style="{ backgroundColor: bg }"
  >
    <img
      v-if="generatedImage"
      :src="generatedImage"
      alt="生成的商品海报"
      class="absolute inset-0 h-full w-full object-contain"
    />
    <template v-else>
    <!-- 内框 -->
    <div
      class="absolute inset-5 border transition-opacity duration-500"
      :style="{ borderColor: fg, opacity: buildStep >= 0 ? 0.35 : 0 }"
    ></div>

    <!-- 顶部标签 -->
    <div
      class="absolute left-9 top-9 font-mono text-[11px] uppercase tracking-[0.2em] transition-opacity duration-500"
      :style="{ color: fg, opacity: buildStep >= 2 ? 0.75 : 0 }"
    >
      {{ tag }} · N° 01
    </div>

    <!-- 产品图 -->
    <div
      class="absolute inset-0 flex items-center justify-center px-14 transition-opacity duration-500"
      :style="{ opacity: buildStep >= 1 ? 1 : 0 }"
    >
      <div v-if="image" class="w-full border bg-paper p-2.5" :style="{ borderColor: fg }">
        <img :src="image" alt="商品" class="aspect-[4/3] w-full object-cover" />
      </div>
      <svg v-else viewBox="0 0 200 200" fill="none" class="h-2/5 w-2/5">
        <rect x="55" y="90" width="90" height="95" rx="18" :fill="fg" opacity="0.85" />
        <rect x="72" y="70" width="56" height="26" rx="10" :fill="fg" opacity="0.72" />
        <rect x="85" y="54" width="30" height="20" rx="8" :fill="fg" />
      </svg>
    </div>

    <!-- 底部标题 -->
    <div
      class="absolute bottom-9 left-9 right-9 transition-opacity duration-500"
      :style="{ opacity: buildStep >= 2 ? 1 : 0 }"
    >
      <h3 class="font-display text-3xl leading-snug" :style="{ color: fg }">
        {{ title || '商品名称' }}
      </h3>
      <p class="mt-2 font-mono text-[10px] uppercase tracking-[0.18em]" :style="{ color: fg, opacity: 0.6 }">
        {{ tag }}
      </p>
    </div>
    </template>
  </div>
</template>
