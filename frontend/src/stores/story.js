import { defineStore } from 'pinia'
import { ref } from 'vue'

import { storyApi } from '../api/story'

const DEFAULT_FILTERS = {
  status: '',
  type: '',
  assignee_id: '',
  priority: '',
  keyword: '',
  ordering: '-no_seq',
}

export const useStoryStore = defineStore('story', () => {
  const list = ref([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const filters = ref({ ...DEFAULT_FILTERS })
  const loading = ref(false)
  const ready = ref(false)
  const error = ref('')
  const detail = ref(null)
  const detailLoading = ref(false)
  const selectedId = ref(null)

  async function loadList(teamId) {
    if (!teamId) {
      list.value = []
      total.value = 0
      ready.value = true
      return
    }
    loading.value = true
    error.value = ''
    try {
      const data = await storyApi.list(teamId, {
        ...filters.value,
        page: page.value,
        page_size: pageSize.value,
      })
      list.value = data.results || []
      total.value = data.count || 0
      ready.value = true
    } catch (err) {
      error.value = err.message
      ready.value = true
    } finally {
      loading.value = false
    }
  }

  function setFilter(key, value) {
    filters.value[key] = value
    page.value = 1
  }

  function resetFilters() {
    filters.value = { ...DEFAULT_FILTERS }
    page.value = 1
  }

  function setPage(value) {
    page.value = value
  }

  function resetForTeam() {
    list.value = []
    total.value = 0
    detail.value = null
    selectedId.value = null
    page.value = 1
    error.value = ''
    ready.value = false
  }

  async function openDetail(teamId, storyId) {
    selectedId.value = storyId
    detailLoading.value = true
    try {
      detail.value = await storyApi.detail(teamId, storyId)
    } catch (err) {
      detail.value = null
      throw err
    } finally {
      detailLoading.value = false
    }
  }

  function closeDetail() {
    selectedId.value = null
    detail.value = null
  }

  function applyDetail(payload) {
    if (!payload) return
    // 合并而非替换：编辑响应不带流转历史时，保留已加载的记录
    detail.value = { ...(detail.value || {}), ...payload }
    const index = list.value.findIndex((row) => row.id === payload.id)
    if (index !== -1) list.value[index] = { ...list.value[index], ...payload }
  }

  return {
    list, total, page, pageSize, filters, loading, ready, error,
    detail, detailLoading, selectedId,
    loadList, setFilter, resetFilters, setPage, resetForTeam,
    openDetail, closeDetail, applyDetail,
  }
})
