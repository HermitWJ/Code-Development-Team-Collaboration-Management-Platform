<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { authApi } from '../api/auth'
import { ROLE_LABELS } from '../config/constants'
import { useTeamStore } from '../stores/team'
import { useThemeStore } from '../stores/theme'
import { useUserStore } from '../stores/user'
import ProjectSwitcher from './ProjectSwitcher.vue'
import TeamSwitcher from './TeamSwitcher.vue'

const userStore = useUserStore()
const teamStore = useTeamStore()
const theme = useThemeStore()
const router = useRouter()

const roleLabel = computed(
  () => ROLE_LABELS[teamStore.myRole] || teamStore.myRole || '—'
)

function openTeamSettings() {
  const teamId = teamStore.currentTeamId || teamStore.teams[0]?.id || 0
  router.push({ name: 'team-settings', params: { teamId } })
}

async function logout() {
  try {
    await authApi.logout()
  } catch {
    // 退出以本地为主，接口失败也照常清理
  }
  userStore.signOut()
  router.replace({ name: 'login' })
}
</script>

<template>
  <header class="top">
    <div class="top__left">
      <TeamSwitcher />
      <span class="top__sep"></span>
      <ProjectSwitcher />
    </div>
    <div class="top__right">
      <button class="top__manage btn btn--quiet btn--sm" @click="openTeamSettings">
        团队设置
      </button>
      <button
        class="btn btn--quiet btn--sm top__theme"
        :aria-label="theme.mode === 'dark' ? '切换到浅色主题' : '切换到深色主题'"
        @click="theme.toggle()"
      >
        {{ theme.mode === 'dark' ? '☀ 浅色' : '☾ 深色' }}
      </button>
      <span class="top__sep"></span>
      <span class="u-label">角色</span>
      <span class="top__role u-mono">{{ roleLabel }}</span>
      <span class="top__sep"></span>
      <span class="u-label">当前身份</span>
      <span>{{ userStore.user?.display_name || '—' }}</span>
      <button class="btn btn--quiet btn--sm" @click="logout">退出</button>
    </div>
  </header>
</template>

<style scoped>
.top {
  height: var(--topbar-h);
  flex: 0 0 var(--topbar-h);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  padding: 0 var(--margin);
  border-bottom: 1px solid var(--line-base);
  background: var(--bg-paper);
}
.top__left {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  min-width: 0;
}
.top__right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--fs-body);
  flex: 0 0 auto;
}
.top__sep {
  width: 1px;
  height: 16px;
  background: var(--line-base);
}
.top__role {
  color: var(--ink);
}
.top__theme {
  border: 1px solid var(--line-base);
  min-width: 62px;
}
@media (max-width: 992px) {
  .top__manage {
    display: none;
  }
}
</style>
