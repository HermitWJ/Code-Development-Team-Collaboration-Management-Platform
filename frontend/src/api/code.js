import { request } from './http'

export const codeApi = {
  projects: (teamId) => request(`/teams/${teamId}/code/projects/`),
  createProject: (teamId, data) =>
    request(`/teams/${teamId}/code/projects/`, { method: 'POST', data }),
  updateProject: (teamId, projectId, data) =>
    request(`/teams/${teamId}/code/projects/${projectId}/`, {
      method: 'PATCH',
      data,
    }),
  removeProject: (teamId, projectId) =>
    request(`/teams/${teamId}/code/projects/${projectId}/`, {
      method: 'DELETE',
    }),
  commits: (teamId, params) =>
    request(`/teams/${teamId}/code/commits/`, { params }),
  importCommits: (teamId, data) =>
    request(`/teams/${teamId}/code/commits/`, { method: 'POST', data }),
  commit: (teamId, sha, projectId) =>
    request(`/teams/${teamId}/code/commits/${sha}/`, {
      params: { project_id: projectId || 0 },
    }),
  syncBranch: (teamId, data) =>
    request(`/teams/${teamId}/code/sync-branch/`, { method: 'POST', data }),
}
