const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

function getToken() {
  return localStorage.getItem('token')
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 204) return null

  const data = await res.json().catch(() => ({ detail: 'Unexpected server error' }))

  if (!res.ok) {
    throw new Error(data.detail || 'Request failed')
  }

  return data
}

export const api = {
  get:    (path)        => request(path),
  post:   (path, body)  => request(path, { method: 'POST',  body: JSON.stringify(body) }),
  patch:  (path, body)  => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path)        => request(path, { method: 'DELETE' }),
}
