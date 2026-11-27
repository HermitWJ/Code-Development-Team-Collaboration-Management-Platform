<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useProjectStore } from '../stores/project'
import { useTeamStore } from '../stores/team'

const teamStore = useTeamStore()
const projectStore = useProjectStore()
const router = useRouter()
const open = ref(false)

async function pick(team) {
  open.value = false
  await teamStore.switchTeam(team.id, { reload: false })
  // 团队切换后项目列表必须重拉，项目 ID 是全局唯一的
  await projectStore.loadProjects(team.id)
  router.push({ name: 'dashboard', params: { teamId: team.id } })
}

function createTeam() {
  open.value = false
  router.push({
    name: 'team-settings',
    params: { teamId: teamStore.currentTeamId || 0 },
  })
}
</script>

<template>
  <div class="switcher">
    <button class="switcher__trigger" @click="open = !open" :aria-expanded="open">
      <span class="u-label">团队</span>
      <span class="switcher__name">{{ teamStore.currentTeam?.name || '选择团队' }}</span>
      <span class="switcher__slug u-mono">{{ teamStore.currentTeam?.slug || '—' }}</span>
      <span class="switcher__caret">⌄</span>
    </button>

    <div v-if="open" class="switcher__menu">
      <div class="switcher__menu-label u-label">我加入的团队</div>
      <button
        v-for="team in teamStore.teams"
        :key="team.id"
        class="switcher__row"
        :class="{ 'is-current': team.id === teamStore.currentTeamId }"
        @click="pick(team)"
      >
        <span>{{ team.name }}</span>
        <span class="u-mono">{{ team.slug }}</span>
      </button>
      <button class="switcher__create" @click="createTeam">
        ＋ 新建团队
      </button>
    </div>
  </div>
</template>

<style scoped>
.switcher {
  position: relative;
}
.switcher__trigger {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  border: 0;
  background: transparent;
  padding: 0;
  height: var(--topbar-h);
}
.switcher__name {
  border-bottom: 1px solid var(--line-base);
  padding-bottom: 2px;
  font-size: var(--fs-body);
}
.switcher__trigger:hover .switcher__name {
  border-bottom-color: var(--ink);
}
.switcher__slug {
  color: var(--ink-3);
}
.switcher__caret {
  color: var(--ink-2);
  font-size: 16px;
}
.switcher__menu {
  position: absolute;
  top: calc(var(--topbar-h) - 4px);
  left: 0;
  z-index: 30;
  width: 260px;
  background: var(--bg-surface);
  border: 1px solid var(--line-base);
  border-radius: var(--radius-sm);
  padding: var(--space-3) 0;
}
.switcher__menu-label {
  padding: 0 var(--space-4) var(--space-2);
}
.switcher__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  border: 0;
  background: transparent;
  padding: var(--space-2) var(--space-4);
  text-align: left;
  font-size: var(--fs-body);
}
.switcher__row:hover {
  background: var(--bg-sunken);
}
.switcher__row.is-current {
  box-shadow: inset 2px 0 0 var(--accent);
}
.switcher__row .u-mono {
  color: var(--ink-3);
}
.switcher__create {
  width: 100%;
  border: 0;
  border-top: 1px solid var(--line-hair);
  background: transparent;
  padding: var(--space-3) var(--space-4);
  margin-top: var(--space-2);
  text-align: left;
  font-size: var(--fs-body);
  color: var(--ink-2);
}
.switcher__create:hover {
  color: var(--ink);
  background: var(--bg-sunken);
}
</style>
