<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useStudio } from '@/composables/useStudio'
import { listWorks, getWork, deleteWork, type WorkSummary } from '@/services/worksApi'
import WorkCard from '@/components/works/WorkCard.vue'

const router = useRouter()
const auth = useAuth()
const studio = useStudio()

const works = ref<WorkSummary[]>([])
const loading = ref(false)
const error = ref('')
const openingId = ref<string | null>(null)
const deletingId = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    works.value = (await listWorks()).works
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载作品失败。'
  } finally {
    loading.value = false
  }
}

async function openWork(work: WorkSummary) {
  if (openingId.value) return
  openingId.value = work.id
  error.value = ''
  try {
    const detail = await getWork(work.id)
    studio.setPendingOpenWork(detail)
    await router.push('/studio')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '打开作品失败。'
  } finally {
    openingId.value = null
  }
}

async function removeWork(work: WorkSummary) {
  if (deletingId.value) return
  if (!window.confirm(`确定删除「${work.title}」吗？此操作不可撤销。`)) return
  deletingId.value = work.id
  error.value = ''
  try {
    await deleteWork(work.id)
    works.value = works.value.filter((w) => w.id !== work.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败。'
  } finally {
    deletingId.value = null
  }
}

// 认证态就绪后加载作品列表（含首次以 URL 直达 /works 的 initializing → authed 场景）。
watch(
  () => auth.state.status,
  (status) => {
    if (status === 'authed') load()
  },
  { immediate: true }
)
</script>

<template>
  <div class="min-h-screen bg-paper text-ink">
    <section class="px-6 py-24 md:px-10 md:py-32 lg:px-16">
      <!-- 标题 -->
      <div class="mb-12 md:mb-16">
        <p class="font-mono text-xs uppercase tracking-[0.2em] text-ink-faint">
          My Works — 我的作品
        </p>
        <h1 class="mt-4 font-display text-4xl leading-tight md:text-6xl">作品库</h1>
      </div>

      <!-- 未登录 -->
      <div v-if="auth.state.status === 'guest'" class="max-w-md py-12">
        <p class="font-display text-2xl">登录后查看你的作品</p>
        <p class="mt-3 text-sm leading-relaxed text-ink-soft">
          登录即可保存、查看和继续编辑你的创作。
        </p>
        <button type="button" class="btn-cta mt-8" @click="auth.openLogin">登录 / 注册</button>
      </div>

      <!-- 加载 / 错误 / 空态 / 列表 -->
      <template v-else>
        <div v-if="loading" class="flex items-center gap-2 py-16 text-sm text-ink-soft">
          <span class="dot-pulse"></span> 正在加载作品…
        </div>
        <p v-else-if="error" class="py-16 text-sm text-red-700">{{ error }}</p>
        <div v-else-if="!works.length" class="max-w-md py-16">
          <p class="font-display text-2xl">还没有保存的作品</p>
          <p class="mt-3 text-sm leading-relaxed text-ink-soft">
            进入工作室，创作你的第一张宣传海报。
          </p>
          <RouterLink to="/studio" class="btn-cta mt-8 inline-flex">
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
        <div v-else class="columns-1 gap-12 sm:columns-2 lg:columns-3 [&>*]:mb-16">
          <WorkCard
            v-for="work in works"
            :key="work.id"
            :work="work"
            :deleting="deletingId === work.id"
            :opening="openingId === work.id"
            @open="openWork(work)"
            @delete="removeWork(work)"
          />
        </div>
      </template>
    </section>
  </div>
</template>
