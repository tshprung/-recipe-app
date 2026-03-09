import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

// Use Cloudflare test key so widget always shows when no real key is set
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'

export default function LoginPage() {
  const { lang, setLang, t } = useLanguage()
  const [tab, setTab] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false)
  const [turnstileToken, setTurnstileToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()
  const turnstileContainerRef = useRef(null)
  const turnstileWidgetIdRef = useRef(null)

  // Explicit render: widget is only in DOM when Register tab is active, so we must render it when tab switches to register.
  // Script is loaded synchronously in index.html (no defer) so window.turnstile is available; we poll briefly if needed.
  useEffect(() => {
    if (tab !== 'register' || !turnstileContainerRef.current) return

    const renderWidget = () => {
      if (!window.turnstile || !turnstileContainerRef.current) return
      if (turnstileWidgetIdRef.current != null) return // already rendered
      turnstileWidgetIdRef.current = window.turnstile.render(turnstileContainerRef.current, {
        sitekey: TURNSTILE_SITE_KEY,
        callback: (token) => setTurnstileToken(token),
      })
    }

    if (window.turnstile) {
      renderWidget()
    } else {
      const check = setInterval(() => {
        if (window.turnstile) {
          clearInterval(check)
          renderWidget()
        }
      }, 50)
      return () => clearInterval(check)
    }

    return () => {
      if (window.turnstile && turnstileWidgetIdRef.current != null) {
        window.turnstile.remove(turnstileWidgetIdRef.current)
        turnstileWidgetIdRef.current = null
      }
      setTurnstileToken('')
    }
  }, [tab])

  const EyeIcon = ({ open }) => (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-5 h-5"
    >
      {open ? (
        <>
          <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
          <circle cx="12" cy="12" r="3" />
        </>
      ) : (
        <>
          <path d="M10.58 10.58a2 2 0 0 0 2.83 2.83" />
          <path d="M9.88 5.09A10.94 10.94 0 0 1 12 5c6.5 0 10 7 10 7a19.57 19.57 0 0 1-3.33 4.64" />
          <path d="M6.61 6.61A19.57 19.57 0 0 0 2 12s3.5 7 10 7c1.06 0 2.07-.18 3.02-.49" />
          <path d="M2 2l20 20" />
        </>
      )}
    </svg>
  )

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (tab === 'register') {
      if (password.length < 8) {
        setError(t('passwordTooShort') || 'Password must be at least 8 characters')
        return
      }
      if (password !== passwordConfirm) {
        setError(t('passwordsMismatch'))
        return
      }
    }
    setLoading(true)
    try {
      if (tab === 'login') {
        await login(email, password)
      } else {
        await register(email, password, turnstileToken || null)
        alert(t('verificationEmailSent'))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Decorative blobs */}
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-amber-200/40 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-orange-200/40 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/4 w-64 h-64 bg-rose-200/20 rounded-full blur-3xl pointer-events-none" />

      <div className="relative bg-white rounded-3xl shadow-2xl shadow-orange-100 w-full max-w-md p-8">
        {/* Language switcher */}
        <div className="absolute top-4 right-4 flex rounded-lg overflow-hidden border border-stone-200 bg-stone-50">
          {['en', 'he', 'pl'].map(l => (
            <button
              key={l}
              type="button"
              onClick={() => setLang(l)}
              className={`px-2 py-1 text-xs font-bold uppercase ${lang === l ? 'bg-amber-500 text-white' : 'text-stone-500 hover:bg-stone-100'}`}
            >
              {l === 'he' ? 'עב' : l.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl shadow-lg shadow-orange-200 text-3xl mb-4">
            🍳
          </div>
          <h1 className="text-2xl font-bold text-stone-800">{t('appTitle')}</h1>
          <p className="text-stone-400 text-sm mt-1">{t('tagline')}</p>
        </div>

        {/* Tab switcher */}
        <div className="flex bg-stone-100 rounded-2xl p-1 mb-6">
          {['login', 'register'].map(tabKey => (
            <button
              key={tabKey}
              onClick={() => { setTab(tabKey); setError('') }}
              className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition-all ${
                tab === tabKey
                  ? 'bg-white text-stone-800 shadow-sm'
                  : 'text-stone-400 hover:text-stone-600'
              }`}
            >
              {tabKey === 'login' ? t('login') : t('register')}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('email')}</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="you@example.com"
              className="w-full border border-stone-200 rounded-xl px-4 py-3 text-sm bg-stone-50 text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('password')}</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                placeholder="••••••••"
                className="w-full border border-stone-200 rounded-xl pl-4 pr-11 py-3 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                aria-label={showPassword ? t('hidePassword') : t('showPassword')}
                className="absolute inset-y-0 right-0 px-3 flex items-center text-stone-500 hover:text-stone-700"
              >
                <EyeIcon open={showPassword} />
              </button>
            </div>
          </div>
          {tab === 'register' && (
            <div>
              <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('confirmPassword')}</label>
              <div className="relative">
                <input
                  type={showPasswordConfirm ? "text" : "password"}
                  value={passwordConfirm}
                  onChange={e => setPasswordConfirm(e.target.value)}
                  required={tab === 'register'}
                  autoComplete="new-password"
                  placeholder="••••••••"
                  className="w-full border border-stone-200 rounded-xl pl-4 pr-11 py-3 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPasswordConfirm(v => !v)}
                  aria-label={showPasswordConfirm ? t('hidePassword') : t('showPassword')}
                  className="absolute inset-y-0 right-0 px-3 flex items-center text-stone-500 hover:text-stone-700"
                >
                  <EyeIcon open={showPasswordConfirm} />
                </button>
              </div>
            </div>
          )}
          {tab === 'register' && (
            <div className="flex justify-center min-h-[65px]" ref={turnstileContainerRef} />
          )}

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
              <span className="flex-shrink-0">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-amber-500 hover:bg-amber-600 active:scale-[0.98] text-white rounded-xl py-3 text-sm font-bold disabled:opacity-50 transition-all hover:shadow-lg hover:shadow-amber-200 mt-2"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {t('loading')}
              </span>
            ) : tab === 'login' ? t('logInButton') : t('createAccountButton')}
          </button>
        </form>
      </div>
    </div>
  )
}
