<script setup lang="ts">
defineProps<{
  type: 'jar' | 'bottle' | 'cup' | 'box' | 'tube'
  fill: string
}>()
</script>

<template>
  <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg" class="h-full w-full">
    <!-- 陶罐 -->
    <g v-if="type === 'jar'">
      <rect x="55" y="90" width="90" height="95" rx="18" :fill="fill" />
      <rect x="72" y="70" width="56" height="26" rx="10" :fill="fill" opacity="0.9" />
      <rect x="85" y="54" width="30" height="20" rx="8" :fill="fill" />
    </g>
    <!-- 瓶装 -->
    <g v-else-if="type === 'bottle'">
      <rect x="70" y="46" width="60" height="22" rx="8" :fill="fill" />
      <rect x="80" y="62" width="40" height="16" :fill="fill" opacity="0.9" />
      <rect x="62" y="74" width="76" height="112" rx="16" :fill="fill" />
    </g>
    <!-- 水杯 -->
    <g v-else-if="type === 'cup'">
      <path d="M52 84 h96 l-11 96 a20 20 0 0 1 -20 17 h-34 a20 20 0 0 1 -20 -17 z" :fill="fill" />
    </g>
    <!-- 礼盒 -->
    <g v-else-if="type === 'box'">
      <rect x="50" y="70" width="100" height="92" rx="8" :fill="fill" />
      <rect x="50" y="70" width="100" height="16" rx="8" :fill="fill" opacity="0.65" />
      <rect x="92" y="70" width="16" height="92" fill="#fff" opacity="0.35" />
    </g>
    <!-- 软管 -->
    <g v-else>
      <rect x="76" y="38" width="48" height="18" rx="8" :fill="fill" />
      <rect x="62" y="52" width="76" height="134" rx="18" :fill="fill" />
    </g>
  </svg>
</template>
