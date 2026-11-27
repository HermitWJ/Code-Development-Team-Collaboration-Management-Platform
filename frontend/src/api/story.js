import { request, upload } from './http'

export const storyApi = {
  list: (teamId, params) => request(`/teams/${teamId}/stories/`, { params }),
  detail: (teamId, storyId) => request(`/teams/${teamId}/stories/${storyId}/`),
  create: (teamId, data) =>
    request(`/teams/${teamId}/stories/`, { method: 'POST', data }),
  update: (teamId, storyId, data) =>
    request(`/teams/${teamId}/stories/${storyId}/`, { method: 'PATCH', data }),
  remove: (teamId, storyId) =>
    request(`/teams/${teamId}/stories/${storyId}/`, { method: 'DELETE' }),
  transitions: (teamId, storyId) =>
    request(`/teams/${teamId}/stories/${storyId}/transitions/`),
  doTransition: (teamId, storyId, data) =>
    request(`/teams/${teamId}/stories/${storyId}/transitions/`, {
      method: 'POST',
      data,
    }),
  stats: (teamId, params) =>
    request(`/teams/${teamId}/stories/stats/`, { params }),
  uploadMedia: (teamId, file) =>
    upload(`/teams/${teamId}/stories/media/`, file),
}
