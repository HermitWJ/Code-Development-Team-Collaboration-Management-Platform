import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const THEME_KEY = 'collab_theme'

function apply(value) {
  document.documentElement.dataset.theme = value
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) {
    meta.setAttribute('content', value === 'light' ? '#F7F9FB' : '#0E1116')
  }
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref(localStorage.getItem(THEME_KEY) === 'light' ? 'light' : 'dark')

  function toggle() {
    mode.value = mode.value === 'dark' ? 'light' : 'dark'
  }

  function init() {
    apply(mode.value)
  }

  watch(mode, (value) => {
    localStorage.setItem(THEME_KEY, value)
    apply(value)
  })

  init()
  return { mode, toggle, init }
})
