import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import reveal from './directives/reveal'

// ── 字体（日式：霞鹜文楷 · 楷体） ──────────────────
import '@fontsource/lxgw-wenkai/500.css'
// 正文兜底：思源黑体（LXGW WenKai 缺字时回退）
import '@fontsource/noto-sans-sc/400.css'
import '@fontsource/noto-sans-sc/500.css'
import '@fontsource/noto-sans-sc/700.css'

import './styles/tokens.css'
import './styles/base.css'

createApp(App).use(router).directive('reveal', reveal).mount('#app')
