const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

function getToken() {
  return localStorage.getItem('token')
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers })
  } catch (err) {
    // Network error, CORS block, or server unreachable (browser often reports "Failed to fetch")
    const isFetchError = (err?.message ?? '').toLowerCase().includes('fetch')
    const msg = isFetchError
      ? "Can't reach the server. Check your connection and that the API URL is correct (and CORS is configured on the server)."
      : (err?.message || 'Network error')
    throw new Error(msg)
  }

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
