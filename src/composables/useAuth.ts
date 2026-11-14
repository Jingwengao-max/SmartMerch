import { computed, reactive } from 'vue'
import {
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  me as apiMe,
  type AuthUser,
} from '@/services/authApi'

export type AuthMode = 'login' | 'register'
export type AuthStatus = 'initializing' | 'guest' | 'authed'

/**
 * 认证状态 —— 与 useStudio 一致的模块级 reactive 单例。
 * 各组件通过 useAuth() 拿到同一份状态，无需 Pinia。
 *
 * status 三态：
 * - initializing：启动时正在通过 /api/auth/me 恢复登录态，避免闪现错误状态。
 * - guest：未登录。
 * - authed：已登录。
 */
const state = reactive({
  modalOpen: false,
  modalMode: 'login' as AuthMode,
  user: null as AuthUser | null,
  status: 'initializing' as AuthStatus,
})

export function useAuth() {
  const isAuthenticated = computed(() => state.status === 'authed')

  function openLogin() {
    state.modalMode = 'login'
    state.modalOpen = true
  }
  function openRegister() {
    state.modalMode = 'register'
    state.modalOpen = true
  }
  function closeModal() {
    state.modalOpen = false
  }
  function switchMode() {
    state.modalMode = state.modalMode === 'login' ? 'register' : 'login'
  }

  /** 登录：成功更新状态并关闭弹窗；失败抛出错误，由弹窗展示并保持打开。 */
  async function login(email: string, password: string) {
    const user = await apiLogin(email, password)
    state.user = user
    state.status = 'authed'
    state.modalOpen = false
  }

  /** 注册：成功后视为已登录。 */
  async function register(email: string, password: string) {
    const user = await apiRegister(email, password)
    state.user = user
    state.status = 'authed'
    state.modalOpen = false
  }

  /** 退出：无论接口是否成功，都清除本地认证状态。 */
  async function logout() {
    try {
      await apiLogout()
    } catch {
      // 接口失败也照常退出本地状态；真实会话在刷新后会重新判断。
    } finally {
      state.user = null
      state.status = 'guest'
    }
  }

  /** 启动时恢复登录态：未登录或后端未就绪都归为 guest，不伪造已登录。 */
  async function fetchCurrentUser() {
    state.status = 'initializing'
    try {
      state.user = await apiMe()
      state.status = 'authed'
    } catch {
      state.user = null
      state.status = 'guest'
    }
  }

  return {
    state,
    isAuthenticated,
    openLogin,
    openRegister,
    closeModal,
    switchMode,
    login,
    register,
    logout,
    fetchCurrentUser,
  }
}
