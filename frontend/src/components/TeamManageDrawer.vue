<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { teamApi } from '../api/team'
import { ASSIGNABLE_ROLES, ROLE_LABELS } from '../config/constants'
import { useTeamStore } from '../stores/team'
import { useToastStore } from '../stores/toast'

const store = useTeamStore()
const toast = useToastStore()
const router = useRouter()

const form = ref({ name: '', slug: '' })
const roleToAdd = ref('member')
const saving = ref(false)
const error = ref('')
const keyword = ref('')
const candidates = ref([])
const busyId = ref(null)

const hasTeam = computed(() => !!store.currentTeamId)

watch(
  () => store.drawerOpen,
  (open) => {
    if (!open) return
    error.value = ''
    keyword.value = ''
    candidates.value = []
    if (hasTeam.value) store.refreshMembers().catch(() => {})
  }
)

async function createTeam() {
  if (!form.value.name.trim() || !form.value.slug.trim()) {
    error.value = '请填写团队名与单号前缀'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const team = await teamApi.create({
      name: form.value.name.trim(),
      slug: form.value.slug.trim().toUpperCase(),
    })
    await store.loadTeams()
    await store.switchTeam(team.id, { reload: false })
    form.value = { name: '', slug: '' }
    toast.notify(`已创建团队 ${team.name}，单号前缀 ${team.slug}`)
    store.closeDrawer()
    router.push({ name: 'dashboard', params: { teamId: team.id } })
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
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
    await teamApi.addMember(store.currentTeamId, {
      user_id: userId,
      role: roleToAdd.value,
    })
    await store.refreshMembers()
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
    await teamApi.updateRole(store.currentTeamId, row.user.id, role)
    await store.refreshMembers()
    toast.notify(`${row.user.display_name} 已设为${ROLE_LABELS[role]}`)
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
    await store.refreshMembers().catch(() => {})
  } finally {
    busyId.value = null
  }
}

async function removeMember(row) {
  if (row.user.id === store.currentTeam?.owner?.id) return
  busyId.value = row.user.id
  try {
    await teamApi.removeMember(store.currentTeamId, row.user.id)
    await store.refreshMembers()
    toast.notify('成员已移除')
  } catch (err) {
    toast.notify(err.message, { tone: 'error' })
  } finally {
    busyId.value = null
  }
}
</script>

<template>
  <Transition name="panel">
    <div
      v-if="store.drawerOpen"
      class="overlay overlay--drawer"
      @click.self="store.closeDrawer()"
    >
      <div class="drawer">
        <div class="drawer__head">
          <div>
            <div class="u-label">团队管理</div>
            <div class="drawer__sub">组建团队与成员</div>
          </div>
          <button class="btn btn--quiet btn--sm" @click="store.closeDrawer()">关闭 ×</button>
        </div>

        <section class="section">
          <div class="section__head">
            <span class="section__num">01</span>
            <h2 class="section__title">新建团队</h2>
            <span class="section__rule"></span>
          </div>
          <p class="u-muted" style="margin-bottom: var(--space-6)">
            创建者自动成为管理员；单号前缀用于生成需求单号，创建后不可修改。
          </p>

          <div class="field">
            <label class="field__label" for="team-name">团队名 <em>*</em></label>
            <input
              id="team-name"
              v-model="form.name"
              class="underline-input"
              placeholder="例如：星河项目组"
              autocomplete="off"
            />
          </div>
          <div class="field">
            <label class="field__label" for="team-slug">单号前缀 <em>*</em></label>
            <input
              id="team-slug"
              v-model="form.slug"
              class="underline-input u-mono"
              placeholder="例如：STAR"
              maxlength="16"
              autocomplete="off"
            />
            <div class="field__hint">2–16 位大写字母或数字，新需求将从 1 开始编号</div>
          </div>
          <div v-if="error" class="field__error" style="margin-bottom: var(--space-4)">
            {{ error }}
          </div>
          <button class="btn btn--primary" :disabled="saving" @click="createTeam">
            {{ saving ? '创建中…' : '创建团队' }}
          </button>
        </section>

        <section v-if="hasTeam" class="section">
          <div class="section__head">
            <span class="section__num">02</span>
            <h2 class="section__title">团队成员</h2>
            <span class="section__rule"></span>
          </div>
          <p class="u-muted" style="margin-bottom: var(--space-4)">
            验收负责人负责「待验收」需求的通过或打回；创建者角色不可修改。
          </p>

          <div class="member-list">
            <div v-for="row in store.members" :key="row.id" class="member-row">
              <div>
                <div>{{ row.user.display_name }}</div>
                <div class="u-label">{{ row.user.username }}</div>
              </div>
              <select
                v-if="store.canManage && row.role !== 'owner'"
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
                v-if="store.canManage && row.role !== 'owner'"
                class="btn btn--quiet btn--sm"
                :disabled="busyId === row.user.id"
                @click="removeMember(row)"
              >
                移除
              </button>
              <span v-else class="u-label">—</span>
            </div>
          </div>

          <div v-if="store.canManage" class="add-member">
            <div class="field__label">添加成员</div>
            <div class="add-member__row">
              <input
                v-model="keyword"
                class="underline-input"
                placeholder="按用户名或邮箱搜索"
                @keyup.enter="search"
              />
              <select v-model="roleToAdd" class="underline-select add-member__role" aria-label="新成员角色">
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
        </section>

        <div v-else class="state-block">
          <div class="state-block__title">还没有团队</div>
          <div class="state-block__desc">先创建一个团队，才能在团队内管理需求单。</div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.member-list {
  border-top: 1px solid var(--line-base);
  margin-bottom: var(--space-8);
}
.member-row {
  display: grid;
  grid-template-columns: 1fr 116px 56px;
  align-items: center;
  gap: var(--space-4);
  min-height: 52px;
  border-bottom: 1px solid var(--line-hair);
  padding: var(--space-2) 0;
}
.member-role {
  padding: 2px 0;
  border: 0;
  border-bottom: 1px solid var(--line-base);
  background: transparent;
  font-size: var(--fs-label);
}
.add-member__row {
  display: flex;
  align-items: flex-end;
  gap: var(--space-4);
}
.add-member__role {
  flex: 0 0 120px;
  font-size: var(--fs-label);
}
.candidate-list {
  margin-top: var(--space-3);
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
.candidate-row:hover:not(:disabled) {
  background: var(--bg-sunken);
}
</style>
