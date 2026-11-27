import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { setToken } from '../api/http'

const USER_KEY = 'collab_user'

function loadUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const user = ref(loadUser())
  const isLogged = computed(() => !!user.value)

  function signIn(payload) {
    setToken(payload.token)
    user.value = payload.user
    localStorage.setItem(USER_KEY, JSON.stringify(payload.user))
  }

  function signOut() {
    setToken('')
    user.value = null
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem('collab_team_id')
  }

  return { user, isLogged, signIn, signOut }
})
