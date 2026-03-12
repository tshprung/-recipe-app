import { useState, useEffect, useRef } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { api } from '../api/client'

// Use Cloudflare test key so widget always shows when no real key is set
const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'
const API_BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

const COLORS = {
  bg: '#111111',
  card: '#1c1c1c',
  text: '#F8F8F6',
  accent: '#C96A4A',
  secondary: '#8FAF8F',
}

const COUNTRIES = [
  { code: 'PL', name: 'Poland' },
  { code: 'IL', name: 'Israel' },
  { code: 'US', name: 'United States' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'ES', name: 'Spain' },
  { code: 'IT', name: 'Italy' },
]

const TARGET_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'pl', name: 'Polski' },
  { code: 'he', name: 'עברית' },
  { code: 'es', name: 'Español' },
  { code: 'fr', name: 'Français' },
  { code: 'de', name: 'Deutsch' },
  { code: 'it', name: 'Italiano' },
  { code: 'pt', name: 'Português' },
  { code: 'ru', name: 'Русский' },
  { code: 'ar', name: 'العربية' },
  { code: 'uk', name: 'Українська' },
  { code: 'nl', name: 'Nederlands' },
  { code: 'tr', name: 'Türkçe' },
  { code: 'ja', name: '日本語' },
  { code: 'zh', name: '中文' },
  { code: 'cs', name: 'Čeština' },
  { code: 'hu', name: 'Magyar' },
  { code: 'ro', name: 'Română' },
  { code: 'el', name: 'Ελληνικά' },
  { code: 'sv', name: 'Svenska' },
]

