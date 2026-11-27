<script setup>
import { computed, ref } from 'vue'

import { storyApi } from '../../../api/story'
import { STATUS_GLYPHS, STATUS_LABELS, STATUS_TONES } from '../../../config/constants'
import { useToastStore } from '../../../stores/toast'

const props = defineProps({
  teamId: { type: Number, default: 0 },
  detail: { type: Object, default: null },
})
const emit = defineEmits(['updated', 'refresh'])

const toast = useToastStore()
const pending = ref(null)
const remark = ref('')
const busy = ref(false)

const actions = computed(() => props.detail?.available_actions || [])
const status = computed(() => props.detail?.status || '')

async function run(action, text) {
  if (!action || busy.value) return
  // 后端 require_remark 是唯一权威；前端再挡一次，回车也不能提交空理由
  if (action.require_remark && !(text || '').trim()) {
    toast.notify('请填写说明或原因', { tone: 'error' })
    return
  }
  busy.value = true
  try {
    const result = await storyApi.doTransition(props.teamId, props.detail.id, {
      action: action.action,
      version: props.detail.version,
      remark: text || '',
    })
    pending.value = null
    remark.value = ''
    emit('updated', result.story)
    toast.notify(
      `${STATUS_LABELS[result.from_status] || result.from_status} → ${STATUS_LABELS[result.to_status] || result.to_status}`
    )
  } catch (err) {
    if (err.code === 'VERSION_CONFLICT') {
      toast.notify('状态已被别人改过，正在刷新', { tone: 'error' })
      emit('refresh')
    } else {
      toast.notify(err.message, { tone: 'error' })
    }
  } finally {
    busy.value = false
  }
}

function choose(action) {
  if (action.require_remark) {
    pending.value = action
    remark.value = ''
  } else {
    run(action, '')
  }
}

function submitRemark() {
  run(pending.value, remark.value)
}
</script>

<template>
  <div class="trans">
    <div class="trans__current">
      <span class="u-label">当前状态</span>
      <span class="status-mark" :data-tone="STATUS_TONES[status] || 'idle'">
        {{ STATUS_GLYPHS[status] }} {{ STATUS_LABELS[status] || status }}
      </span>
      <span class="u-mono">v{{ detail?.version }}</span>
    </div>

    <div v-if="actions.length" class="trans__actions">
      <span class="u-label">可执行</span>
      <button
        v-for="action in actions"
        :key="action.action"
        class="btn btn--sm"
        :class="{ 'trans__action--remark': action.require_remark }"
        :disabled="busy"
        :title="`流转到 ${STATUS_LABELS[action.to_status] || action.to_status || ''}`"
        @click="choose(action)"
      >
        {{ action.label }}
        <span v-if="action.require_remark" class="trans__tag">需说明</span>
      </button>
    </div>
    <div v-else class="field__hint">
      当前状态没有可执行的操作（终态，或角色受限）。可用动作由后端返回。
    </div>
    <div class="field__hint">
      只有暂停 / 暂缓、验收不通过打回开发需要写明理由，其他步骤直接生效。
    </div>

    <div v-if="pending" class="trans__remark">
      <div class="field__label">{{ pending.label }} · 请填写说明或原因</div>
      <input
        v-model="remark"
        class="underline-input"
        placeholder="说明或原因"
        @keyup.enter="submitRemark"
      />
      <div class="trans__remark-actions">
        <button class="btn btn--quiet btn--sm" @click="pending = null">取消</button>
        <button
          class="btn btn--primary btn--sm"
          :disabled="busy || !remark.trim()"
          @click="submitRemark"
        >
          确认
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trans__current,
.trans__actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
}
.trans__current .u-mono {
  color: var(--ink-3);
  margin-left: auto;
}
.trans__action--remark {
  border-color: var(--status-pending-accept);
}
.trans__tag {
  font-size: 11px;
  color: var(--status-pending-accept);
}
.trans__remark {
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-hair);
}
.trans__remark-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-3);
}
</style>
