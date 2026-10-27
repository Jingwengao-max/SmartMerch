import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import reveal from './directives/reveal'

// 中文字体库：只打包浏览器实际使用的 WOFF2。
import './styles/fonts.css'

import './styles/tokens.css'
import './styles/base.css'

createApp(App).use(router).directive('reveal', reveal).mount('#app')
