<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { teamApi } from '../api/team'
import { ASSIGNABLE_ROLES, ROLE_LABELS } from '../config/constants'
import { useTeamStore } from '../stores/team'
import { useToastStore } from '../stores/toast'

const route = useRoute()
const router = useRouter()
const team = useTeamStore()
const toast = useToastStore()

const teamId = computed(() => Number(route.params.teamId) || 0)
const current = computed(
  () => team.teams.find((item) => item.id === teamId.value) || null
)
const isOwner = computed(() => team.myRole === 'owner')
const canManage = computed(() => team.canManage)
const canOpenRepo = computed(() =>
  /^https?:\/\//i.test(settingsForm.value.git_repo_url || '')
)

const createForm = ref({ name: '', slug: '', git_repo_url: '' })
const createError = ref('')
const createBusy = ref(false)
const settingsForm = ref({ name: '', git_repo_url: '' })
const settingsBusy = ref(false)
const keyword = ref('')
const candidates = ref([])
const roleToAdd = ref('member')
const busyId = ref(null)

function fillSettings() {
  settingsForm.value = {
    name: current.value?.name || '',
    git_repo_url: current.value?.git_repo_url || '',
  }
}

async function refreshAll() {
  await team.loadTeams().catch(() => {})
  await team.refreshMembers().catch(() => {})
  fillSettings()
}

onMounted(refreshAll)
watch(() => team.epoch, refreshAll)

async function createTeam() {
  createError.value = ''
  if (!createForm.value.name.trim() || !createForm.value.slug.trim()) {
    createError.value = '请填写团队名与单号前缀'
    return
  }
  createBusy.value = true
  try {
    const created = await teamApi.create({
      name: createForm.value.name.trim(),
      slug: createForm.value.slug.trim().toUpperCase(),
      git_repo_url: createForm.value.git_repo_url.trim(),
    })
    createForm.value = { name: '', slug: '', git_repo_url: '' }
    await team.loadTeams()
    await team.switchTeam(created.id, { reload: false })
    router.push({ name: 'team-settings', params: { teamId: created.id } })
    toast.notify(`已创建团队 ${created.name}`)
  } catch (err) {
    createError.value = err.message
  } finally {
    createBusy.value = false
  }
}

async function switchTo(row) {
  await team.switchTeam(row.id, { reload: false })
  router.push({ name: 'team-settings', params: { teamId: row.id } })
}

async function saveSettings() {
  if (!settingsForm.value.name.trim()) {
    toast.notify('团队名不能为空', { tone: 'error' })
    return
  }
  settingsBusy.value = true
  try {
    await teamApi.update(teamId.value, {
      name: settingsForm.value.name.trim(),
      git_repo_url: settingsForm.value.git_repo_url.trim(),
    })
    await team.loadTeams()
    fillSettings()
    toast.notify('团队设置已保存')
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  } finally {
    settingsBusy.value = false
  }
}

async function unbindRepo() {
  settingsForm.value.git_repo_url = ''
  await saveSettings()
}

async function deleteTeam(row) {
  if (
    !window.confirm(
      `确定删除团队「${row.name}」(${row.slug}) 吗？\n团队内的需求单、成员与流转记录会一并删除，且不可恢复。`
    )
  ) {
    return
  }
  try {
    await teamApi.remove(row.id)
    await team.loadTeams()
    if (team.currentTeamId === row.id) {
      const next = team.teams[0]?.id || 0
      await team.switchTeam(next, { reload: false })
      router.push({ name: 'team-settings', params: { teamId: next } })
    }
    toast.notify(`团队 ${row.slug} 已删除`)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  }
}

async function search() {
  if (!keyword.value.trim()) {
    candidates.value = []
    return
  }
  try {
    candidates.value = await teamApi.searchUsers(keyword.value.trim())
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  }
}

async function addMember(userId) {
  busyId.value = userId
  try {
    await teamApi.addMember(teamId.value, {
      user_id: userId,
      role: roleToAdd.value,
    })
    await team.refreshMembers()
    keyword.value = ''
    candidates.value = []
    toast.notify(`成员已加入，角色：${ROLE_LABELS[roleToAdd.value]}`)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  } finally {
    busyId.value = null
  }
}

async function changeRole(row, event) {
  const role = event.target.value
  busyId.value = row.user.id
  try {
    await teamApi.updateRole(teamId.value, row.user.id, role)
    await team.refreshMembers()
    toast.notify(`${row.user.display_name} 已设为${ROLE_LABELS[role]}`)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
    await team.refreshMembers().catch(() => {})
  } finally {
    busyId.value = null
  }
}

