import { request } from './http'

export const teamApi = {
  list: () => request('/teams/'),
  create: (data) => request('/teams/', { method: 'POST', data }),
  detail: (teamId) => request(`/teams/${teamId}/`),
  update: (teamId, data) =>
    request(`/teams/${teamId}/`, { method: 'PATCH', data }),
  remove: (teamId) => request(`/teams/${teamId}/`, { method: 'DELETE' }),
  members: (teamId) => request(`/teams/${teamId}/members/`),
  addMember: (teamId, data) =>
    request(`/teams/${teamId}/members/`, { method: 'POST', data }),
  updateRole: (teamId, userId, role) =>
    request(`/teams/${teamId}/members/${userId}/`, {
      method: 'PATCH',
      data: { role },
    }),
  removeMember: (teamId, userId) =>
    request(`/teams/${teamId}/members/${userId}/`, { method: 'DELETE' }),
  searchUsers: (q) => request('/users/search/', { params: { q } }),
}
