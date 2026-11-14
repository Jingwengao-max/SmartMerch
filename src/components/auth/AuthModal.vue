<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useAuth } from '@/composables/useAuth'
import AuthField from './AuthField.vue'

const { state, closeModal, switchMode, login, register } = useAuth()

const isRegister = computed(() => state.modalMode === 'register')

const email = ref('')
const password = ref('')
const confirm = ref('')
const submitting = ref(false)
const errors = reactive({ email: '', password: '', confirm: '', form: '' })

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const PASSWORD_MIN = 8

function validate(): boolean {
  errors.email = ''
  errors.password = ''
  errors.confirm = ''
  errors.form = ''
  const value = email.value.trim()
  if (!value) errors.email = '请输入邮箱'
  else if (!EMAIL_RE.test(value)) errors.email = '邮箱格式不正确'
  if (!password.value) errors.password = '请输入密码'
  else if (password.value.length < PASSWORD_MIN) errors.password = `密码至少 ${PASSWORD_MIN} 位`
  if (isRegister.value) {
    if (!confirm.value) errors.confirm = '请再次输入密码'
    else if (confirm.value !== password.value) errors.confirm = '两次输入的密码不一致'
  }
  return !errors.email && !errors.password && !errors.confirm
}

async function submit() {
  if (!validate()) return
  submitting.value = true
  errors.form = ''
  try {
    if (isRegister.value) await register(email.value.trim(), password.value)
    else await login(email.value.trim(), password.value)
  } catch (error) {
    errors.form = error instanceof Error ? error.message : '操作失败，请稍后重试。'
  } finally {
    submitting.value = false
  }
}

// 打开时锁定背景滚动并清空表单；关闭时恢复。
watch(
  () => state.modalOpen,
  (open) => {
    if (open) {
      document.body.style.overflow = 'hidden'
      email.value = ''
      password.value = ''
      confirm.value = ''
      submitting.value = false
      Object.assign(errors, { email: '', password: '', confirm: '', form: '' })
    } else {
      document.body.style.overflow = ''
    }
  }
)

// 切换登录/注册时保留邮箱，但清空密码与错误。
watch(
  () => state.modalMode,
  () => {
    password.value = ''
    confirm.value = ''
    errors.password = ''
    errors.confirm = ''
    errors.form = ''
  }
)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && state.modalOpen) closeModal()
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="state.modalOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <!-- 半透明深色遮罩：首页仍可辨认 -->
        <div class="absolute inset-0 bg-ink/60 backdrop-blur-[2px]" @click="closeModal"></div>

        <!-- 暖白弹窗 -->
        <div class="relative w-full max-w-md rounded-xl bg-paper p-8 shadow-2xl sm:p-10">
          <!-- 关闭 -->
          <button
            type="button"
            class="absolute right-4 top-4 text-ink-faint transition-colors hover:text-ink"
            aria-label="关闭"
            @click="closeModal"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-5 w-5"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>

          <!-- 品牌 -->
          <div class="flex items-center justify-center gap-2.5">
            <span class="inline-block h-2.5 w-2.5 rounded-full bg-sage"></span>
            <span class="font-display text-2xl tracking-wide">SmartMerch</span>
          </div>
          <p class="mt-2 text-center text-sm text-ink-soft">
            {{ isRegister ? '创建账号，保存你的创作' : '登录以保存你的创作' }}
          </p>

          <!-- 表单 -->
          <form class="mt-8" novalidate @submit.prevent="submit">
            <Transition name="form" mode="out-in">
              <div :key="state.modalMode" class="space-y-5">
                <AuthField
                  label="邮箱"
                  type="email"
                  v-model="email"
                  placeholder="you@example.com"
                  autocomplete="email"
                  :error="errors.email"
                />
                <AuthField
                  label="密码"
                  type="password"
                  v-model="password"
                  placeholder="至少 8 位"
                  :autocomplete="isRegister ? 'new-password' : 'current-password'"
                  :error="errors.password"
                />
                <AuthField
                  v-if="isRegister"
                  label="确认密码"
                  type="password"
                  v-model="confirm"
                  placeholder="再次输入密码"
                  autocomplete="new-password"
                  :error="errors.confirm"
                />
              </div>
            </Transition>

            <p v-if="errors.form" class="mt-4 text-center text-sm text-red-700">{{ errors.form }}</p>

            <button
              type="submit"
              class="mt-6 w-full rounded-lg bg-sage py-3 font-display text-base text-paper transition-colors hover:bg-moss disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="submitting"
            >
              {{ submitting ? '请稍候…' : isRegister ? '注册' : '登录' }}
            </button>
          </form>

          <!-- 分隔线 -->
          <div class="mt-6 flex items-center gap-3">
            <span class="h-px flex-1 bg-warm-200"></span>
            <span class="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint">或</span>
            <span class="h-px flex-1 bg-warm-200"></span>
          </div>

          <!-- 登录/注册切换 -->
          <p class="mt-5 text-center text-sm text-ink-soft">
            {{ isRegister ? '已有账号？' : '还没有账号？' }}
            <button type="button" class="text-sage transition-colors hover:text-moss" @click="switchMode">
              {{ isRegister ? '立即登录' : '立即注册' }}
            </button>
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.form-enter-active,
.form-leave-active {
  transition: opacity 0.15s ease;
}
.form-enter-from,
.form-leave-to {
  opacity: 0;
}
</style>
