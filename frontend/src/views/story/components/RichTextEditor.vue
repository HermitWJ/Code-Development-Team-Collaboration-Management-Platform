<script setup>
import { onMounted, ref, watch } from 'vue'

import { storyApi } from '../../../api/story'
import { useToastStore } from '../../../stores/toast'

const props = defineProps({
  modelValue: { type: String, default: '' },
  teamId: { type: Number, default: 0 },
  placeholder: {
    type: String,
    default: '写下背景、范围、验收口径，可插入图片或视频',
  },
})
const emit = defineEmits(['update:modelValue'])

const editor = ref(null)
const imageInput = ref(null)
const videoInput = ref(null)
const uploading = ref(false)
const toast = useToastStore()
let savedRange = null

const TOOLS = [
  { label: '正文', title: '正文段落', cmd: 'formatBlock', value: 'p' },
  { label: 'H2', title: '二级标题', cmd: 'formatBlock', value: 'h2' },
  { label: 'H3', title: '三级标题', cmd: 'formatBlock', value: 'h3' },
  { label: 'B', title: '加粗', cmd: 'bold' },
  { label: 'I', title: '斜体', cmd: 'italic' },
  { label: 'U', title: '下划线', cmd: 'underline' },
  { label: 'S', title: '删除线', cmd: 'strikeThrough' },
  { label: '≡', title: '无序列表', cmd: 'insertUnorderedList' },
  { label: '1.', title: '有序列表', cmd: 'insertOrderedList' },
  { label: '❝', title: '引用', cmd: 'formatBlock', value: 'blockquote' },
  { label: '—', title: '分割线', cmd: 'insertHorizontalRule' },
  { label: '↶', title: '撤销', cmd: 'undo' },
  { label: '↷', title: '重做', cmd: 'redo' },
  { label: '⌫', title: '清除格式', cmd: 'removeFormat' },
]

function rememberSelection() {
  const selection = window.getSelection()
  if (
    selection &&
    selection.rangeCount &&
    editor.value?.contains(selection.anchorNode)
  ) {
    savedRange = selection.getRangeAt(0).cloneRange()
  }
}

function restoreSelection() {
  if (!editor.value) return
  editor.value.focus()
  const selection = window.getSelection()
  selection.removeAllRanges()
  if (savedRange) {
    selection.addRange(savedRange)
    return
  }
  const range = document.createRange()
  range.selectNodeContents(editor.value)
  range.collapse(false)
  selection.addRange(range)
}

function sync() {
  if (editor.value) emit('update:modelValue', editor.value.innerHTML)
}

function exec(command, value = null) {
  restoreSelection()
  document.execCommand(command, false, value)
  sync()
  rememberSelection()
}

function insertHtml(html) {
  restoreSelection()
  document.execCommand('insertHTML', false, html)
  sync()
  rememberSelection()
}

function addLink() {
  const url = window.prompt('输入链接地址（http/https）')
  if (!url || !/^https?:\/\//i.test(url)) return
  exec('createLink', url)
}

async function pickFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!props.teamId) {
    toast.notify('请先选择团队', { tone: 'error' })
    return
  }
  uploading.value = true
  try {
    const result = await storyApi.uploadMedia(props.teamId, file)
    const url = String(result.url).replace(/"/g, '&quot;')
    insertHtml(
      result.kind === 'video'
        ? `<video src="${url}" controls></video><p><br></p>`
        : `<img src="${url}" alt="说明配图"><p><br></p>`
    )
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  if (editor.value) editor.value.innerHTML = props.modelValue || ''
})

watch(
  () => props.modelValue,
  (value) => {
    if (editor.value && editor.value.innerHTML !== (value || '')) {
      editor.value.innerHTML = value || ''
    }
  }
)
</script>

<template>
  <div class="rich-editor">
    <div class="rich-editor__toolbar">
      <button
        v-for="tool in TOOLS"
        :key="tool.label"
        type="button"
        class="rich-editor__tool"
        :title="tool.title"
        @mousedown.prevent
        @click="exec(tool.cmd, tool.value)"
      >
        {{ tool.label }}
      </button>
      <span class="rich-editor__sep"></span>
      <button type="button" class="rich-editor__tool" title="插入链接" @mousedown.prevent @click="addLink">
        链接
      </button>
      <button
        type="button"
        class="rich-editor__tool"
        title="上传图片"
        :disabled="uploading"
        @mousedown.prevent
        @click="imageInput?.click()"
      >
        图片
      </button>
      <button
        type="button"
        class="rich-editor__tool"
        title="上传视频"
        :disabled="uploading"
        @mousedown.prevent
        @click="videoInput?.click()"
      >
        视频
      </button>
    </div>

    <div
      ref="editor"
      class="rich-editor__body rich-content"
      contenteditable="true"
      :data-placeholder="placeholder"
      @input="sync"
      @blur="rememberSelection"
      @keyup="rememberSelection"
      @mouseup="rememberSelection"
    ></div>

    <input
      ref="imageInput"
      type="file"
      accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
      hidden
      @change="pickFile"
    />
    <input
      ref="videoInput"
      type="file"
      accept="video/mp4,video/webm,video/quicktime,video/x-m4v"
      hidden
      @change="pickFile"
    />

    <div class="rich-editor__foot">
      <span>{{ uploading ? '正在上传…' : '支持标题、列表、引用、链接，以及图片 / 视频' }}</span>
      <span>图片 ≤ 10MB · 视频 ≤ 100MB</span>
    </div>
  </div>
</template>
