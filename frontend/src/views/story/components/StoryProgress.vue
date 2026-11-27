<script setup>
import { computed } from 'vue'

import {
  BRANCH_STATUSES,
  STATUS_LABELS,
  STATUS_STEPS,
  STATUS_TONES,
  formatTime,
} from '../../../config/constants'

const props = defineProps({
  status: { type: String, default: 'planning' },
  compact: { type: Boolean, default: false },
  transitions: { type: Array, default: () => [] },
})

const isBranch = computed(() => BRANCH_STATUSES.includes(props.status))
const tone = computed(() => STATUS_TONES[props.status] || 'planning')

// CSS 变量用连字符（--status-pending-test），状态枚举用下划线（pending_test）
const toneStyle = (value) => ({
  '--tone-color': `var(--status-${String(value).replaceAll('_', '-')})`,
})

// 旁路状态主线停在「进入旁路之前」的那一步，从流转记录反推，不猜
const branchFrom = computed(() => {
  if (!props.transitions.length) return 'planning'
  return props.transitions[props.transitions.length - 1].from_status || 'planning'
})

const currentIndex = computed(() => {
  const main = STATUS_STEPS.findIndex((step) => step.key === props.status)
  if (main >= 0) return main
  const from = STATUS_STEPS.findIndex((step) => step.key === branchFrom.value)
  return from >= 0 ? from : 0
})

function stateOf(index) {
  if (index < currentIndex.value) return 'is-done'
  if (index === currentIndex.value) return isBranch.value ? 'is-branch' : 'is-current'
  return ''
}

// 已经走过的步骤、以及发布后的最后一步，圆圈内显示勾
function isCompleteStep(index) {
  return (
    stateOf(index) === 'is-done' ||
    (props.status === 'released' && index === STATUS_STEPS.length - 1)
  )
}

// 每一步的时间只取自真实流转记录，没有就留白
function timeFor(key) {
  for (let i = props.transitions.length - 1; i >= 0; i -= 1) {
    if (props.transitions[i].to_status === key) {
      return formatTime(props.transitions[i].created_at)
    }
  }
  return ''
}

const branchReason = computed(() => {
  if (!props.transitions.length) return ''
  return props.transitions[props.transitions.length - 1].remark || ''
})

const label = computed(() => STATUS_LABELS[props.status] || props.status)
</script>

<template>
  <!-- 列表：五段迷你进度条，颜色与当前状态一致 -->
  <div
    v-if="compact"
    class="progress-mini"
    :style="toneStyle(tone)"
    :aria-label="`状态进度：${label}`"
  >
    <div class="progress-mini__segs">
      <span
        v-for="(step, index) in STATUS_STEPS"
        :key="step.key"
        class="progress-mini__seg"
        :class="stateOf(index)"
      ></span>
    </div>
    <span class="progress-mini__label" :data-tone="tone">{{ label }}</span>
  </div>

  <!-- 详情：五步五色 + 连续连线 + 每步时间 + 完成打勾 -->
  <div v-else class="progress-flow">
    <div class="progress-flow__steps">
      <div
        v-for="(step, index) in STATUS_STEPS"
        :key="step.key"
        class="progress-flow__step"
        :class="[stateOf(index), { 'is-complete': isCompleteStep(index) }]"
        :style="toneStyle(step.tone)"
      >
        <div class="progress-flow__dot">
          <span v-if="isCompleteStep(index)" class="progress-flow__check">✓</span>
        </div>
        <div class="progress-flow__name">{{ step.label }}</div>
        <div class="progress-flow__time">{{ timeFor(step.key) }}</div>
      </div>
    </div>
    <div v-if="isBranch" class="progress-flow__branch">
      旁路 · {{ label }}<span v-if="branchReason"> / {{ branchReason }}</span>
    </div>
  </div>
</template>
