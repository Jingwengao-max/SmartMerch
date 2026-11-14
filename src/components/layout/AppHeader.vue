<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useAuth } from '@/composables/useAuth'

const { state, openLogin, logout } = useAuth()

const scrolled = ref(false)
const menuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)

const avatarChar = computed(() => {
  const source = state.user?.name || state.user?.email || '?'
  return source.trim().charAt(0).toUpperCase()
})

const onScroll = () => {
  scrolled.value = window.scrollY > 24
}

function onDocClick(event: MouseEvent) {
  if (menuOpen.value && menuRef.value && !menuRef.value.contains(event.target as Node)) {
    menuOpen.value = false
  }
}

function onLogout() {
  menuOpen.value = false
  logout()
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  document.addEventListener('click', onDocClick)
  onScroll()
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  document.removeEventListener('click', onDocClick)
})
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-50 border-b transition-colors duration-300"
    :class="scrolled ? 'border-warm-300 bg-paper/90 backdrop-blur' : 'border-transparent bg-transparent'"
  >
    <div class="mx-auto flex h-16 items-center justify-between px-6 md:h-[72px] md:px-10 lg:px-16">
      <RouterLink to="/" class="flex items-center gap-2.5">
        <span class="inline-block h-2.5 w-2.5 rounded-full bg-sage"></span>
        <span class="font-display text-xl tracking-wide">SmartMerch</span>
      </RouterLink>

      <nav class="hidden items-center gap-8 font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft md:flex">
        <a href="#compare" class="transition-colors hover:text-ink">原图与成品</a>
        <a href="#works" class="transition-colors hover:text-ink">作品</a>
        <a href="#about" class="transition-colors hover:text-ink">关于</a>
      </nav>

      <div class="flex items-center gap-6">
        <span class="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-ink-faint lg:block">
          Vol. 01
        </span>

        <!-- 认证区域：初始化中不渲染，避免闪现错误的用户状态 -->
        <div v-if="state.status === 'authed' && state.user" ref="menuRef" class="relative">
          <button
            type="button"
            class="flex items-center gap-2 text-sm transition-colors"
            @click="menuOpen = !menuOpen"
          >
            <span class="flex h-7 w-7 items-center justify-center rounded-full bg-sage text-xs text-paper">
              {{ avatarChar }}
            </span>
            <span class="hidden text-ink-soft sm:block">{{ state.user.name || state.user.email }}</span>
          </button>
          <Transition name="menu">
            <div
              v-if="menuOpen"
              class="absolute right-0 top-full mt-2 w-40 rounded-md border border-warm-300 bg-paper py-1 shadow-lg"
            >
              <!-- 阶段五：在此补充「作品库」「个人中心」入口 -->
              <button
                type="button"
                class="block w-full px-4 py-2 text-left text-sm text-ink-soft transition-colors hover:bg-warm-100"
                @click="onLogout"
              >
                退出登录
              </button>
            </div>
          </Transition>
        </div>
        <button
          v-else-if="state.status !== 'initializing'"
          type="button"
          class="btn-link cursor-pointer text-sm"
          @click="openLogin"
        >
          登录/注册
        </button>

        <RouterLink to="/studio" class="btn-link text-sm">进入创作<span class="arrow">→</span></RouterLink>
      </div>
    </div>
  </header>
</template>

<style scoped>
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
