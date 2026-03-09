const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

const LANG_STORAGE_KEY = 'recipe-app-lang'

function getToken() {
  return localStorage.getItem('token')
}

function getLang() {
  try {
    const l = localStorage.getItem(LANG_STORAGE_KEY)
    if (l === 'en' || l === 'he' || l === 'pl') return l
  } catch (_) {}
  return 'en'
}

function t(key, vars = {}) {
  const lang = getLang()
  const dict = {
    en: {
      cantReachServer:
        "Can't reach the server at {{apiBase}}. Check your connection, that VITE_API_URL is set correctly when building, and that CORS allows your origin.",
    },
    he: {
      cantReachServer:
        "לא ניתן להגיע לשרת בכתובת {{apiBase}}. בדוק את החיבור, ש־VITE_API_URL מוגדר נכון בבנייה, וש־CORS מאפשר את המקור שלך.",
    },
    pl: {
      cantReachServer:
        "Nie można połączyć się z serwerem pod adresem {{apiBase}}. Sprawdź połączenie, czy VITE_API_URL jest poprawnie ustawione podczas budowania oraz czy CORS zezwala na Twoje źródło.",
    },
  }
  const raw = dict[lang]?.[key] ?? dict.en[key] ?? key
  return Object.entries(vars).reduce(
    (s, [k, v]) => s.replace(new RegExp(`{{${k}}}`, 'g'), String(v)),
    raw
  )
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
    const apiBase = (import.meta.env.VITE_API_URL ?? '(same origin)') + '/api'
    const msg = isFetchError
      ? t('cantReachServer', { apiBase })
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
  delete: (path, body)   => request(path, body != null ? { method: 'DELETE', body: JSON.stringify(body) } : { method: 'DELETE' }),
}
