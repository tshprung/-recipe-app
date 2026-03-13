import { createContext, useContext, useState, useEffect } from 'react'
import { api, getTrialToken, setTrialTokenStorage } from '../api/client'
import { hashPasswordForTransport } from '../auth/passwordHash'

const AuthContext = createContext(null)
const LANG_STORAGE_KEY = 'recipe-app-lang'
const TRIAL_REMAINING_KEY = 'trial_remaining_actions'
const MAX_TRIAL_ACTIONS = 5

function getTrialRemainingFromStorage() {
  try {
    const v = localStorage.getItem(TRIAL_REMAINING_KEY)
    if (v != null) {
      const n = parseInt(v, 10)
      if (Number.isFinite(n) && n >= 0) return Math.min(n, MAX_TRIAL_ACTIONS)
    }
  } catch (_) {}
  return MAX_TRIAL_ACTIONS
}

function setTrialRemainingStorage(n) {
  try {
    if (n != null) localStorage.setItem(TRIAL_REMAINING_KEY, String(n))
    else localStorage.removeItem(TRIAL_REMAINING_KEY)
  } catch (_) {}
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [trialToken, setTrialTokenState] = useState(null)
  const [trialRemainingActions, setTrialRemainingActionsState] = useState(MAX_TRIAL_ACTIONS)
  const [loading, setLoading] = useState(true)

  function setTrialToken(token, remainingActions = null) {
    if (token) setTrialTokenStorage(token)
    else setTrialTokenStorage(null)
    setTrialTokenState(token || null)
    const remaining = remainingActions != null ? remainingActions : (token ? getTrialRemainingFromStorage() : MAX_TRIAL_ACTIONS)
    setTrialRemainingActionsState(remaining)
    setTrialRemainingStorage(remaining)
  }

  /** Sign out of trial view only: hide app and show landing. Keeps trial token and credits in storage so "Try for free" restores the same session. */
  function leaveTrial() {
    setTrialTokenState(null)
  }

  function decrementTrialActions() {
    setTrialRemainingActionsState((prev) => {
      const next = Math.max(0, prev - 1)
      setTrialRemainingStorage(next)
      return next
    })
  }

  function syncUiLanguageToStorage(u) {
    const l = u?.ui_language
    if (l === 'en' || l === 'he' || l === 'pl') {
      try {
        localStorage.setItem(LANG_STORAGE_KEY, l)
      } catch (_) {}
    }
  }

  async function refreshUser() {
    if (!getToken()) return
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
    const trial = getTrialToken()
    if (trial) {
      setTrialTokenState(trial)
      setTrialRemainingActionsState(getTrialRemainingFromStorage())
    }
    if (token) {
      api.get('/users/me')
        .then(me => {
          const user = storeRenewedToken(me)
          setUser(user)
          syncUiLanguageToStorage(user)
        })
        .catch(err => {
          // Only clear token on 401 (invalid/expired); keep it on network errors so session persists
          if (err && err.status === 401) {
            clearToken()
            setUser(null)
          }
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
    setTrialToken(null) // clear trial when user logs in
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
    setTrialToken(null)
    setTrialRemainingStorage(null)
    setTrialRemainingActionsState(MAX_TRIAL_ACTIONS)
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
    <AuthContext.Provider value={{
      user, setUser, refreshUser, login, register, logout, setTokenFromOAuth,
      trialToken, setTrialToken, leaveTrial, trialRemainingActions, decrementTrialActions,
      loading,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
