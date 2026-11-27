import { request } from './http'

export const authApi = {
  login: (username, password) =>
    request('/auth/login/', { method: 'POST', data: { username, password } }),
  me: () => request('/auth/me/'),
  logout: () => request('/auth/logout/', { method: 'POST' }),
}
