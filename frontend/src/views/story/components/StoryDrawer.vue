<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { codeApi } from '../../../api/code'
import { storyApi } from '../../../api/story'
import {
  PRIORITY_LABELS,
  STATUS_GLYPHS,
  STATUS_LABELS,
  STATUS_TONES,
  STORY_TYPES,
  formatTime,
} from '../../../config/constants'
import { useStoryStore } from '../../../stores/story'
import { useTeamStore } from '../../../stores/team'
import { useToastStore } from '../../../stores/toast'
import CommitTitleBar from './CommitTitleBar.vue'
import RichTextEditor from './RichTextEditor.vue'
import StoryProgress from './StoryProgress.vue'
import TransitionPanel from './TransitionPanel.vue'

const props = defineProps({ teamId: { type: Number, default: 0 } })
const emit = defineEmits(['reload'])

const router = useRouter()
const story = useStoryStore()
const team = useTeamStore()
const toast = useToastStore()

const detail = computed(() => story.detail)
const branchSummary = computed(() => detail.value?.branch_summary || null)
const editing = ref(false)
const saving = ref(false)
const editError = ref('')
const editForm = ref({})
const projects = ref([])

const members = computed(() => team.members.map((row) => row.user))
const transitions = computed(() => (detail.value?.transitions || []).slice().reverse())

async function loadProjects() {
  if (!props.teamId) return
  try {
    projects.value = await codeApi.projects(props.teamId)
  } catch {
    projects.value = []
  }
}

onMounted(loadProjects)
watch(() => team.epoch, loadProjects)

watch(
  () => story.selectedId,
  () => {
    editing.value = false
    editError.value = ''
  }
)

function startEdit() {
  editError.value = ''
  editForm.value = {
    type: detail.value.type,
    title: detail.value.title,
    description: detail.value.description || '',
    assignee_id: detail.value.assignee?.id || '',
    priority: detail.value.priority,
    project_id: detail.value.project?.id || '',
    branch_name: detail.value.branch_name || '',
  }
  editing.value = true
}

async function saveEdit() {
  if (!editForm.value.title.trim()) {
    editError.value = '标题不能为空'
    return
  }
  saving.value = true
  editError.value = ''
  try {
    const updated = await storyApi.update(props.teamId, detail.value.id, {
      version: detail.value.version,
      type: editForm.value.type,
      title: editForm.value.title.trim(),
      description: editForm.value.description,
      assignee_id: editForm.value.assignee_id || null,
      priority: editForm.value.priority,
      project_id: editForm.value.project_id || null,
      branch_name: editForm.value.branch_name.trim(),
    })
    story.applyDetail(updated)
    editing.value = false
    emit('reload')
    await refreshDetail()
    toast.notify('需求单已保存')
  } catch (err) {
    editError.value = err.message
    if (err.code === 'VERSION_CONFLICT') refreshDetail()
  } finally {
    saving.value = false
  }
}

function onUpdated(payload) {
  story.applyDetail(payload)
  emit('reload')
}

async function refreshDetail() {
  if (!story.selectedId) return
  try {
    await story.openDetail(props.teamId, story.selectedId)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  }
}

async function removeCurrent() {
  if (!detail.value) return
  const storyNo = detail.value.story_no
  if (!window.confirm(`确定删除 ${storyNo} 吗？删除后不可在列表中查看。`)) return
  try {
    await storyApi.remove(props.teamId, detail.value.id)
    story.closeDetail()
    emit('reload')
    toast.notify(`${storyNo} 已删除`)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  }
}

async function syncBranch() {
  if (!detail.value) return
  try {
    const result = await codeApi.syncBranch(props.teamId, {
      story_id: detail.value.id,
      branch_name: detail.value.branch_name,
    })
    toast.notify(`同步完成，新增 ${result.created} 条 commit`)
    await refreshDetail()
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  }
}

function openCommit(row) {
  router.push({
    name: 'code-commit-detail',
    params: { teamId: props.teamId, sha: row.sha },
  })
}
</script>

