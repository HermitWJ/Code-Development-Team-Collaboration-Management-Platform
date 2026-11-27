<script setup>
import {
  PRIORITY_LABELS,
  STATUS_GLYPHS,
  STATUS_LABELS,
  STATUS_TONES,
} from '../../../config/constants'
import { useStoryStore } from '../../../stores/story'
import { useTeamStore } from '../../../stores/team'
import { useToastStore } from '../../../stores/toast'
import StoryProgress from './StoryProgress.vue'

const props = defineProps({ teamId: { type: Number, default: 0 } })
const emit = defineEmits(['reload', 'copy', 'delete'])

const story = useStoryStore()
const team = useTeamStore()
const toast = useToastStore()

async function open(row) {
  try {
    await story.openDetail(props.teamId, row.id)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  }
}
</script>

<template>
  <!-- 错误态：有原因，也有重试入口 -->
  <div v-if="story.error" class="state-block">
    <div class="state-block__title">需求列表没能加载</div>
    <div class="state-block__desc">{{ story.error }}</div>
    <button class="btn" @click="emit('reload')">重试加载</button>
  </div>

  <!-- 加载态：骨架行结构与真实表格对齐 -->
  <div v-else-if="story.loading && !story.ready">
    <div v-for="n in 6" :key="n" class="skeleton-row">
      <div class="skeleton-bar" style="width: 5%"></div>
      <div class="skeleton-bar" style="width: 11%"></div>
      <div class="skeleton-bar" style="width: 26%"></div>
      <div class="skeleton-bar" style="width: 8%"></div>
      <div class="skeleton-bar" style="width: 10%"></div>
      <div class="skeleton-bar" style="width: 8%"></div>
    </div>
  </div>

  <!-- 空态：一行说明 + 明确动作，不用插画 -->
  <div v-else-if="story.ready && !story.list.length" class="state-block">
    <div class="state-block__title">还没有需求单</div>
    <div class="state-block__desc">
      这个团队还没有需求单，或当前筛选条件下没有匹配结果。
    </div>
    <button class="btn btn--quiet" @click="emit('reload')">重新加载</button>
  </div>

  <div v-else class="table-wrap">
    <table class="data-table">
      <colgroup>
        <col style="width: 56px" />
        <col style="width: 108px" />
        <col style="width: 240px" />
        <col style="width: 80px" />
        <col style="width: 128px" />
        <col style="width: 88px" />
        <col style="width: 60px" />
        <col style="width: 100px" />
      </colgroup>
      <thead>
        <tr>
          <th class="num" scope="col">序号</th>
          <th scope="col">单号</th>
          <th scope="col">需求标题</th>
          <th scope="col">类型</th>
          <th scope="col">状态</th>
          <th scope="col">负责人</th>
          <th scope="col">优先</th>
          <th class="num" scope="col">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in story.list"
          :key="row.id"
          :class="{
            'is-selected': row.id === story.selectedId,
            'is-released': row.status === 'released',
          }"
          @click="open(row)"
        >
          <td class="num u-mono">{{ row.no_seq }}</td>
          <td class="u-mono">{{ row.story_no }}</td>
          <td>
            <span class="table-title">
              <button class="data-table__link data-table__title-btn" @click.stop="open(row)">
                {{ row.title }}
              </button>
              <span v-if="row.status === 'released'" class="done-badge">✓ 已完成</span>
            </span>
          </td>
          <td><span class="type-mark">{{ row.type }}</span></td>
          <td>
            <div class="status-cell">
              <span
                class="status-chip"
                :class="{ 'status-chip--released': row.status === 'released' }"
                :data-tone="STATUS_TONES[row.status] || 'planning'"
              >
                <span class="status-chip__glyph">{{ STATUS_GLYPHS[row.status] }}</span>
                {{ STATUS_LABELS[row.status] || row.status }}
              </span>
              <StoryProgress compact :status="row.status" />
            </div>
          </td>
          <td :class="{ 'empty-value': !row.assignee }">
            {{ row.assignee?.display_name || '—' }}
          </td>
          <td>{{ PRIORITY_LABELS[row.priority] || row.priority }}</td>
          <td class="num">
            <div class="data-table__ops">
              <button
                class="btn btn--quiet btn--sm"
                :aria-label="`复制 ${row.story_no} 的 commit 标题`"
                @click.stop="emit('copy', row.commit_title)"
              >
                复制
              </button>
              <button
                v-if="team.canManage"
                class="btn btn--quiet btn--sm btn--danger"
                :aria-label="`删除 ${row.story_no}`"
                @click.stop="emit('delete', row)"
              >
                删除
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.table-title .data-table__title-btn {
  flex: 1 1 auto;
  min-width: 0;
}
</style>
