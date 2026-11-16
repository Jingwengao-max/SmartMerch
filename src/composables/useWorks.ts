import { computed, reactive, watch } from 'vue'
import { useAuth } from '@/composables/useAuth'
import { useStudio } from '@/composables/useStudio'
import { createWork, updateWork, WorksApiError } from '@/services/worksApi'
import type { PosterDocument } from '@/services/posterApi'

const auth = useAuth()
const studio = useStudio()

const state = reactive({
  saving: false,
  savedVersion: null as number | null,
  error: '',
})

/** 是否「有未保存修改 / 从未保存」——用于按钮显示。 */
const isDirty = computed(
  () => state.savedVersion === null || state.savedVersion !== studio.state.docVersion
)

let saveTokenCounter = 0
let activeToken = 0

function deriveTitle(document: PosterDocument): string | undefined {
  const title = String(
    studio.previewTitle.value || document.productName || document.name || ''
  ).trim()
  return title || undefined
}

/** 发起保存：深拷贝 + 同步 editorDocument + 快照；未登录则暂存并打开登录弹窗。 */
function requestSave(document: PosterDocument) {
  if (state.saving) return
  // 同步：把最新文档写回 editorDocument 并推进 docVersion，确保快照的文档与版本号一致。
  const synced = JSON.parse(JSON.stringify(document)) as PosterDocument
  studio.updateEditorDocument(synced)

  const token = ++saveTokenCounter
  activeToken = token
  auth.state.pendingSave = {
    document: synced,
    title: deriveTitle(document),
    style: studio.state.style,
    copy: studio.state.copy,
    workId: studio.state.editingWorkId,
    generation: studio.state.editGeneration,
    docVersion: studio.state.docVersion,
  }

  if (auth.isAuthenticated.value) {
    void doSave(token)
  } else {
    auth.openLogin()
  }
}

async function doSave(token: number) {
  const pending = auth.state.pendingSave
  if (!pending || state.saving) return
  state.saving = true
  state.error = ''
  // 本次任务是否仍属于当前编辑上下文（reset/setFile/loadSavedWork 都会 editGeneration++）
  const isCurrent = () => pending.generation === studio.state.editGeneration
  try {
    const body = {
      title: pending.title,
      style: pending.style,
      copy: pending.copy,
      document: pending.document,
    }
    const result =
      pending.workId === null
        ? await createWork(body)
        : await updateWork(pending.workId, body)

    // 只有仍是本次任务才清理 pendingSave（防止误清后来产生的新暂存）。
    if (token === activeToken) {
      auth.state.pendingSave = null
    }
    // 只有任务仍属于当前编辑上下文，才回填作品 ID 与「已保存」标记。
    if (isCurrent()) {
      if (pending.workId === null) {
        studio.state.editingWorkId = result.id
      }
      state.savedVersion = pending.docVersion
    }
  } catch (error) {
    if (error instanceof WorksApiError && error.status === 401) {
      // 会话过期：仅当 pendingSave 仍属于本次请求且任务已过期时才清理，避免误删新任务暂存。
      if (token === activeToken && !isCurrent()) {
        auth.state.pendingSave = null
      }
      auth.requireLogin()
    } else if (error instanceof WorksApiError && error.status === 404 && pending.workId !== null) {
      // 更新目标已被删除：转为新创作，避免反复 PUT 已删作品。
      if (isCurrent()) {
        studio.state.editingWorkId = null
        state.error = '作品已被删除，已转为新创作，可重新保存。'
      }
    } else if (isCurrent()) {
      state.error = error instanceof Error ? error.message : '保存失败，请稍后重试。'
    }
  } finally {
    state.saving = false
  }
}

// 登录/注册成功后续存：模块级 watcher，仅注册一次。
watch(
  () => auth.state.status,
  (now, prev) => {
    if (prev !== 'authed' && now === 'authed' && auth.state.pendingSave && !state.saving) {
      void doSave(activeToken)
    }
  }
)

// 编辑上下文变化（reset/setFile/打开作品）→ 清空错误，并按是否已关联作品设置「已保存」标记。
watch(
  () => studio.state.editGeneration,
  () => {
    state.error = ''
    state.savedVersion = studio.state.editingWorkId !== null ? studio.state.docVersion : null
  }
)

export function useWorks() {
  return { state, isDirty, requestSave }
}