<template>
  <Transition name="panel">
    <div
      v-if="story.selectedId"
      class="overlay overlay--drawer"
      @click.self="story.closeDetail()"
    >
      <div class="drawer">
        <div class="drawer__head">
          <div>
            <div class="drawer__title">{{ detail?.story_no || '—' }}</div>
            <div class="drawer__sub">{{ detail?.title || '读取中' }}</div>
          </div>
          <div class="drawer__head-actions">
            <button
              v-if="detail && team.canManage"
              class="btn btn--quiet btn--sm btn--danger"
              @click="removeCurrent"
            >
              删除
            </button>
            <button class="btn btn--quiet btn--sm" @click="story.closeDetail()">关闭 ×</button>
          </div>
        </div>

        <div v-if="story.detailLoading" class="state-block">
          <div class="state-block__desc">正在读取需求单…</div>
        </div>

        <template v-else-if="detail">
          <div v-if="detail.status === 'released'" class="released-banner">
            <span class="released-banner__glyph">✓</span>
            <span>已完成 · 该需求单已发布，与进行中的工作区分开</span>
          </div>

          <div class="drawer__status">
            <span
              class="status-chip"
              :class="{ 'status-chip--released': detail.status === 'released' }"
              :data-tone="STATUS_TONES[detail.status] || 'planning'"
            >
              <span class="status-chip__glyph">{{ STATUS_GLYPHS[detail.status] }}</span>
              {{ STATUS_LABELS[detail.status] || detail.status }}
            </span>
            <span class="u-mono">v{{ detail.version }}</span>
            <span class="u-label">更新 {{ formatTime(detail.updated_at) }}</span>
          </div>

          <CommitTitleBar :text="detail.commit_title" />

          <section class="section">
            <div class="section__head">
              <span class="section__num">01</span>
              <h2 class="section__title">基本信息</h2>
              <span class="section__rule"></span>
              <button
                v-if="!editing"
                class="btn btn--quiet btn--sm section__edit"
                @click="startEdit"
              >
                编辑
              </button>
            </div>

            <div v-if="!editing" class="meta-grid">
              <div>
                <div class="meta-grid__key">需求类型</div>
                <div class="meta-grid__value type-mark">{{ detail.type }}</div>
              </div>
              <div>
                <div class="meta-grid__key">优先级</div>
                <div class="meta-grid__value">
                  {{ PRIORITY_LABELS[detail.priority] || detail.priority }}
                </div>
              </div>
              <div>
                <div class="meta-grid__key">负责人</div>
                <div class="meta-grid__value">{{ detail.assignee?.display_name || '—' }}</div>
              </div>
              <div>
                <div class="meta-grid__key">创建人</div>
                <div class="meta-grid__value">{{ detail.creator?.display_name || '—' }}</div>
              </div>
              <div>
                <div class="meta-grid__key">所属项目</div>
                <div class="meta-grid__value">
                  {{ detail.project ? `${detail.project.name} (${detail.project.slug})` : '—' }}
                </div>
              </div>
              <div>
                <div class="meta-grid__key">开发分支</div>
                <div class="meta-grid__value u-mono">
                  {{ detail.branch_name || '—' }}
                  <span v-if="detail.branch_name" class="u-label">基线 {{ detail.base_branch }}</span>
                </div>
              </div>
              <div class="meta-grid__full">
                <div class="meta-grid__key">说明</div>
                <!-- 服务端 bleach 已净化白名单，这里只渲染权威 HTML -->
                <div
                  v-if="detail.description"
                  class="meta-grid__value drawer__desc rich-content"
                  v-html="detail.description"
                ></div>
                <div v-else class="meta-grid__value drawer__desc">—</div>
              </div>
            </div>

            <form v-else @submit.prevent="saveEdit">
              <div class="field">
                <label class="field__label" for="edit-type">需求类型</label>
                <select id="edit-type" v-model="editForm.type" class="underline-select">
                  <option v-for="item in STORY_TYPES" :key="item.value" :value="item.value">
                    {{ item.label }}
                  </option>
                </select>
              </div>
              <div class="field">
                <label class="field__label" for="edit-title">标题</label>
                <input id="edit-title" v-model="editForm.title" class="underline-input" />
              </div>
              <div class="field">
                <div class="field__label">说明</div>
                <RichTextEditor v-model="editForm.description" :team-id="teamId" />
              </div>
              <div class="field">
                <label class="field__label" for="edit-project">所属项目</label>
                <select id="edit-project" v-model="editForm.project_id" class="underline-select">
                  <option value="">未指定</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.name }} ({{ project.slug }}) · {{ project.main_branch }}
                  </option>
                </select>
              </div>
              <div class="field">
                <label class="field__label" for="edit-branch">开发分支</label>
                <input
                  id="edit-branch"
                  v-model="editForm.branch_name"
                  class="underline-input u-mono"
                  placeholder="feature/STAR-1024（留空解绑）"
                />
                <div class="field__hint">绑定后自动以所选项目 main 分支作为基线</div>
              </div>
              <div class="meta-grid">
                <div>
                  <div class="field">
                    <label class="field__label" for="edit-assignee">负责人</label>
                    <select
                      id="edit-assignee"
                      v-model="editForm.assignee_id"
                      class="underline-select"
                    >
                      <option value="">未指定</option>
                      <option v-for="user in members" :key="user.id" :value="user.id">
                        {{ user.display_name }}
                      </option>
                    </select>
                  </div>
                </div>
                <div>
                  <div class="field">
                    <label class="field__label" for="edit-priority">优先级</label>
                    <select
                      id="edit-priority"
                      v-model="editForm.priority"
                      class="underline-select"
                    >
                      <option value="low">低</option>
                      <option value="medium">中</option>
                      <option value="high">高</option>
                      <option value="urgent">紧急</option>
                    </select>
                  </div>
                </div>
              </div>
              <div v-if="editError" class="field__error" style="margin-bottom: var(--space-4)">
                {{ editError }}
              </div>
              <div class="drawer__edit-actions">
                <button type="button" class="btn btn--quiet" @click="editing = false">取消</button>
                <button type="submit" class="btn btn--primary" :disabled="saving">
                  {{ saving ? '保存中…' : '保存' }}
                </button>
              </div>
            </form>
          </section>

          <section class="section">
            <div class="section__head">
              <span class="section__num">02</span>
              <h2 class="section__title">状态进展</h2>
              <span class="section__rule"></span>
            </div>
            <StoryProgress :status="detail.status" :transitions="detail.transitions || []" />
            <TransitionPanel
              :team-id="teamId"
              :detail="detail"
              @updated="onUpdated"
              @refresh="refreshDetail"
            />
          </section>

          <section class="section">
            <div class="section__head">
              <span class="section__num">03</span>
              <h2 class="section__title">分支与提交</h2>
              <span class="section__rule"></span>
              <button
                v-if="team.canManage && branchSummary?.branch_name"
                class="btn btn--quiet btn--sm section__edit"
                @click="syncBranch"
              >
                从本地仓库同步
              </button>
            </div>

            <div v-if="!branchSummary || !branchSummary.branch_name" class="field__hint">
              还没有绑定开发分支。点「编辑」选择项目并填写分支名，绑定后这里会显示相对 main 基线的新增提交。
            </div>
            <template v-else>
              <div class="branch-meta">
                <div>
                  <span class="meta-grid__key">开发分支</span>
                  <span class="u-mono">{{ branchSummary.branch_name }}</span>
                </div>
                <div>
                  <span class="meta-grid__key">基线分支</span>
                  <span class="u-mono">{{ branchSummary.base_branch }}</span>
                </div>
                <div>
                  <span class="meta-grid__key">项目</span>
                  <span>{{ branchSummary.project?.name || '—' }}</span>
                </div>
              </div>

              <div class="branch-kpis">
                <div><span class="u-label">新增提交</span><span class="u-num">{{ branchSummary.total }}</span></div>
                <div><span class="u-label">新增行</span><span class="u-num add">+{{ branchSummary.additions }}</span></div>
                <div><span class="u-label">删除行</span><span class="u-num del">−{{ branchSummary.deletions }}</span></div>
                <div><span class="u-label">变更文件</span><span class="u-num">{{ branchSummary.files_changed }}</span></div>
                <div>
                  <span class="u-label">作者 / 最近提交</span>
                  <span class="u-mono">{{ branchSummary.author_count }} · {{ formatTime(branchSummary.latest_commit_at) }}</span>
                </div>
              </div>

              <div class="branch-links">
                <a v-if="branchSummary.repo_links.repo" :href="branchSummary.repo_links.repo"
                  target="_blank" rel="noopener" class="btn btn--sm">打开仓库 ↗</a>
                <a v-if="branchSummary.repo_links.branch" :href="branchSummary.repo_links.branch"
                  target="_blank" rel="noopener" class="btn btn--sm">打开分支 ↗</a>
                <a v-if="branchSummary.repo_links.compare" :href="branchSummary.repo_links.compare"
                  target="_blank" rel="noopener" class="btn btn--sm">对比基线 ↗</a>
              </div>

              <div v-if="branchSummary.commits.length" class="commit-list">
                <button
                  v-for="row in branchSummary.commits"
                  :key="row.id"
                  class="commit-row"
                  @click="openCommit(row)"
                >
                  <span class="u-mono commit-row__sha">{{ row.short_sha }}</span>
                  <span class="commit-row__title">{{ row.title }}</span>
                  <span class="u-mono commit-row__stats">
                    <span class="add">+{{ row.additions }}</span>/<span class="del">−{{ row.deletions }}</span>
                  </span>
                  <span class="u-mono commit-row__time">{{ formatTime(row.committed_at) }}</span>
                  <span class="commit-row__go">详情 →</span>
                </button>
              </div>
              <div v-else class="field__hint">
                该分支还没有 commit 记录。可在「代码工程 / 代码提交」导入，或点上方按钮从本地仓库同步。
              </div>
            </template>
          </section>

          <section class="section">
            <div class="section__head">
              <span class="section__num">04</span>
              <h2 class="section__title">流转记录</h2>
              <span class="section__rule"></span>
            </div>
            <div v-if="transitions.length" class="timeline">
              <div v-for="row in transitions" :key="row.id" class="timeline__item">
                <div class="timeline__line">
                  {{ row.from_status_label || STATUS_LABELS[row.from_status] || row.from_status }}
                  → {{ row.to_status_label || STATUS_LABELS[row.to_status] || row.to_status }}
                </div>
                <div class="timeline__meta">
                  {{ row.operator?.display_name || '—' }} · {{ formatTime(row.created_at) }}
                  <span v-if="row.remark"> · {{ row.remark }}</span>
                </div>
              </div>
            </div>
            <div v-else class="field__hint">还没有流转记录，创建后默认落在「规划中」。</div>
          </section>
        </template>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.drawer__head-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 0 0 auto;
}
.released-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--status-released);
  background: color-mix(in srgb, var(--status-released) 10%, transparent);
  color: var(--status-released);
  font-size: var(--fs-body);
  font-weight: 600;
}
.released-banner__glyph {
  font-family: var(--font-mono);
  font-size: 16px;
}
.drawer__status {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}
.drawer__status .u-label {
  margin-left: auto;
}
.section__edit {
  margin-left: auto;
}
.meta-grid__full {
  grid-column: 1 / -1;
}
.drawer__desc {
  line-height: 1.7;
  color: var(--ink-2);
}
.drawer__edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-hair);
}
.branch-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
}
.branch-meta > div {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}
.branch-meta .u-mono {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.branch-kpis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-2);
  margin: var(--space-6) 0;
  padding: var(--space-4) 0;
  border-top: 1px solid var(--line-hair);
  border-bottom: 1px solid var(--line-hair);
}
.branch-kpis > div {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.branch-kpis .u-num { font-size: 18px; font-weight: 600; }
.branch-kpis .u-mono { font-size: 11px; }
.add { color: var(--status-released); }
.del { color: var(--signal-error); }
.branch-links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.branch-links a { text-decoration: none; }
.commit-list { border-top: 1px solid var(--line-base); }
.commit-row {
  display: grid;
  grid-template-columns: 64px 1fr 64px 88px 44px;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) 0;
  border: 0;
  border-bottom: 1px solid var(--line-hair);
  background: transparent;
  text-align: left;
  font-size: var(--fs-label);
}
.commit-row:hover { background: var(--bg-sunken); }
.commit-row__sha { color: var(--accent); }
.commit-row__title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.commit-row__stats, .commit-row__time { color: var(--ink-3); font-size: 11px; }
.commit-row__go { color: var(--ink-2); font-size: 11px; white-space: nowrap; }
@media (max-width: 992px) {
  .branch-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .branch-meta { grid-template-columns: 1fr; }
  .commit-row { grid-template-columns: 56px 1fr 56px; }
  .commit-row__time, .commit-row__go { display: none; }
}
</style>
