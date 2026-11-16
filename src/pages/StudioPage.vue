<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useStudio } from '@/composables/useStudio'
import { useWorks } from '@/composables/useWorks'
import StudioHeader from '@/components/studio/StudioHeader.vue'
import StageNav from '@/components/studio/StageNav.vue'
import CanvasStage from '@/components/studio/CanvasStage.vue'
import ControlPanel from '@/components/studio/ControlPanel.vue'

const { state, setFile, reset, consumePendingOpenWork, loadSavedWork } = useStudio()
const works = useWorks()

function onPaste(e: ClipboardEvent) {
  const item = Array.from(e.clipboardData?.items ?? []).find((i) => i.type.startsWith('image/'))
  const file = item?.getAsFile()
  if (file) setFile(file)
}

onMounted(() => {
  reset()
  const pending = consumePendingOpenWork()
  if (pending) void loadSavedWork(pending)
  window.addEventListener('paste', onPaste)
})
onBeforeUnmount(() => window.removeEventListener('paste', onPaste))

// 有未保存修改时，离开工作室前确认。
onBeforeRouteLeave(() => {
  if (state.generated && state.editorDocument && works.isDirty.value) {
    return window.confirm('当前有未保存的修改，确定离开吗？')
  }
  return true
})
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
