import { defineStore } from 'pinia'
import { ref } from 'vue'

let seq = 0

export const useToastStore = defineStore('toast', () => {
  const items = ref([])

  function notify(message, { tone = 'info', action = null, timeout = 4200 } = {}) {
    const id = ++seq
    items.value.push({ id, message, tone, action })
    if (timeout) window.setTimeout(() => dismiss(id), timeout)
    return id
  }

  function dismiss(id) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  return { items, notify, dismiss }
})
