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
    // 开发环境把 API 与静态资源代理到后端，使前端与后端同源，
    // 避免 localhost / 127.0.0.1 跨站导致 SameSite=Lax Cookie 不被携带。
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/generated': 'http://127.0.0.1:8000',
      '/works-static': 'http://127.0.0.1:8000',
      '/poster-design-static': 'http://127.0.0.1:8000',
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})
