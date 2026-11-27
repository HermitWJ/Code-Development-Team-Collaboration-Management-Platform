<script setup>
import { computed, ref, watch } from 'vue'

import { STATUS_OPTIONS } from '../../../config/constants'
import { useStoryStore } from '../../../stores/story'
import { useTeamStore } from '../../../stores/team'

defineProps({ teamId: { type: Number, default: 0 } })
const emit = defineEmits(['change'])

const story = useStoryStore()
const team = useTeamStore()

const TYPE_OPTIONS = [
  { value: '', label: '全部类型' },
  { value: 'feat', label: 'feat 新功能' },
  { value: 'fix', label: 'fix 缺陷修复' },
  { value: 'docs', label: 'docs 文档' },
  { value: 'refactor', label: 'refactor 重构' },
  { value: 'perf', label: 'perf 性能' },
  { value: 'test', label: 'test 测试' },
  { value: 'chore', label: 'chore 杂务' },
]
const PRIORITY_OPTIONS = [
  { value: '', label: '全部优先级' },
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
  { value: 'urgent', label: '紧急' },
]

const keyword = ref(story.filters.keyword)
let timer = null

watch(keyword, (value) => {
  window.clearTimeout(timer)
  timer = window.setTimeout(() => {
    if (value === story.filters.keyword) return
    story.setFilter('keyword', value)
    emit('change')
  }, 300)
})

watch(
  () => story.filters.keyword,
  (value) => {
    if (value !== keyword.value) keyword.value = value
  }
)

const employees = computed(() => team.members.map((row) => row.user))
const activeCount = computed(
  () =>
    Object.entries(story.filters).filter(
      ([key, value]) => key !== 'ordering' && key !== 'project_id' && value
    ).length
)

function update(key, event) {
  story.setFilter(key, event.target.value)
  emit('change')
}

function reset() {
  story.resetFilters()
  keyword.value = ''
  emit('change')
}
</script>

<template>
  <div class="filter">
    <select class="filter__control" :value="story.filters.status" @change="update('status', $event)">
      <option v-for="item in STATUS_OPTIONS" :key="item.value" :value="item.value">
        {{ item.label }}
      </option>
    </select>
    <select class="filter__control" :value="story.filters.type" @change="update('type', $event)">
      <option v-for="item in TYPE_OPTIONS" :key="item.value" :value="item.value">
        {{ item.label }}
      </option>
    </select>
    <select
      class="filter__control"
      :value="story.filters.assignee_id"
      @change="update('assignee_id', $event)"
    >
      <option value="">全部负责人</option>
      <option v-for="user in employees" :key="user.id" :value="user.id">
        {{ user.display_name }}
      </option>
    </select>
    <select
      class="filter__control"
      :value="story.filters.priority"
      @change="update('priority', $event)"
    >
      <option v-for="item in PRIORITY_OPTIONS" :key="item.value" :value="item.value">
        {{ item.label }}
      </option>
    </select>
    <input
      v-model="keyword"
      class="filter__search"
      type="search"
      placeholder="搜索标题或单号"
      aria-label="搜索标题或单号"
    />
    <button v-if="activeCount" class="btn btn--quiet btn--sm" @click="reset">
      清除 {{ activeCount }} 项
    </button>
  </div>
</template>

<style scoped>
.filter {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: var(--space-6);
  flex: 1;
}
.filter__control {
  appearance: none;
  border: 0;
  border-bottom: 1px solid var(--line-base);
  border-radius: 0;
  background: transparent;
  padding: var(--space-2) var(--space-6) var(--space-2) 0;
  font-size: var(--fs-body);
  color: var(--ink);
  background-image: linear-gradient(45deg, transparent 50%, var(--ink-2) 50%),
    linear-gradient(135deg, var(--ink-2) 50%, transparent 50%);
  background-position: calc(100% - 6px) 15px, calc(100% - 1px) 15px;
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
  transition: border-color var(--t-hover) var(--ease-standard);
}
.filter__control:hover,
.filter__control:focus {
  border-bottom-color: var(--ink);
}
.filter__search {
  border: 0;
  border-bottom: 1px solid var(--line-base);
  border-radius: 0;
  background: transparent;
  padding: var(--space-2) 0;
  min-width: 180px;
  flex: 1;
  font-size: var(--fs-body);
}
.filter__search:focus {
  outline: none;
  border-bottom: 2px solid var(--ink);
  padding-bottom: 7px;
}
.filter__search:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 3px;
}
</style>
