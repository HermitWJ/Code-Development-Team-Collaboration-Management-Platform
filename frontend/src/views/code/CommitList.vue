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
const rows = ref([])
const summary = ref({ total: 0, additions: 0, deletions: 0, files_changed: 0, authors: 0, branches: 0 })
const projects = ref([])
const loading = ref(false)
const error = ref('')
const filters = ref({ branch: '', keyword: '' })
const busy = ref(false)
const importOpen = ref(false)
const importForm = ref({
  story_id: '',
  branch_name: '',
  base_branch: '',
  raw: '',
})

const branches = computed(() => [
  ...new Set(rows.value.map((row) => row.branch_name).filter(Boolean)),
].sort())

async function load() {
  if (!teamId.value) return
  loading.value = true
  try {
    const [data, projectRows] = await Promise.all([
      codeApi.commits(teamId.value, {
        ...filters.value,
        project_id: project.currentProjectId || 0,
      }),
      codeApi.projects(teamId.value),
    ])
    rows.value = data.results || []
    summary.value = data.summary || summary.value
    projects.value = projectRows
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  filters.value.branch = route.query.branch || ''
  load()
})
watch(() => team.epoch, load)
watch(() => project.epoch, load)
watch(
  () => route.query.branch,
  (branch) => {
    filters.value.branch = branch || ''
    load()
  }
)

function projectRepo(row) {
  const found = projects.value.find((item) => item.id === row.project)
  return found?.repo_url || ''
}

function commitLink(row) {
  if (row.url) return row.url
  return repoLinks(projectRepo(row), '', '', row.sha).commit
}

function openDetail(row) {
  router.push({
    name: 'code-commit-detail',
    params: { teamId: teamId.value, sha: row.sha },
  })
}

function openStory(row) {
  if (!row.story) return
  router.push({
    name: 'stories',
    params: { teamId: teamId.value },
    query: { story: row.story },
  })
}

async function importRows() {
  if (!project.currentProjectId) {
    toast.notify('请先在顶部选择项目', { tone: 'error' })
    return
  }
  let commits
  try {
    commits = JSON.parse(importForm.value.raw || '[]')
  } catch {
    toast.notify('commit JSON 格式不正确', { tone: 'error' })
    return
  }
  if (!Array.isArray(commits) || !commits.length) {
    toast.notify('请填写至少一条 commit 记录', { tone: 'error' })
    return
  }
  if (!importForm.value.branch_name.trim()) {
    toast.notify('请填写开发分支名', { tone: 'error' })
    return
  }
  busy.value = true
  try {
    const result = await codeApi.importCommits(teamId.value, {
      project_id: project.currentProjectId,
      story_id: Number(importForm.value.story_id) || null,
      branch_name: importForm.value.branch_name.trim(),
      base_branch: importForm.value.base_branch.trim(),
      commits,
    })
    toast.notify(`导入完成，新增 ${result.created} 条 commit`)
    importForm.value.raw = ''
    await load()
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  } finally {
    busy.value = false
  }
}

