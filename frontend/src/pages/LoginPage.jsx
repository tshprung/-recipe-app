import { useState, useEffect } from 'react'
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
  const [turnstileToken, setTurnstileToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()

  useEffect(() => {
    if (tab !== 'register') return
    window.onTurnstileSuccess = (token) => setTurnstileToken(token)
    return () => {
      window.onTurnstileSuccess = undefined
      setTurnstileToken('')
    }
  }, [tab])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (tab === 'register') {
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
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full border border-stone-200 rounded-xl px-4 py-3 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
            />
          </div>
          {tab === 'register' && (
            <div>
              <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('confirmPassword')}</label>
              <input
                type="password"
                value={passwordConfirm}
                onChange={e => setPasswordConfirm(e.target.value)}
                required={tab === 'register'}
                placeholder="••••••••"
                className="w-full border border-stone-200 rounded-xl px-4 py-3 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
              />
            </div>
          )}
          {tab === 'register' && (
            <div className="cf-turnstile-wrapper flex justify-center" data-sitekey={TURNSTILE_SITE_KEY}>
              <div className="cf-turnstile" data-sitekey={TURNSTILE_SITE_KEY} data-callback="onTurnstileSuccess" />
            </div>
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
