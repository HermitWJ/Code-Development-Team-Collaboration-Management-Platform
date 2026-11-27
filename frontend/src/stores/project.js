import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { codeApi } from '../api/code'

const PROJECT_KEY = 'collab_project_id'

export const useProjectStore = defineStore('project', () => {
  const projects = ref([])
  const currentProjectId = ref(Number(localStorage.getItem(PROJECT_KEY)) || 0)
  const loading = ref(false)
  // 每次切换项目自增；页面 watch 它统一重新加载，保证全站数据隔离
  const epoch = ref(0)

  const currentProject = computed(
    () => projects.value.find((row) => row.id === currentProjectId.value) || null
  )

  function persist() {
    if (currentProjectId.value) {
      localStorage.setItem(PROJECT_KEY, String(currentProjectId.value))
    } else {
      localStorage.removeItem(PROJECT_KEY)
    }
  }

  async function loadProjects(teamId) {
    if (!teamId) {
      projects.value = []
      currentProjectId.value = 0
      persist()
      epoch.value += 1
      return
    }
    loading.value = true
    try {
      projects.value = await codeApi.projects(teamId)
      // 项目 ID 全局唯一；切团队后旧项目不在列表里，自动落到该团队第一个项目
      if (!projects.value.some((row) => row.id === currentProjectId.value)) {
        currentProjectId.value = projects.value[0]?.id || 0
        persist()
      }
      epoch.value += 1
    } finally {
      loading.value = false
    }
  }

  function switchProject(id) {
    const next = Number(id) || 0
    if (next && !projects.value.some((row) => row.id === next)) return
    currentProjectId.value = next
    persist()
    epoch.value += 1
  }

  return {
    projects,
    currentProjectId,
    currentProject,
    loading,
    epoch,
    loadProjects,
    switchProject,
  }
})