async function syncFromLocal() {
  if (!importForm.value.story_id) {
    toast.notify('请填写需求单 ID 后再同步', { tone: 'error' })
    return
  }
  busy.value = true
  try {
    const result = await codeApi.syncBranch(teamId.value, {
      story_id: Number(importForm.value.story_id),
      branch_name: importForm.value.branch_name.trim(),
    })
    toast.notify(`同步完成，新增 ${result.created} 条 commit`)
    await load()
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page__head">
      <div>
        <nav class="u-label page__crumb">协作平台 / 代码工程 / 代码提交</nav>
        <h1 class="display">代码提交</h1>
        <p class="u-muted page__lead">
          只展示当前项目下的提交记录；点短 SHA 进入 commit 详情。
        </p>
      </div>
      <div class="page__head-right">
        <span class="u-label">当前项目</span>
        <span class="page__project">{{ project.currentProject?.name || '未选择' }}</span>
        <button class="btn btn--sm" @click="load">刷新</button>
        <button v-if="team.canManage" class="btn btn--primary btn--sm" @click="importOpen = !importOpen">
          {{ importOpen ? '收起导入' : '导入 / 同步' }}
        </button>
      </div>
    </div>
    <div class="page__rule"></div>

    <div class="kpi-grid">
      <div><span class="u-label">提交数</span><span class="u-num kpi">{{ summary.total }}</span></div>
      <div><span class="u-label">新增行</span><span class="u-num kpi add">+{{ summary.additions }}</span></div>
      <div><span class="u-label">删除行</span><span class="u-num kpi del">−{{ summary.deletions }}</span></div>
      <div><span class="u-label">变更文件</span><span class="u-num kpi">{{ summary.files_changed }}</span></div>
      <div><span class="u-label">参与作者</span><span class="u-num kpi">{{ summary.authors }}</span></div>
      <div><span class="u-label">开发分支</span><span class="u-num kpi">{{ summary.branches }}</span></div>
    </div>

    <section v-if="importOpen && team.canManage" class="card import-card">
      <div class="card__head">
        <h2 class="card__title">导入 / 同步 commit</h2>
        <span class="u-label">写入当前项目：{{ project.currentProject?.slug || '未选择' }}</span>
      </div>
      <div class="import-grid">
        <input v-model="importForm.story_id" class="underline-input" placeholder="需求单 ID（可选）" />
        <input v-model="importForm.branch_name" class="underline-input u-mono" placeholder="开发分支 feature/…" />
        <input v-model="importForm.base_branch" class="underline-input u-mono" placeholder="基线分支（默认项目 main）" />
      </div>
      <textarea
        v-model="importForm.raw"
        class="underline-textarea import-json u-mono"
        placeholder='[{"sha":"…","title":"feat: …","author":"zhangsan","additions":40,"deletions":5,"files_changed":3}]'
      ></textarea>
      <div class="field__hint">
        按 (项目, 分支, SHA) 去重；同步按钮会读取项目配置的本地仓库，按 main..开发分支 生成记录。
      </div>
      <div class="card__actions">
        <button class="btn btn--sm" :disabled="busy" @click="syncFromLocal">从本地仓库同步</button>
        <button class="btn btn--primary btn--sm" :disabled="busy" @click="importRows">导入 commit</button>
      </div>
    </section>

    <div class="filter-row">
      <select v-model="filters.branch" class="underline-select" @change="load">
        <option value="">全部分支</option>
        <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
      </select>
      <input
        v-model="filters.keyword"
        class="underline-input"
        placeholder="搜索标题 / SHA / 作者"
        @keyup.enter="load"
      />
      <button class="btn btn--sm" @click="load">筛选</button>
    </div>

    <div v-if="error" class="state-block">
      <div class="state-block__title">提交记录没能加载</div>
      <div class="state-block__desc">{{ error }}</div>
      <button class="btn" @click="load">重试加载</button>
    </div>
    <div v-else-if="!project.currentProjectId" class="state-block">
      <div class="state-block__title">还没有选择项目</div>
      <div class="state-block__desc">请在顶部下拉选择项目，提交记录按项目隔离。</div>
    </div>
    <div v-else-if="loading && !rows.length" class="state-block">
      <div class="state-block__desc">正在读取当前项目的 commit 记录…</div>
    </div>
    <div v-else-if="!rows.length" class="state-block">
      <div class="state-block__title">当前项目没有提交记录</div>
      <div class="state-block__desc">调整筛选条件，或先在上方导入 / 同步 commit。</div>
    </div>

    <div v-else class="table-wrap">
      <table class="data-table commit-table">
        <thead>
          <tr>
            <th scope="col">SHA</th>
            <th scope="col">提交标题</th>
            <th scope="col">开发分支</th>
            <th scope="col">需求单</th>
            <th scope="col">作者</th>
            <th scope="col">提交时间</th>
            <th class="num" scope="col">变更</th>
            <th class="num" scope="col">外链</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>
              <button class="sha-btn u-mono" @click="openDetail(row)">{{ row.short_sha }}</button>
            </td>
            <td><span class="commit-title" :title="row.title">{{ row.title }}</span></td>
            <td><span class="u-mono branch-cell">{{ row.branch_name }}</span></td>
            <td>
              <button v-if="row.story_no" class="btn btn--quiet btn--sm u-mono" @click="openStory(row)">
                {{ row.story_no }} ↗
              </button>
              <span v-else class="u-label">—</span>
            </td>
            <td>{{ row.author || '—' }}</td>
            <td class="u-mono">{{ formatTime(row.committed_at) }}</td>
            <td class="num u-mono">
              <span class="add">+{{ row.additions }}</span> /
              <span class="del">−{{ row.deletions }}</span>
            </td>
            <td class="num">
              <a v-if="commitLink(row)" :href="commitLink(row)" target="_blank" rel="noopener"
                class="btn btn--quiet btn--sm">仓库 ↗</a>
            </td>
          </tr>
        </tbody>
      </table>
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
.page__rule { height: 2px; background: var(--line-base); margin-bottom: var(--space-8); }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  border: 1px solid var(--line-base);
  margin-bottom: var(--space-6);
}
.kpi-grid > div {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3) var(--space-4);
  border-right: 1px solid var(--line-hair);
}
.kpi-grid > div:last-child { border-right: 0; }
.kpi { font-size: 22px; line-height: 30px; font-weight: 600; }
.add { color: var(--status-released); }
.del { color: var(--signal-error); }
.card {
  border: 1px solid var(--line-base);
  background: var(--bg-surface);
  padding: var(--space-6);
  margin-bottom: var(--space-6);
}
.card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--line-hair);
  margin-bottom: var(--space-4);
}
.card__title { font-size: var(--fs-h2); line-height: var(--lh-h2); font-weight: 600; }
.card__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}
.import-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.import-json { min-height: 96px; font-size: var(--fs-mono); }
.filter-row {
  display: flex;
  align-items: flex-end;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}
.filter-row .underline-select { max-width: 220px; }
.commit-table { min-width: 1000px; }
.commit-table tbody td { height: 48px; }
.sha-btn {
  padding: 0;
  border: 0;
  border-bottom: 1px solid transparent;
  background: transparent;
  color: var(--accent);
}
.sha-btn:hover { border-bottom-color: var(--accent); }
.commit-title { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.branch-cell { font-size: 11px; color: var(--ink-2); }
@media (max-width: 992px) {
  .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .import-grid { grid-template-columns: 1fr; }
  .page__head { flex-direction: column; align-items: flex-start; }
  .filter-row { flex-wrap: wrap; }
}
</style>
