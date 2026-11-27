<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { codeApi } from '../../api/code'
import { repoLinks } from '../../config/constants'
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
const loading = ref(false)
const error = ref('')
const editingId = ref(null)
const busy = ref(false)
const formError = ref('')

const emptyForm = () => ({
  name: '', slug: '', repo_url: '', main_branch: 'main',
  local_repo_path: '', description: '',
})
const form = ref(emptyForm())

async function load() {
  if (!teamId.value) return
  loading.value = true
  try {
    projects.value = await codeApi.projects(teamId.value)
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => team.epoch, load)

function links(row) {
  return repoLinks(row.repo_url, row.main_branch)
}

function startEdit(row) {
  editingId.value = row.id
  form.value = {
    name: row.name,
    slug: row.slug,
    repo_url: row.repo_url || '',
    main_branch: row.main_branch || 'main',
    local_repo_path: row.local_repo_path || '',
    description: row.description || '',
  }
  formError.value = ''
}

function resetForm() {
  editingId.value = null
  form.value = emptyForm()
  formError.value = ''
}

async function refreshProjectContext() {
  await project.loadProjects(teamId.value)
}

async function submit() {
  if (!form.value.name.trim() || (!editingId.value && !form.value.slug.trim())) {
    formError.value = '请填写项目名与项目标识'
    return
  }
  busy.value = true
  formError.value = ''
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      repo_url: form.value.repo_url.trim(),
      main_branch: form.value.main_branch.trim() || 'main',
      local_repo_path: form.value.local_repo_path.trim(),
    }
    if (editingId.value) {
      delete payload.slug
      await codeApi.updateProject(teamId.value, editingId.value, payload)
      toast.notify('项目已保存')
    } else {
      await codeApi.createProject(teamId.value, payload)
      toast.notify('项目已创建')
    }
    resetForm()
    await load()
    await refreshProjectContext()
  } catch (err) {
    formError.value = err.message
  } finally {
    busy.value = false
  }
}

async function remove(row) {
  if (
    !window.confirm(
      `确定删除项目「${row.name}」吗？项目下的 commit 记录会一并删除，需求单会解除项目归属。`
    )
  ) return
  try {
    await codeApi.removeProject(teamId.value, row.id)
    await load()
    await refreshProjectContext()
    toast.notify(`项目 ${row.slug} 已删除`)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  }
}

function viewStories(row) {
  project.switchProject(row.id)
  router.push({
    name: 'stories',
    params: { teamId: teamId.value },
    query: { project_id: row.id },
  })
}

function viewCommits(row) {
  project.switchProject(row.id)
  router.push({
    name: 'code-commits',
    params: { teamId: teamId.value },
    query: { project_id: row.id },
  })
}
</script>

