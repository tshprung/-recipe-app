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
      setUser(me)
      syncUiLanguageToStorage(me)
    } catch (_) {
      /* ignore */
    }
  }

  useEffect(() => {
    const token = getToken()
    if (token) {
      api.get('/users/me')
        .then(me => {
          setUser(me)
          syncUiLanguageToStorage(me)
        })
        .catch(() => clearToken())
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
    setUser(me)
    syncUiLanguageToStorage(me)
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
      setUser(me)
      syncUiLanguageToStorage(me)
    } catch (_) {
      clearToken()
    }
  }

  return (
    <AuthContext.Provider value={{ user, setUser, refreshUser, login, register, logout, setTokenFromOAuth, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
