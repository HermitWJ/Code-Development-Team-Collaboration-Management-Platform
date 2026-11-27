<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { codeApi } from '../../api/code'
import { formatTime, repoLinks } from '../../config/constants'
import { useProjectStore } from '../../stores/project'
import { useTeamStore } from '../../stores/team'
import { useToastStore } from '../../stores/toast'

const route = useRoute()
const router = useRouter()
const team = useTeamStore()
const project = useProjectStore()
const toast = useToastStore()

const teamId = computed(() => Number(route.params.teamId) || 0)
const projects = ref([])
const commits = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  if (!teamId.value || !project.currentProjectId) {
    commits.value = []
    error.value = ''
    loading.value = false
    return
  }
  loading.value = true
  try {
    const [projectRows, commitRows] = await Promise.all([
      codeApi.projects(teamId.value),
      codeApi.commits(teamId.value, { project_id: project.currentProjectId }),
    ])
    projects.value = projectRows
    commits.value = commitRows.results || []
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => team.epoch, load)
watch(() => project.epoch, load)

const groups = computed(() => {
  const map = new Map()
  for (const row of commits.value) {
    if (!map.has(row.branch_name)) {
      map.set(row.branch_name, {
        branch: row.branch_name,
        base: row.base_branch,
        project_id: row.project,
        project_name: row.project_name,
        storyIds: new Map(),
        rows: [],
      })
    }
    const group = map.get(row.branch_name)
    group.rows.push(row)
    if (row.story) group.storyIds.set(row.story_no, row.story)
  }
  return [...map.values()]
    .map((group) => {
      const repo = projects.value.find((row) => row.id === group.project_id)
      return {
        ...group,
        stories: [...group.storyIds].map(([storyNo, id]) => ({ storyNo, id })),
        total: group.rows.length,
        additions: group.rows.reduce((sum, row) => sum + row.additions, 0),
        deletions: group.rows.reduce((sum, row) => sum + row.deletions, 0),
        files_changed: group.rows.reduce((sum, row) => sum + row.files_changed, 0),
        authors: new Set(group.rows.map((row) => row.author).filter(Boolean)).size,
        latest: group.rows
          .map((row) => row.committed_at)
          .filter(Boolean)
          .sort()
          .slice(-1)[0] || '',
        links: repoLinks(repo?.repo_url || '', group.branch, group.base),
      }
    })
    .sort((left, right) => left.branch.localeCompare(right.branch))
})

function viewCommits(branch) {
  router.push({
    name: 'code-commits',
    params: { teamId: teamId.value },
    query: { branch },
  })
}

function viewStory(storyId) {
  router.push({
    name: 'stories',
    params: { teamId: teamId.value },
    query: { story: storyId },
  })
}

function retry() {
  load().catch((err) => toast.notify(err.message, { tone: 'error' }))
}
</script>

<template>
  <div class="page">
    <div class="page__head">
      <div>
        <nav class="u-label page__crumb">协作平台 / 代码工程 / 分支查看</nav>
        <h1 class="display">分支查看</h1>
        <p class="u-muted page__lead">
          只展示当前项目下的开发分支，按相对 main 基线的新增提交汇总。
        </p>
      </div>
      <div class="page__head-right">
        <span class="u-label">当前项目</span>
        <span class="page__project">{{ project.currentProject?.name || '未选择' }}</span>
        <span class="u-label">分支数</span>
        <span class="u-num page__count">{{ groups.length }}</span>
      </div>
    </div>
    <div class="page__rule"></div>

    <div v-if="error" class="state-block">
      <div class="state-block__title">分支数据没能加载</div>
      <div class="state-block__desc">{{ error }}</div>
      <button class="btn" @click="retry">重试加载</button>
    </div>
    <div v-else-if="!project.currentProjectId" class="state-block">
      <div class="state-block__title">还没有选择项目</div>
      <div class="state-block__desc">请在顶部下拉选择项目，分支数据按项目隔离。</div>
    </div>
    <div v-else-if="loading && !groups.length" class="state-block">
      <div class="state-block__desc">正在汇总当前项目的开发分支…</div>
    </div>
    <div v-else-if="!groups.length" class="state-block">
      <div class="state-block__title">当前项目还没有分支提交记录</div>
      <div class="state-block__desc">
        在需求单上绑定开发分支并导入或同步 commit 后，这里会出现分支汇总。
      </div>
    </div>

    <div v-else class="branch-list">
      <section v-for="group in groups" :key="group.branch" class="card branch">
        <div class="card__head">
          <div>
            <h2 class="card__title u-mono">{{ group.branch }}</h2>
            <span class="u-label">基线 {{ group.base }} · 项目 {{ group.project_name }}</span>
          </div>
          <span class="u-label">{{ group.total }} commit</span>
        </div>

        <div class="kpi-row">
          <div><span class="u-label">新增行</span><span class="u-num kpi add">+{{ group.additions }}</span></div>
          <div><span class="u-label">删除行</span><span class="u-num kpi del">−{{ group.deletions }}</span></div>
          <div><span class="u-label">变更文件</span><span class="u-num kpi">{{ group.files_changed }}</span></div>
          <div><span class="u-label">参与作者</span><span class="u-num kpi">{{ group.authors }}</span></div>
          <div><span class="u-label">最近提交</span><span class="u-mono kpi">{{ formatTime(group.latest) }}</span></div>
        </div>

        <div v-if="group.stories.length" class="story-row">
          <span class="u-label">关联需求单</span>
          <button
            v-for="story in group.stories"
            :key="story.id"
            class="btn btn--quiet btn--sm u-mono"
            @click="viewStory(story.id)"
          >
            {{ story.storyNo }} ↗
          </button>
        </div>

        <div class="card__actions">
          <a v-if="group.links.branch" :href="group.links.branch" target="_blank" rel="noopener" class="btn btn--sm">
            打开分支 ↗
          </a>
          <a v-if="group.links.compare" :href="group.links.compare" target="_blank" rel="noopener" class="btn btn--sm">
            对比 {{ group.base }}...{{ group.branch }} ↗
          </a>
          <button class="btn btn--primary btn--sm" @click="viewCommits(group.branch)">查看提交</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: var(--maxw);
  margin: 0 auto;
  padding: var(--space-12) var(--margin) var(--space-16);
}
.page__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--gutter);
  padding-bottom: var(--space-8);
}
.page__crumb { margin-bottom: var(--space-4); }
.page__lead { margin-top: var(--space-2); }
.page__head-right { display: flex; align-items: center; gap: var(--space-3); }
.page__project { font-weight: 600; }
.page__count { font-size: var(--fs-h2); font-weight: 600; }
.page__rule { height: 2px; background: var(--line-base); margin-bottom: var(--space-8); }
.branch-list { display: flex; flex-direction: column; gap: var(--space-6); }
.card {
  border: 1px solid var(--line-base);
  background: var(--bg-surface);
  padding: var(--space-6);
}
.card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--line-hair);
}
.card__title { font-size: var(--fs-h2); line-height: var(--lh-h2); font-weight: 600; }
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-4);
  padding: var(--space-6) 0;
}
.kpi-row > div { display: flex; flex-direction: column; gap: var(--space-1); }
.kpi { font-size: 18px; line-height: 26px; font-weight: 600; }
.kpi.add { color: var(--status-released); }
.kpi.del { color: var(--signal-error); }
.story-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-top: 1px solid var(--line-hair);
}
.card__actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-hair);
}
.card__actions a { text-decoration: none; }
@media (max-width: 992px) {
  .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .page__head { flex-direction: column; align-items: flex-start; }
}
</style>
