<script setup>
import { ref } from 'vue'

import { copyText } from '../../../utils/clipboard'

const props = defineProps({ text: { type: String, default: '' } })

const copied = ref(false)
const failed = ref(false)
let timer = null

async function copy() {
  const ok = await copyText(props.text)
  failed.value = !ok
  if (!ok) return
  copied.value = true
  window.clearTimeout(timer)
  timer = window.setTimeout(() => {
    copied.value = false
  }, 1600)
}

function selectAll(event) {
  event.target.select()
}
</script>

<template>
  <div class="commit-bar">
    <div class="commit-bar__head">
      <span class="u-label">commit 标题</span>
      <button class="btn btn--quiet btn--sm" :disabled="!text" @click="copy">
        {{ copied ? '已复制' : '复制标题' }}
      </button>
    </div>
    <div v-if="!failed" class="commit-bar__text">{{ text }}</div>
    <input
      v-else
      class="underline-input u-mono"
      :value="text"
      readonly
      @focus="selectAll"
    />
    <div v-if="failed" class="field__hint" style="margin-top: var(--space-2)">
      浏览器不允许自动复制，已把标题放进输入框，请手动选中复制。
    </div>
  </div>
</template>
