<script setup>
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ImageLightbox from '../components/ImageLightbox.vue'
import SideNav from '../components/SideNav.vue'
import ToastHost from '../components/ToastHost.vue'
import TopBar from '../components/TopBar.vue'
import { useProjectStore } from '../stores/project'
import { useTeamStore } from '../stores/team'

const route = useRoute()
const router = useRouter()
const teamStore = useTeamStore()
const projectStore = useProjectStore()

onMounted(async () => {
  await teamStore.loadTeams()
  const routeTeamId = Number(route.params.teamId) || 0
  const target = routeTeamId || teamStore.teams[0]?.id || 0
  // 总是走一次 switchTeam：清缓存、重拉真实角色、epoch+1 触发页面加载
  await teamStore.switchTeam(target, { reload: false })
  await projectStore.loadProjects(target)
  if (!routeTeamId && target) {
    router.replace({ name: 'dashboard', params: { teamId: target } })
  }
})

// 直接改地址栏的 teamId 也要触发清缓存、重拉角色与项目列表
watch(
  () => route.params.teamId,
  async (value) => {
    const id = Number(value) || 0
    if (id && id !== teamStore.currentTeamId) {
      await teamStore.switchTeam(id, { reload: false })
      await projectStore.loadProjects(id)
    }
  }
)
</script>

<template>
  <div class="shell">
    <SideNav />
    <div class="shell__body">
      <TopBar />
      <main class="shell__content">
        <router-view />
      </main>
    </div>
    <ToastHost />
    <ImageLightbox />
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}
.shell__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.shell__content {
  flex: 1;
  min-width: 0;
}
</style>
