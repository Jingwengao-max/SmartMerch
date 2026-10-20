import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    watch: {
      // 后端会在 backend/ 下写 generated/ 和浏览器 profile，
      // 让 Vite 监听这些文件会导致 EBUSY 崩溃或无意义的热更新。
      ignored: ['**/node_modules/**', '**/.git/**', '**/backend/**'],
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
