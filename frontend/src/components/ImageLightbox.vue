<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

const url = ref('')

function onDocumentClick(event) {
  const target = event.target
  if (!(target instanceof HTMLImageElement)) return
  // 编辑区里的图片要可选中、可调整，不拦截；只放大查看态的富文本图片
  if (target.closest('[contenteditable="true"]')) return
  if (!target.closest('.rich-content')) return
  url.value = target.currentSrc || target.src
}

function onKeydown(event) {
  if (event.key === 'Escape') url.value = ''
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick, true)
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick, true)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="url" class="lightbox" @click="url = ''">
      <button type="button" class="lightbox__close" @click.stop="url = ''">关闭 ×</button>
      <img :src="url" alt="放大查看" @click.stop />
    </div>
  </Teleport>
</template>

<style scoped>
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  background: rgba(4, 7, 10, 0.9);
}
.lightbox img {
  max-width: 92vw;
  max-height: 86vh;
  object-fit: contain;
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.lightbox__close {
  position: absolute;
  top: var(--space-4);
  right: var(--space-6);
  padding: var(--space-2) var(--space-4);
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: transparent;
  color: #FFFFFF;
  font-size: var(--fs-body);
}
.lightbox__close:hover {
  border-color: #FFFFFF;
}
</style>
