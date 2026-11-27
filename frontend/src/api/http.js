const BASE = '/api/v1'
const TOKEN_KEY = 'collab_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

function authHeaders() {
  const headers = {}
  if (getToken()) headers.Authorization = `Token ${getToken()}`
  return headers
}

function normalizeError(response, payload) {
  const error = new Error(payload?.message || `请求失败 (${response.status})`)
  error.code = payload?.code || 'REQUEST_FAILED'
  error.status = response.status
  error.detail = payload?.detail
  return error
}

export async function request(path, { method = 'GET', data, params } = {}) {
  const url = new URL(BASE + path, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        url.searchParams.set(key, value)
      }
    })
  }

  const headers = authHeaders()
  if (data !== undefined) headers['Content-Type'] = 'application/json'

  let response
  try {
    response = await fetch(url.toString(), {
      method,
      headers,
      body: data === undefined ? undefined : JSON.stringify(data),
    })
  } catch {
    const error = new Error('无法连接服务，请确认后端已启动')
    error.code = 'NETWORK_ERROR'
    throw error
  }

  if (response.status === 204) return null

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) throw normalizeError(response, payload)
  return payload
}

/** 富文本图片/视频上传：走 multipart，不设 Content-Type，交给浏览器带 boundary。 */
export async function upload(path, file) {
  const url = new URL(BASE + path, window.location.origin)
  const body = new FormData()
  body.append('file', file)

  let response
  try {
    response = await fetch(url.toString(), {
      method: 'POST',
      headers: authHeaders(),
      body,
    })
  } catch {
    const error = new Error('无法连接服务，请确认后端已启动')
    error.code = 'NETWORK_ERROR'
    throw error
  }

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) throw normalizeError(response, payload)
  return payload
}