<template>
  <div class="page">
    <div class="page__head">
      <div>
        <nav class="u-label page__crumb">协作平台 / 团队与项目管理 / 项目管理</nav>
        <h1 class="display">项目管理</h1>
        <p class="u-muted page__lead">
          一个团队下可以有多个项目；每个项目绑定自己的代码仓库与 main 基线分支，全站数据按当前项目隔离。
        </p>
      </div>
      <div class="page__head-right">
        <span class="u-label">项目数</span>
        <span class="u-num page__count">{{ projects.length }}</span>
      </div>
    </div>
    <div class="page__rule"></div>

    <div v-if="error" class="state-block">
      <div class="state-block__title">项目列表没能加载</div>
      <div class="state-block__desc">{{ error }}</div>
      <button class="btn" @click="load">重试加载</button>
    </div>

    <div class="grid">
      <div class="projects">
        <div v-if="!projects.length && !loading" class="card empty-card">
          <div class="state-block__title">还没有项目</div>
          <div class="field__hint">用右侧表单创建第一个项目，再绑定代码仓库。</div>
        </div>
        <section v-for="row in projects" :key="row.id" class="card project">
          <div class="card__head">
            <div>
              <h2 class="card__title">{{ row.name }}</h2>
              <span class="u-mono project__slug">{{ row.slug }}</span>
            </div>
            <span class="u-label">{{ row.story_count }} 需求 · {{ row.commit_count }} commit</span>
          </div>
          <p v-if="row.description" class="u-muted project__desc">{{ row.description }}</p>
          <div class="meta-grid">
            <div>
              <div class="meta-grid__key">代码仓库</div>
              <div class="meta-grid__value project__repo">
                <a v-if="links(row).repo" :href="links(row).repo" target="_blank" rel="noopener">
                  {{ row.repo_url }} ↗
                </a>
                <span v-else>{{ row.repo_url || '未绑定' }}</span>
              </div>
            </div>
            <div>
              <div class="meta-grid__key">main 基线分支</div>
              <div class="meta-grid__value">
                <a v-if="links(row).branch" :href="links(row).branch" target="_blank" rel="noopener"
                  class="u-mono">{{ row.main_branch }} ↗</a>
                <span v-else class="u-mono">{{ row.main_branch }}</span>
              </div>
            </div>
            <div class="meta-grid__full">
              <div class="meta-grid__key">本地仓库路径（可选，用于同步 commit）</div>
              <div class="meta-grid__value u-mono">{{ row.local_repo_path || '未配置' }}</div>
            </div>
          </div>
          <div class="card__actions">
            <button class="btn btn--sm" @click="viewStories(row)">查看需求单</button>
            <button class="btn btn--sm" @click="viewCommits(row)">查看提交</button>
            <template v-if="team.canManage">
              <button class="btn btn--sm" @click="startEdit(row)">编辑</button>
              <button class="btn btn--sm btn--danger" @click="remove(row)">删除</button>
            </template>
          </div>
        </section>
      </div>

      <section class="card form-card">
        <div class="card__head">
          <h2 class="card__title">{{ editingId ? '编辑项目' : '新建项目' }}</h2>
          <button v-if="editingId" class="btn btn--quiet btn--sm" @click="resetForm">取消编辑</button>
        </div>
        <div class="field">
          <label class="field__label">项目名 <em>*</em></label>
          <input v-model="form.name" class="underline-input" placeholder="例如：星河前端" />
        </div>
        <div class="field">
          <label class="field__label">项目标识 <em>*</em></label>
          <input
            v-model="form.slug"
            class="underline-input u-mono"
            placeholder="STAR-WEB"
            maxlength="32"
            :disabled="!!editingId"
          />
          <div class="field__hint">创建后不可修改；字母、数字、点、下划线与短横线</div>
        </div>
        <div class="field">
          <label class="field__label">代码仓库地址</label>
          <input
            v-model="form.repo_url"
            class="underline-input u-mono"
            placeholder="https://github.com/org/repo.git"
          />
        </div>
        <div class="field">
          <label class="field__label">main 分支</label>
          <input v-model="form.main_branch" class="underline-input u-mono" placeholder="main" />
        </div>
        <div class="field">
          <label class="field__label">本地仓库路径（可选）</label>
          <input
            v-model="form.local_repo_path"
            class="underline-input u-mono"
            placeholder="D:/repos/star-web"
          />
          <div class="field__hint">配置后可在需求单详情按 main..开发分支 同步真实 commit</div>
        </div>
        <div class="field">
          <label class="field__label">说明</label>
          <input v-model="form.description" class="underline-input" placeholder="项目用途" />
        </div>
        <div v-if="formError" class="field__error">{{ formError }}</div>
        <div class="card__actions">
          <button v-if="team.canManage" class="btn btn--primary btn--sm" :disabled="busy" @click="submit">
            {{ busy ? '保存中…' : editingId ? '保存修改' : '＋ 创建项目' }}
          </button>
          <span v-else class="field__hint">只有创建者或管理员可以维护项目</span>
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
.page__count { font-size: var(--fs-h2); font-weight: 600; }
.page__rule { height: 2px; background: var(--line-base); margin-bottom: var(--space-8); }
.grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: var(--space-6); }
.projects { display: flex; flex-direction: column; gap: var(--space-6); }
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
  margin-bottom: var(--space-4);
}
.card__title { font-size: var(--fs-h2); line-height: var(--lh-h2); font-weight: 600; }
.card__actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-hair);
}
.project__slug { color: var(--ink-3); }
.project__desc { margin-bottom: var(--space-4); }
.project__repo { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project__repo a { color: var(--accent); }
.meta-grid__full { grid-column: 1 / -1; }
.form-card { align-self: start; }
.empty-card { padding: var(--space-8); }
@media (max-width: 992px) {
  .grid { grid-template-columns: 1fr; }
  .page__head { flex-direction: column; align-items: flex-start; }
}
</style>
