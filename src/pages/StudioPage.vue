<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { useStudio } from '@/composables/useStudio'
import StudioHeader from '@/components/studio/StudioHeader.vue'
import StageNav from '@/components/studio/StageNav.vue'
import CanvasStage from '@/components/studio/CanvasStage.vue'
import ControlPanel from '@/components/studio/ControlPanel.vue'

const { setFile, reset } = useStudio()

function onPaste(e: ClipboardEvent) {
  const item = Array.from(e.clipboardData?.items ?? []).find((i) => i.type.startsWith('image/'))
  const file = item?.getAsFile()
  if (file) setFile(file)
}

onMounted(() => {
  reset()
  window.addEventListener('paste', onPaste)
})
onBeforeUnmount(() => window.removeEventListener('paste', onPaste))
</script>

<template>
  <div class="flex min-h-screen flex-col bg-paper text-ink md:h-screen">
    <StudioHeader />
    <div class="flex flex-1 flex-col md:min-h-0 md:flex-row">
      <StageNav />
      <main class="min-w-0 flex-1">
        <CanvasStage />
      </main>
      <ControlPanel />
    </div>
  </div>
</template>
