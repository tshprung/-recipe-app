import { createContext, useContext, useState, useEffect } from 'react'
import { api } from '../api/client'
import { hashPasswordForTransport } from '../auth/passwordHash'

const AuthContext = createContext(null)
const LANG_STORAGE_KEY = 'recipe-app-lang'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  function syncUiLanguageToStorage(u) {
    const l = u?.ui_language
    if (l === 'en' || l === 'he' || l === 'pl') {
      try {
        localStorage.setItem(LANG_STORAGE_KEY, l)
      } catch (_) {}
    }
  }

  async function refreshUser() {
    try {
      const me = await api.get('/users/me')
      const user = storeRenewedToken(me)
      setUser(user)
      syncUiLanguageToStorage(user)
    } catch (_) {
      /* ignore */
    }
  }

  useEffect(() => {
    const token = getToken()
    if (token) {
      api.get('/users/me')
        .then(me => {
          const user = storeRenewedToken(me)
          setUser(user)
          syncUiLanguageToStorage(user)
        })
        .catch(err => {
          // Only clear token on 401 (invalid/expired); keep it on network errors so session persists
          if (err && err.status === 401) clearToken()
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  function getToken() {
    const usePersistent = typeof localStorage !== 'undefined' && localStorage.getItem('recipe_app_remember_me') === '1'
    if (usePersistent) return localStorage.getItem('token')
    return sessionStorage.getItem('token')
  }

  function clearToken() {
    localStorage.removeItem('token')
    sessionStorage.removeItem('token')
    localStorage.setItem('recipe_app_remember_me', '0')
  }

  function storeRenewedToken(me) {
    if (!me || !me.renewed_token) return me
    const usePersistent = localStorage.getItem('recipe_app_remember_me') === '1'
    if (usePersistent) localStorage.setItem('token', me.renewed_token)
    else sessionStorage.setItem('token', me.renewed_token)
    const { renewed_token: _, ...rest } = me
    return rest
  }

  async function login(email, password, rememberMe = true) {
    const password_hash = await hashPasswordForTransport(password)
    const data = await api.post('/auth/login', { email, password_hash })
    const token = data.access_token
    localStorage.setItem('recipe_app_remember_me', rememberMe ? '1' : '0')
    if (rememberMe) {
      localStorage.setItem('token', token)
      sessionStorage.removeItem('token')
    } else {
      sessionStorage.setItem('token', token)
      localStorage.removeItem('token')
    }
    const me = await api.get('/users/me')
    const user = storeRenewedToken(me)
    setUser(user)
    syncUiLanguageToStorage(user)
  }

  async function register(email, password, captchaToken = null, settings, rememberMe = true) {
    const password_hash = await hashPasswordForTransport(password)
    const body = {
      email,
      password_hash,
      ...settings,
    }
    if (captchaToken) body.captcha_token = captchaToken
    await api.post('/auth/register', body)
    await login(email, password, rememberMe)
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  async function setTokenFromOAuth(accessToken) {
    if (!accessToken || typeof accessToken !== 'string') return
    localStorage.setItem('recipe_app_remember_me', '1')
    localStorage.setItem('token', accessToken)
    sessionStorage.removeItem('token')
    try {
      const me = await api.get('/users/me')
      const user = storeRenewedToken(me)
      setUser(user)
      syncUiLanguageToStorage(user)
    } catch (err) {
      // Only clear on 401 (invalid token); keep stored token on network/5xx so user can retry
      if (err && err.status === 401) clearToken()
    }
  }

  return (
    <AuthContext.Provider value={{ user, setUser, refreshUser, login, register, logout, setTokenFromOAuth, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