async function removeMember(row) {
  if (!window.confirm(`确定从团队移除 ${row.user.display_name} 吗？`)) return
  busyId.value = row.user.id
  try {
    await teamApi.removeMember(teamId.value, row.user.id)
    await team.refreshMembers()
    toast.notify('成员已移除')
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <div class="page">
    <div class="page__head">
      <div>
        <nav class="u-label page__crumb">协作平台 / 团队与项目管理 / 团队设置</nav>
        <h1 class="display">团队与项目管理</h1>
        <p class="u-muted page__lead">绑定 Git 仓库，创建、切换、删除团队，管理成员与验收负责人。</p>
      </div>
      <div class="page__head-right">
        <span class="u-label">当前团队</span>
        <span class="page__team">{{ current?.name || '—' }}</span>
      </div>
    </div>
    <div class="page__rule"></div>

    <div class="grid">
      <section class="card">
        <div class="card__head">
          <h2 class="card__title">01 / 我的团队</h2>
          <span class="u-label">共 {{ team.teams.length }} 个</span>
        </div>

        <div v-if="team.teams.length" class="team-list">
          <div
            v-for="row in team.teams"
            :key="row.id"
            class="team-row"
            :class="{ 'is-current': row.id === teamId }"
          >
            <div class="team-row__main">
              <div>
                {{ row.name }}
                <span v-if="row.id === teamId" class="chip-current">当前</span>
              </div>
              <div class="u-label u-mono">
                {{ row.slug }} · 我的角色 {{ ROLE_LABELS[row.my_role] || row.my_role || '—' }}
              </div>
            </div>
            <div class="team-row__ops">
              <button v-if="row.id !== teamId" class="btn btn--sm" @click="switchTo(row)">
                切换
              </button>
              <button
                v-if="row.my_role === 'owner'"
                class="btn btn--sm btn--danger"
                @click="deleteTeam(row)"
              >
                删除
              </button>
            </div>
          </div>
        </div>
        <div v-else class="field__hint">还没有团队，用下面表单创建第一个。</div>

        <div class="subform">
          <div class="field__label">新建团队</div>
          <div class="subform__grid">
            <input v-model="createForm.name" class="underline-input" placeholder="团队名" />
            <input
              v-model="createForm.slug"
              class="underline-input u-mono"
              placeholder="前缀 STAR"
              maxlength="16"
            />
          </div>
          <input
            v-model="createForm.git_repo_url"
            class="underline-input"
            placeholder="Git 仓库地址（可选，https://… 或 git@…）"
          />
          <div v-if="createError" class="field__error">{{ createError }}</div>
          <button class="btn btn--primary btn--sm" :disabled="createBusy" @click="createTeam">
            {{ createBusy ? '创建中…' : '＋ 创建团队' }}
          </button>
          <div class="field__hint">前缀创建后不可修改；创建者自动成为团队 owner。</div>
        </div>
      </section>

      <section class="card">
        <div class="card__head">
          <h2 class="card__title">02 / 当前团队设置</h2>
          <span class="u-label u-mono">{{ current?.slug || '—' }}</span>
        </div>

        <template v-if="current">
          <div class="field">
            <label class="field__label">团队名</label>
            <input
              v-model="settingsForm.name"
              class="underline-input"
              :disabled="!canManage"
            />
          </div>
          <div class="meta-grid">
            <div>
              <div class="meta-grid__key">单号前缀</div>
              <div class="meta-grid__value u-mono">{{ current.slug }}</div>
            </div>
            <div>
              <div class="meta-grid__key">我的角色</div>
              <div class="meta-grid__value">
                {{ ROLE_LABELS[team.myRole] || team.myRole || '—' }}
              </div>
            </div>
          </div>

          <div class="field">
            <label class="field__label">项目与代码仓库</label>
            <div class="field__hint">
              仓库地址、main 分支与本地仓库路径按项目维护；一个团队可以有多个项目，需求单在项目下绑定开发分支。
            </div>
            <button
              class="btn btn--sm"
              @click="router.push({ name: 'projects', params: { teamId } })"
            >
              前往项目与仓库 →
            </button>
          </div>

          <div class="card__actions">
            <button
              v-if="canManage"
              class="btn btn--primary btn--sm"
              :disabled="settingsBusy"
              @click="saveSettings"
            >
              {{ settingsBusy ? '保存中…' : '保存团队名' }}
            </button>
          </div>

          <div v-if="isOwner" class="danger-zone">
            <div>
              <div class="field__label">删除当前团队</div>
              <div class="field__hint">会一并删除需求单、成员与流转记录，不可恢复。</div>
            </div>
            <button class="btn btn--sm btn--danger" @click="deleteTeam(current)">
              删除团队
            </button>
          </div>
        </template>
        <div v-else class="field__hint">请先创建或选择一个团队。</div>
      </section>
    </div>

    <section class="card members">
      <div class="card__head">
        <h2 class="card__title">03 / 团队成员</h2>
        <span class="u-label">验收负责人负责「待验收」的通过或打回</span>
      </div>

      <template v-if="current">
        <div class="member-list">
          <div v-for="row in team.members" :key="row.id" class="member-row">
            <span class="member-row__name">{{ row.user.display_name }}</span>
            <span class="u-label">{{ row.user.username }}</span>
            <select
              v-if="canManage && row.role !== 'owner'"
              class="member-role"
              :value="row.role"
              :disabled="busyId === row.user.id"
              :aria-label="`设置 ${row.user.display_name} 的角色`"
              @change="changeRole(row, $event)"
            >
              <option v-for="item in ASSIGNABLE_ROLES" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
            <span v-else class="u-label">
              {{ row.role_label || ROLE_LABELS[row.role] || row.role }}
            </span>
            <button
              v-if="canManage && row.role !== 'owner'"
              class="btn btn--quiet btn--sm btn--danger"
              :disabled="busyId === row.user.id"
              @click="removeMember(row)"
            >
              移除
            </button>
            <span v-else class="u-label">—</span>
          </div>
        </div>

        <div v-if="canManage" class="subform">
          <div class="field__label">添加成员</div>
          <div class="subform__row">
            <input
              v-model="keyword"
              class="underline-input"
              placeholder="按用户名或邮箱搜索"
              @keyup.enter="search"
            />
            <select v-model="roleToAdd" class="underline-select subform__role" aria-label="新成员角色">
              <option v-for="item in ASSIGNABLE_ROLES" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
            <button class="btn btn--sm" @click="search">搜索</button>
          </div>
          <div v-if="candidates.length" class="candidate-list">
            <button
              v-for="user in candidates"
              :key="user.id"
              class="candidate-row"
              :disabled="busyId === user.id"
              @click="addMember(user.id)"
            >
              <span>{{ user.username }}</span>
              <span class="u-label">添加 ＋</span>
            </button>
          </div>
          <div v-else-if="keyword.trim()" class="field__hint">没有匹配的用户</div>
        </div>
      </template>
      <div v-else class="field__hint">选择团队后可管理成员。</div>
    </section>
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
.page__head-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.page__team { font-weight: 600; }
.page__rule {
  height: 2px;
  background: var(--line-base);
  margin-bottom: var(--space-8);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}
.card {
  border: 1px solid var(--line-base);
  background: var(--bg-surface);
  padding: var(--space-6);
}
.card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--line-hair);
  margin-bottom: var(--space-6);
}
.card__title {
  font-size: var(--fs-h2);
  line-height: var(--lh-h2);
  font-weight: 600;
}
.card__actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.team-list {
  border-top: 1px solid var(--line-base);
  margin-bottom: var(--space-8);
}
.team-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 56px;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--line-hair);
}
.team-row.is-current {
  background: var(--bg-sunken);
  box-shadow: inset 3px 0 0 var(--accent);
}
.team-row__main { min-width: 0; }
.team-row__ops {
  display: flex;
  gap: var(--space-2);
  flex: 0 0 auto;
}
.chip-current {
  margin-left: var(--space-2);
  padding: 0 6px;
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  color: var(--accent);
  font-size: 11px;
}
.subform {
  padding-top: var(--space-4);
  border-top: 1px solid var(--line-hair);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.subform__grid {
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: var(--space-4);
}
.subform__row {
  display: flex;
  align-items: flex-end;
  gap: var(--space-4);
}
.subform__role { flex: 0 0 130px; font-size: var(--fs-label); }
.danger-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-top: var(--space-8);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--signal-error);
  background: color-mix(in srgb, var(--signal-error) 7%, transparent);
}
.members { margin-top: var(--space-6); }
.member-list {
  border-top: 1px solid var(--line-base);
  margin-bottom: var(--space-8);
}
.member-row {
  display: grid;
  grid-template-columns: 1fr 1fr 130px 56px;
  align-items: center;
  gap: var(--space-4);
  min-height: 48px;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--line-hair);
}
.member-row__name { font-weight: 600; }
.member-role {
  padding: 2px 0;
  border: 0;
  border-bottom: 1px solid var(--line-base);
  background: transparent;
  font-size: var(--fs-label);
}
.candidate-list {
  margin-top: var(--space-2);
  border-top: 1px solid var(--line-hair);
}
.candidate-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--line-hair);
  background: transparent;
  padding: var(--space-2) 0;
  text-align: left;
}
.candidate-row:hover:not(:disabled) { background: var(--bg-sunken); }
@media (max-width: 992px) {
  .grid { grid-template-columns: 1fr; }
  .page__head { flex-direction: column; align-items: flex-start; }
  .member-row { grid-template-columns: 1fr 100px 56px; }
  .member-row > .u-label:nth-child(2) { display: none; }
}
</style>
