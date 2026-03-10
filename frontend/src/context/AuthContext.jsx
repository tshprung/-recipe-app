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
    const token = localStorage.getItem('token')
    if (token) {
      api.get('/users/me')
        .then(me => {
          setUser(me)
          syncUiLanguageToStorage(me)
        })
        .catch(() => localStorage.removeItem('token'))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  async function login(email, password) {
    const password_hash = await hashPasswordForTransport(password)
    const data = await api.post('/auth/login', { email, password_hash })
    localStorage.setItem('token', data.access_token)
    const me = await api.get('/users/me')
    setUser(me)
    syncUiLanguageToStorage(me)
  }

  async function register(email, password, captchaToken = null, settings) {
    const password_hash = await hashPasswordForTransport(password)
    const body = {
      email,
      password_hash,
      ...settings,
    }
    if (captchaToken) body.captcha_token = captchaToken
    await api.post('/auth/register', body)
    await login(email, password)
  }

  function logout() {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, refreshUser, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