export default function LoginPage() {
  const { t } = useLanguage()
  const location = useLocation()
  const [tab, setTab] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [uiLanguage, setUiLanguage] = useState('en')
  const [targetLanguage, setTargetLanguage] = useState('pl')
  const [targetCountry, setTargetCountry] = useState('PL')
  const [targetCity, setTargetCity] = useState('Wrocław')
  const [targetZip, setTargetZip] = useState('50-001')
  const [zipStatus, setZipStatus] = useState(null) // null | 'loading' | 'ok' | 'error'
  const [locationDetecting, setLocationDetecting] = useState(false)
  const [locationError, setLocationError] = useState(null)
  const [showPassword, setShowPassword] = useState(false)
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false)
  const [turnstileToken, setTurnstileToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const { login, register, setTokenFromOAuth } = useAuth()
  const navigate = useNavigate()
  const turnstileContainerRef = useRef(null)
  const turnstileWidgetIdRef = useRef(null)

  // Handle OAuth callback: ?token=... or ?error=... (claim onboarding starter recipes if user came from onboarding)
  useEffect(() => {
    const params = new URLSearchParams(location.search || '')
    const token = params.get('token')
    const oauthError = params.get('error')
    if (token) {
      setTokenFromOAuth(token).then(async () => {
        try {
          const raw = sessionStorage.getItem('onboarding_claim')
          if (raw) {
            const payload = JSON.parse(raw)
            await api.post('/users/me/claim-starter-recipes', payload)
            sessionStorage.removeItem('onboarding_claim')
          }
        } catch (_) {}
        navigate('/', { replace: true })
      })
      return
    }
    if (oauthError) {
      const msg = oauthError === 'google_denied' || oauthError === 'facebook_denied'
        ? 'Sign-in was cancelled.'
        : oauthError === 'config' || oauthError === 'google_failed' || oauthError === 'facebook_failed'
          ? 'Sign-in failed. Try again or use email.'
          : 'Something went wrong.'
      setError(msg)
      navigate('/login', { replace: true })
    }
  }, [location.search, setTokenFromOAuth, navigate])

  // Allow deep-linking to Register tab: /login?tab=register
  useEffect(() => {
    const params = new URLSearchParams(location.search || '')
    const next = (params.get('tab') || '').toLowerCase()
    if (next === 'register') setTab('register')
    if (next === 'login') setTab('login')
  }, [location.search])

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

  async function detectLocation() {
    setLocationError(null)
    setLocationDetecting(true)
    try {
      const data = await api.get('/meta/geo')
      if (data?.country_code) {
        const code = data.country_code
        if (COUNTRIES.some(c => c.code === code)) setTargetCountry(code)
      }
      if (data?.city) setTargetCity(data.city)
      if (data?.zip) setTargetZip(data.zip)
      if (data?.region && !data?.city) setTargetCity(data.region)
    } catch (e) {
      setLocationError(e?.message || 'Could not detect location')
    } finally {
      setLocationDetecting(false)
    }
  }

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
        await login(email, password, rememberMe)
      } else {
        await register(email, password, turnstileToken || null, {
          ui_language: uiLanguage,
          target_language: targetLanguage,
          target_country: targetCountry,
          target_city: targetCity,
          target_zip: targetZip || null,
        }, rememberMe)
        alert(t('verificationEmailSent'))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function resolveZipToCity() {
    if (!targetZip.trim() || !targetCountry.trim()) return
    setZipStatus('loading')
    try {
      const data = await api.get(`/meta/resolve-city?country=${encodeURIComponent(targetCountry)}&zip=${encodeURIComponent(targetZip.trim())}`)
      if (data?.city) setTargetCity(data.city)
      setZipStatus('ok')
      setTimeout(() => setZipStatus(null), 2000)
    } catch (_) {
      setZipStatus('error')
      setTimeout(() => setZipStatus(null), 3500)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" style={{ backgroundColor: COLORS.bg, color: COLORS.text }}>
      {/* Subtle background accents (match landing) */}
      <div aria-hidden="true" className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-[30%] -left-48 h-[480px] w-[480px] rounded-full blur-3xl" style={{ backgroundColor: COLORS.accent, opacity: 0.08 }} />
        <div className="absolute -bottom-40 right-[-120px] h-[520px] w-[520px] rounded-full blur-3xl" style={{ backgroundColor: COLORS.secondary, opacity: 0.06 }} />
      </div>

      <div className="relative w-full max-w-md rounded-3xl shadow-2xl ring-1 ring-white/10 p-8" style={{ backgroundColor: COLORS.card }}>
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl ring-1 ring-white/10 text-3xl mb-4" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}>
            🍳
          </div>
          <h1 className="text-2xl font-bold text-white/95">{t('appTitle')}</h1>
          <p className="text-white/60 text-sm mt-1">{t('tagline')}</p>
        </div>

        {/* Tab switcher */}
        <div className="flex rounded-2xl p-1 mb-6 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(0,0,0,0.3)' }}>
          {['login', 'register'].map(tabKey => (
            <button
              key={tabKey}
              onClick={() => { setTab(tabKey); setError('') }}
              className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition-all ${
                tab === tabKey
                  ? 'text-stone-900 shadow-sm'
                  : 'text-white/60 hover:text-white/80'
              }`}
              style={tab === tabKey ? { backgroundColor: COLORS.accent } : {}}
            >
              {tabKey === 'login' ? t('login') : t('register')}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-2 mb-4">
          <a
            href={`${API_BASE}/auth/google`}
            className="flex items-center justify-center gap-2 w-full rounded-xl px-4 py-3 text-sm font-medium bg-white text-stone-800 hover:bg-stone-100 transition-colors border border-white/20"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Continue with Google
          </a>
          <a
            href={`${API_BASE}/auth/facebook`}
            className="flex items-center justify-center gap-2 w-full rounded-xl px-4 py-3 text-sm font-medium bg-[#1877F2] text-white hover:bg-[#166FE5] transition-colors border border-[#1877F2]"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
            Continue with Facebook
          </a>
        </div>

        <div className="relative mb-4">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/20" /></div>
          <div className="relative flex justify-center text-xs"><span className="px-2 bg-[#1c1c1c] text-white/50">Or sign in with email</span></div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('email')}</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="you@example.com"
              className="w-full rounded-xl px-4 py-3 text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('password')}</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                placeholder="••••••••"
                className="w-full rounded-xl pl-4 pr-11 py-3 text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white"
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                aria-label={showPassword ? t('hidePassword') : t('showPassword')}
                className="absolute inset-y-0 right-0 px-3 flex items-center text-white/50 hover:text-white/80"
              >
                <EyeIcon open={showPassword} />
              </button>
            </div>
          </div>
          {tab === 'register' && (
            <div>
              <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('confirmPassword')}</label>
              <div className="relative">
                <input
                  type={showPasswordConfirm ? "text" : "password"}
                  value={passwordConfirm}
                  onChange={e => setPasswordConfirm(e.target.value)}
                  required={tab === 'register'}
                  autoComplete="new-password"
                  placeholder="••••••••"
                  className="w-full rounded-xl pl-4 pr-11 py-3 text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white"
                />
                <button
                  type="button"
                  onClick={() => setShowPasswordConfirm(v => !v)}
                  aria-label={showPasswordConfirm ? t('hidePassword') : t('showPassword')}
                  className="absolute inset-y-0 right-0 px-3 flex items-center text-white/50 hover:text-white/80"
                >
                  <EyeIcon open={showPasswordConfirm} />
                </button>
              </div>
            </div>
          )}

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={e => setRememberMe(e.target.checked)}
              className="rounded border-white/30 bg-black/30 text-[#C96A4A] focus:ring-white/30"
            />
            <span className="text-sm text-white/75">Keep me logged in</span>
          </label>

          {tab === 'register' && (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">Site language</label>
                <select
                  value={uiLanguage}
                  onChange={e => setUiLanguage(e.target.value)}
                  className="w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white"
                >
                  <option value="en" className="bg-stone-800 text-white">English</option>
                  <option value="he" className="bg-stone-800 text-white">עברית</option>
                  <option value="pl" className="bg-stone-800 text-white">Polski</option>
                </select>
                <p className="text-xs text-white/50 mt-1.5">You can change this later in Settings.</p>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={detectLocation}
                    disabled={locationDetecting}
                    className="text-sm font-medium text-white/90 bg-white/10 hover:bg-white/15 border border-white/20 rounded-lg px-3 py-2 transition-colors disabled:opacity-60"
                  >
                    {locationDetecting ? 'Detecting…' : 'Use my location'}
                  </button>
                  {locationError && <span className="text-xs text-red-400">{locationError}</span>}
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <div>
                  <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('translateTo')}</label>
                  <select
                    value={targetLanguage}
                    onChange={e => setTargetLanguage(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white"
                    required
                  >
                    {TARGET_LANGUAGES.map(l => (
                      <option key={l.code} value={l.code} className="bg-stone-800 text-white">{l.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('country')}</label>
                  <select
                    value={targetCountry}
                    onChange={e => setTargetCountry(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white"
                    required
                  >
                    {COUNTRIES.map(c => (
                      <option key={c.code} value={c.code} className="bg-stone-800 text-white">{c.code} — {c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-white/80 mb-1.5">ZIP</label>
                  <input
                    value={targetZip}
                    onChange={e => setTargetZip(e.target.value)}
                    onBlur={resolveZipToCity}
                    placeholder="e.g. 50-001"
                    className="w-full rounded-xl px-4 py-3 text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white"
                    required
                  />
                  {zipStatus === 'loading' && <p className="text-xs text-white/50 mt-1">Looking up city…</p>}
                  {zipStatus === 'error' && <p className="text-xs text-red-400 mt-1">Could not resolve city from ZIP.</p>}
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('city')}</label>
                <input
                  value={targetCity}
                  onChange={e => setTargetCity(e.target.value)}
                  placeholder={t('hintCity')}
                  className="w-full rounded-xl px-4 py-3 text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white"
                  required
                />
                <p className="text-xs text-white/50 mt-1.5">Auto-filled from ZIP. You can adjust if needed.</p>
              </div>
            </div>
          )}

          {tab === 'register' && (
            <div className="flex justify-center min-h-[65px]" ref={turnstileContainerRef} />
          )}

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-300 bg-red-500/20 border border-red-500/30 rounded-xl px-4 py-3">
              <span className="flex-shrink-0">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl py-3 text-sm font-bold disabled:opacity-50 transition-all hover:opacity-95 active:scale-[0.98] mt-2 text-black shadow"
            style={{ backgroundColor: COLORS.accent }}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {t('loading')}
              </span>
            ) : tab === 'login' ? t('logInButton') : t('createAccountButton')}
          </button>

          <p className="mt-6 text-xs text-white/55 text-center leading-relaxed">
            By continuing, you agree to the{' '}
            <Link to="/terms" className="underline hover:text-white/80 transition-colors">Terms of Service</Link>
            {' '}and{' '}
            <Link to="/privacy" className="underline hover:text-white/80 transition-colors">Privacy Policy</Link>.
          </p>
        </form>
      </div>
    </div>
  )
}
