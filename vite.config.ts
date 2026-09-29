import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // 避开 poster-design 前端占用的 5173
    port: 5174,
    proxy: {
      // 后端有两套前缀：/api/* 是 AI、上传、用户、后台；/design/* 是模板素材作品
      '/api': { target: 'http://127.0.0.1:7001', changeOrigin: true },
      '/design': { target: 'http://127.0.0.1:7001', changeOrigin: true },
      // 上传与抠图结果都以相对路径 /static/... 返回，必须代理过去
      '/static': { target: 'http://127.0.0.1:7001', changeOrigin: true },
    },
  },
})
