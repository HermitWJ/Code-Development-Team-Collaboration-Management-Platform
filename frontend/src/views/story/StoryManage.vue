<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { storyApi } from '../../api/story'
import { useProjectStore } from '../../stores/project'
import { useStoryStore } from '../../stores/story'
import { useTeamStore } from '../../stores/team'
import { useToastStore } from '../../stores/toast'
import { copyText } from '../../utils/clipboard'
import StoryCreateModal from './components/StoryCreateModal.vue'
import StoryDrawer from './components/StoryDrawer.vue'
import StoryFilter from './components/StoryFilter.vue'
import StoryTable from './components/StoryTable.vue'

const route = useRoute()
const story = useStoryStore()
const team = useTeamStore()
const project = useProjectStore()
const toast = useToastStore()

const teamId = computed(() => Number(route.params.teamId) || 0)
const createOpen = ref(false)

// 每次加载都把当前项目写进筛选条件；没有项目时用 0，后端返回空而不是全团队数据
function reload() {
  const projectId = project.currentProjectId || 0
  if (story.filters.project_id !== projectId) {
    story.filters.project_id = projectId
  }
  story.loadList(teamId.value)
}

watch(() => team.epoch, reload)
watch(() => project.epoch, reload)

onMounted(() => {
  // 兼容从项目卡片带来的链接：项目已在列表时同步顶部下拉
  const queryProjectId = Number(route.query.project_id) || 0
  if (queryProjectId && project.projects.some((row) => row.id === queryProjectId)) {
    project.switchProject(queryProjectId)
  }
  reload()
  const storyId = Number(route.query.story) || 0
  if (storyId) {
    story
      .openDetail(teamId.value, storyId)
      .catch((err) => toast.notify(err.message, { tone: 'error' }))
  }
})

function changePage(delta) {
  const next = story.page + delta
  if (next < 1 || (next - 1) * story.pageSize >= story.total) return
  story.setPage(next)
  reload()
}

const pageCount = computed(() => Math.max(1, Math.ceil(story.total / story.pageSize)))

function formatTime(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  return date.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  })
}

const lastUpdate = computed(() => {
  if (!story.list.length) return '—'
  const newest = story.list.reduce((a, b) =>
    a.updated_at > b.updated_at ? a : b
  )
  return formatTime(newest.updated_at)
})

async function doCopy(text) {
  if (!text) return
  const ok = await copyText(text)
  toast.notify(
    ok ? 'commit 标题已复制' : '复制失败，请在详情里手动选中标题',
    { tone: ok ? 'info' : 'error' }
  )
}

function onCreated(created) {
  createOpen.value = false
  reload()
  toast.notify(`已创建 ${created.story_no}`, {
    timeout: 8000,
    action: {
      label: '复制 commit 标题',
      onClick: () => doCopy(created.commit_title),
    },
  })
}

async function removeStory(row) {
  if (!window.confirm(`确定删除 ${row.story_no}「${row.title}」吗？\n删除后列表与详情都不再显示，历史流水保留。`)) {
    return
  }
  try {
    await storyApi.remove(teamId.value, row.id)
    if (story.selectedId === row.id) story.closeDetail()
    reload()
    toast.notify(`${row.story_no} 已删除`)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  }
}
</script>

<template>
  <div class="page">
    <div class="page__head">
      <div class="page__title-block">
        <nav class="page__crumb u-label" aria-label="面包屑">协作平台 / 项目管理 / 需求单</nav>
        <h1 class="display">需求单</h1>
        <p class="page__lead u-muted">当前项目下的需求单，找到那一单，看进度，复制提交标题。</p>
      </div>
      <div class="page__meta">
        <div class="page__meta-cell">
          <span class="u-label">当前项目</span>
          <span>{{ project.currentProject?.name || '未选择' }}</span>
        </div>
        <div class="page__meta-cell">
          <span class="u-label">需求总数</span>
          <span class="u-num page__meta-num">{{ story.total }}</span>
        </div>
        <div class="page__meta-cell">
          <span class="u-label">本页最近更新</span>
          <span class="u-mono">{{ lastUpdate }}</span>
        </div>
      </div>
    </div>
    <div class="page__rule"></div>

    <div class="page__toolbar">
      <StoryFilter :team-id="teamId" @change="reload" />
      <button class="btn btn--primary" @click="createOpen = true">＋ 新建需求单</button>
    </div>

    <StoryTable :team-id="teamId" @reload="reload" @copy="doCopy" @delete="removeStory" />

    <div class="page__pager">
      <span class="u-mono">{{ story.total }} 条 · 第 {{ story.page }} / {{ pageCount }} 页</span>
      <div class="page__pager-actions">
        <button class="btn btn--sm" :disabled="story.page <= 1" @click="changePage(-1)">上一页</button>
        <button
          class="btn btn--sm"
          :disabled="story.page >= pageCount"
          @click="changePage(1)"
        >
          下一页
        </button>
      </div>
    </div>

    <StoryCreateModal
      v-if="createOpen"
      :team-id="teamId"
      @close="createOpen = false"
      @created="onCreated"
    />
    <StoryDrawer :team-id="teamId" @reload="reload" />
  </div>
</template>

<style scoped>
.page {
  max-width: var(--maxw);
  margin: 0 auto;
  padding: var(--space-12) var(--margin) var(--space-16);
}
.page__head {
  display: grid;
  grid-template-columns: 8fr 4fr;
  gap: var(--gutter);
  align-items: end;
  padding-bottom: var(--space-8);
}
.page__crumb {
  margin-bottom: var(--space-4);
}
.page__lead {
  margin-top: var(--space-2);
}
.page__meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
  text-align: right;
}
.page__meta-cell {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  text-align: right;
  white-space: nowrap;
}
.page__meta-num {
  font-size: var(--fs-h2);
  line-height: var(--lh-h2);
}
.page__rule {
  height: 2px;
  background: var(--line-base);
  margin-bottom: var(--space-6);
}
.page__toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}
.page__pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--space-4);
  color: var(--ink-2);
}
.page__pager-actions {
  display: flex;
  gap: var(--space-2);
}
@media (max-width: 992px) {
  .page__head {
    grid-template-columns: 1fr;
  }
  .page__meta {
    text-align: left;
  }
  .page__meta-cell {
    text-align: left;
  }
  .page__toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
