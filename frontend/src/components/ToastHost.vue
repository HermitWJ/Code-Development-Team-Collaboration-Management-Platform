<script setup>
import { useToastStore } from '../stores/toast'

const store = useToastStore()

function runAction(item) {
  if (item.action?.onClick) item.action.onClick()
  store.dismiss(item.id)
}
</script>

<template>
  <div class="toast-host" aria-live="polite">
    <div
      v-for="item in store.items"
      :key="item.id"
      class="toast"
      :class="`toast--${item.tone}`"
    >
      <span>{{ item.message }}</span>
      <button v-if="item.action" class="btn btn--quiet btn--sm" @click="runAction(item)">
        {{ item.action.label }}
      </button>
      <button class="btn btn--quiet btn--sm" :aria-label="'关闭提示'" @click="store.dismiss(item.id)">
        ×
      </button>
    </div>
  </div>
</template>
