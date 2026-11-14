<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuth } from '@/composables/useAuth'
import AuthModal from '@/components/auth/AuthModal.vue'

const { fetchCurrentUser } = useAuth()

// 应用启动时恢复登录态，刷新后可正确识别已登录/未登录。
onMounted(() => {
  fetchCurrentUser()
})
</script>

<template>
  <RouterView />
  <AuthModal />
</template>
