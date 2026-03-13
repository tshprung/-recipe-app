const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

/** Base URL for static assets (e.g. recipe images) served by the API. */
export function getStaticBase() {
  const u = import.meta.env.VITE_API_URL ?? ''
  const base = u.replace(/\/api\/?$/, '') || (typeof window !== 'undefined' ? window.location.origin : '')
  return base || ''
}

/** Full URL for a recipe image path (e.g. /static/recipe-images/1.jpg) or external URL (e.g. Unsplash). */
export function getRecipeImageUrl(imageUrl) {
  if (!imageUrl) return null
  if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) return imageUrl
  const base = getStaticBase()
  return base ? `${base}${imageUrl}` : imageUrl
}

const LANG_STORAGE_KEY = 'recipe-app-lang'

const REMEMBER_ME_KEY = 'recipe_app_remember_me'

function getUserToken() {
  const usePersistent = localStorage.getItem(REMEMBER_ME_KEY) === '1'
  if (usePersistent) return localStorage.getItem('token')
  return sessionStorage.getItem('token')
}

/** Auth token for API: user token if logged in, else trial token so trial users can call create/adapt/etc. */
function getToken() {
  const userToken = getUserToken()
  if (userToken) return userToken
  return getTrialToken()
}

const TRIAL_TOKEN_KEY = 'trial_token'

export function getTrialToken() {
  try {
    return typeof localStorage !== 'undefined' ? localStorage.getItem(TRIAL_TOKEN_KEY) : null
  } catch (_) {
    return null
  }
}

export function setTrialTokenStorage(token) {
  try {
    if (token) localStorage.setItem(TRIAL_TOKEN_KEY, token)
    else localStorage.removeItem(TRIAL_TOKEN_KEY)
  } catch (_) {}
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
    const err = new Error(typeof data?.detail === 'string' ? data.detail : data?.message || 'Request failed')
    err.status = res.status
    err.responseData = data
    if (res.status === 402 && data?.code === 'trial_exhausted') err.trialExhausted = true
    throw err
  }

  return data
}

async function uploadRecipeImage(recipeId, file) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/recipes/${recipeId}/image-upload`, {
    method: 'POST',
    body: form,
    headers,
  })
  const data = await res.json().catch(() => ({ detail: 'Unexpected server error' }))
  if (!res.ok) {
    const err = new Error(data.detail || 'Upload failed')
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  get:    (path)        => request(path),
  post:   (path, body)  => request(path, { method: 'POST',  body: JSON.stringify(body) }),
  patch:  (path, body)  => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path, body)   => request(path, body != null ? { method: 'DELETE', body: JSON.stringify(body) } : { method: 'DELETE' }),
  uploadRecipeImage,
}
