import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { teamApi } from '../api/team'
import { useStoryStore } from './story'

const TEAM_KEY = 'collab_team_id'

export const useTeamStore = defineStore('team', () => {
  const teams = ref([])
  const currentTeamId = ref(Number(localStorage.getItem(TEAM_KEY)) || 0)
  const myRole = ref('')
  const members = ref([])
  const drawerOpen = ref(false)
  const loading = ref(false)
  // 每次切换团队自增；页面 watch 它统一重新加载，避免父子组件加载时序竞态
  const epoch = ref(0)

  const currentTeam = computed(
    () => teams.value.find((team) => team.id === currentTeamId.value) || null
  )
  const canManage = computed(() => ['owner', 'admin'].includes(myRole.value))

  async function loadTeams() {
    loading.value = true
    try {
      teams.value = await teamApi.list()
      return teams.value
    } finally {
      loading.value = false
    }
  }

  /** 切换团队的三条硬要求：清业务缓存、重拉真实角色、地址栏变化也触发。 */
  async function switchTeam(teamId, { reload = true } = {}) {
    const id = Number(teamId) || 0
    currentTeamId.value = id
    if (id) localStorage.setItem(TEAM_KEY, String(id))
    else localStorage.removeItem(TEAM_KEY)

    const storyStore = useStoryStore()
    storyStore.resetForTeam()
    epoch.value += 1

    myRole.value = ''
    members.value = []
    if (!id) return

    try {
      const [detail, memberRows] = await Promise.all([
        teamApi.detail(id),
        teamApi.members(id),
      ])
      myRole.value = detail.my_role || ''
      members.value = memberRows
    } catch {
      // 角色拿不到就按最保守的无权限渲染，不用上一个团队的角色
      myRole.value = ''
    }
    if (reload) await storyStore.loadList(id)
  }

  async function refreshMembers() {
    if (!currentTeamId.value) return
    members.value = await teamApi.members(currentTeamId.value)
  }

  function openDrawer() {
    drawerOpen.value = true
  }

  function closeDrawer() {
    drawerOpen.value = false
  }

  return {
    teams,
    currentTeamId,
    currentTeam,
    myRole,
    canManage,
    members,
    drawerOpen,
    loading,
    epoch,
    loadTeams,
    switchTeam,
    refreshMembers,
    openDrawer,
    closeDrawer,
  }
})
