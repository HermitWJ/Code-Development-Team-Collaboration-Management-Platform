import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '../api/http'
import AppShell from '../layouts/AppShell.vue'
import Login from '../views/Login.vue'
import Dashboard from '../views/Dashboard.vue'
import TeamSettings from '../views/TeamSettings.vue'
import BranchList from '../views/code/BranchList.vue'
import CommitDetail from '../views/code/CommitDetail.vue'
import CommitList from '../views/code/CommitList.vue'
import ProjectList from '../views/code/ProjectList.vue'
import StoryManage from '../views/story/StoryManage.vue'

const routes = [
  { path: '/login', name: 'login', component: Login, meta: { public: true } },
  {
    path: '/',
    component: AppShell,
    children: [
      {
        path: '',
        redirect: () => {
          const teamId = localStorage.getItem('collab_team_id')
          return teamId ? `/teams/${teamId}/dashboard` : '/login'
        },
      },
      {
        path: 'teams/:teamId/dashboard',
        name: 'dashboard',
        component: Dashboard,
      },
      {
        path: 'teams/:teamId/settings',
        name: 'team-settings',
        component: TeamSettings,
      },
      {
        path: 'teams/:teamId/projects',
        name: 'projects',
        component: ProjectList,
      },
      {
        // 兼容上一版入口
        path: 'teams/:teamId/code/projects',
        redirect: (to) => ({ name: 'projects', params: { teamId: to.params.teamId } }),
      },
      {
        path: 'teams/:teamId/stories',
        name: 'stories',
        component: StoryManage,
      },
      {
        path: 'teams/:teamId/code/branches',
        name: 'code-branches',
        component: BranchList,
      },
      {
        path: 'teams/:teamId/code/commits',
        name: 'code-commits',
        component: CommitList,
      },
      {
        path: 'teams/:teamId/code/commits/:sha',
        name: 'code-commit-detail',
        component: CommitDetail,
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (!to.meta.public && !getToken()) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if (to.name === 'login' && getToken()) {
    return { path: '/' }
  }
  return true
})

export default router
