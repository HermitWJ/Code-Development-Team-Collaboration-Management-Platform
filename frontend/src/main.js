import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/base.css'
import './styles/components.css'

// 在任何组件挂载前应用主题，避免浅色模式刷新时闪一下深色
const savedTheme = localStorage.getItem('collab_theme') === 'light' ? 'light' : 'dark'
document.documentElement.dataset.theme = savedTheme
const themeMeta = document.querySelector('meta[name="theme-color"]')
if (themeMeta) {
  themeMeta.setAttribute('content', savedTheme === 'light' ? '#F7F9FB' : '#0E1116')
}

createApp(App).use(createPinia()).use(router).mount('#app')
