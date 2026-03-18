import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { api } from '../api/client'
import { COUNTRIES, TARGET_LANGUAGES } from '../constants'

const API_BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

const COLORS = { bg: '#111111', card: '#1c1c1c', text: '#F8F8F6', accent: '#8FAF8F', secondary: '#C96A4A' }

const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'

/** Default recipe/app language for a country (user can change). */
function languageFromCountry(countryCode) {
  if (!countryCode) return 'en'
  const c = (countryCode || '').toUpperCase()
  if (c === 'PL') return 'pl'
  if (c === 'IL') return 'he'
  return 'en'
}

const defaultOnboarding = () => ({
  target_country: 'PL',
  target_language: 'en',
  target_city: '',
  target_zip: '',
  ui_language: 'en',
})

export default function OnboardingPage() {
  const { t } = useLanguage()
  const { login, register, setTokenFromOAuth, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [data, setData] = useState(defaultOnboarding)
  const [authTab, setAuthTab] = useState('register')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [turnstileToken, setTurnstileToken] = useState('')
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const [agreedToLegal, setAgreedToLegal] = useState(false)
  const turnstileContainerRef = useRef(null)
  const turnstileWidgetIdRef = useRef(null)
  const [locationDetecting, setLocationDetecting] = useState(false)
  const [locationError, setLocationError] = useState(null)

  const set = (key) => (value) => setData((d) => ({ ...d, [key]: value }))

  // Step 1: in background, geo-detect country and set country + national language (user can change)
  useEffect(() => {
    if (step !== 1) return
    let cancelled = false
    setLocationDetecting(true)
    setLocationError(null)
    api.get('/meta/geo')
      .then((res) => {
        if (cancelled) return
        if (res?.country_code && COUNTRIES.some((c) => c.code === res.country_code)) {
          const lang = languageFromCountry(res.country_code)
          setData((d) => ({
            ...d,
            target_country: res.country_code,
            target_language: lang,
            ui_language: 'en',
            target_city: res.city || d.target_city,
            target_zip: res.zip || d.target_zip,
          }))
        }
      })
      .catch(() => { if (!cancelled) setLocationError(null) })
      .finally(() => { if (!cancelled) setLocationDetecting(false) })
    return () => { cancelled = true }
  }, [step])

  // Zip-to-city lookup removed from onboarding to keep only language + country.

  // Turnstile for step 3 register
  useEffect(() => {
    if (step !== 3 || authTab !== 'register' || !turnstileContainerRef.current) return
    const render = () => {
      if (!window.turnstile || !turnstileContainerRef.current || turnstileWidgetIdRef.current != null) return
      turnstileWidgetIdRef.current = window.turnstile.render(turnstileContainerRef.current, {
        sitekey: TURNSTILE_SITE_KEY,
        callback: (token) => setTurnstileToken(token),
      })
    }
    if (window.turnstile) render()
    else {
      const id = setInterval(() => { if (window.turnstile) { clearInterval(id); render() } }, 50)
      return () => clearInterval(id)
    }
    return () => {
      if (window.turnstile && turnstileWidgetIdRef.current != null) {
        window.turnstile.remove(turnstileWidgetIdRef.current)
        turnstileWidgetIdRef.current = null
      }
      setTurnstileToken('')
    }
  }, [step, authTab])

  function toggleDish(type) {
    setData((d) => ({
      ...d,
      dish_preferences: d.dish_preferences.includes(type)
        ? d.dish_preferences.filter((x) => x !== type)
        : [...d.dish_preferences, type],
    }))
  }

  function toggleAllergen(code) {
    setData((d) => ({
      ...d,
      allergens: d.allergens.includes(code) ? d.allergens.filter((c) => c !== code) : [...d.allergens, code],
    }))
  }

  function toggleDiet(key) {
    setData((d) => ({
      ...d,
      diet_filters: d.diet_filters.includes(key) ? d.diet_filters.filter((k) => k !== key) : [...d.diet_filters, key],
    }))
  }

  async function handleAuthSubmit(e) {
    e.preventDefault()
    setAuthError('')
    if (authTab === 'register') {
      if (!agreedToLegal) {
        setAuthError('You must agree to the Terms of Service and Privacy Policy to create an account.')
        return
      }
      if (password.length < 8) {
        setAuthError(t('passwordTooShort') || 'Password must be at least 8 characters')
        return
      }
      if (password !== passwordConfirm) {
        setAuthError(t('passwordsMismatch'))
        return
      }
    }
    setAuthLoading(true)
    try {
      if (authTab === 'login') {
        await login(email, password, rememberMe)
        navigate('/', { replace: true })
      } else {
        const settings = {
          ui_language: data.ui_language,
          target_language: data.target_language,
          target_country: data.target_country,
          target_city: data.target_city || undefined,
          target_zip: data.target_zip || undefined,
        }
        await register(email, password, turnstileToken || null, settings, rememberMe)
        if (authTab === 'register') alert(t('verificationEmailSent'))
        navigate('/', { replace: true })
      }
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setAuthLoading(false)
    }
  }

  function handleOAuthClick(provider) {
    // No claim token anymore — we prepare recipes after register. OAuth users can fetch from Settings if needed.
    window.location.href = `${API_BASE}/auth/${provider}`
  }

  const inputCls = 'w-full rounded-xl px-4 py-3 text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/30 transition-colors ring-1 ring-white/10 bg-black/30 text-white'

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" style={{ backgroundColor: COLORS.bg, color: COLORS.text }}>
      <div aria-hidden="true" className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-[30%] -left-48 h-[480px] w-[480px] rounded-full blur-3xl" style={{ backgroundColor: COLORS.accent, opacity: 0.08 }} />
        <div className="absolute -bottom-40 right-[-120px] h-[520px] w-[520px] rounded-full blur-3xl" style={{ backgroundColor: COLORS.secondary, opacity: 0.06 }} />
      </div>

      <div className="relative w-full max-w-lg rounded-3xl shadow-2xl ring-1 ring-white/10 p-6 sm:p-8" style={{ backgroundColor: COLORS.card }}>
        {/* Step 1: Let your helper get to know you */}
        {step === 1 && (
          <>
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white/95">Let your helper get to know you</h1>
              <p className="text-white/60 text-sm mt-1">Location and language (both optional)</p>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">Location</label>
                {locationDetecting && (
                  <p className="text-white/50 text-xs mb-1.5">Detecting your location…</p>
                )}
                <select
                  value={data.target_country}
                  onChange={(e) => set('target_country')(e.target.value)}
                  className={inputCls}
                >
                  {COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>{c.name}</option>
                  ))}
                </select>
                {locationError && <p className="text-amber-400 text-xs mt-1">{locationError}</p>}
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">App / website language</label>
                <div className={`${inputCls} flex items-center`} aria-label="App language">
                  English
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">Recipe language</label>
                <select
                  value={data.target_language}
                  onChange={(e) => set('target_language')(e.target.value)}
                  className={inputCls}
                >
                  {TARGET_LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>{l.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="mt-8 flex justify-end">
              <button
                type="button"
                onClick={() => setStep(3)}
                className="rounded-xl px-5 py-2.5 text-sm font-semibold text-stone-900 shadow transition hover:opacity-95"
                style={{ backgroundColor: COLORS.accent }}
              >
                Next
              </button>
            </div>
          </>
        )}
        {/* Previous Step 2 (household, allergens, diets) was removed from onboarding.
            Users can set preferences later in Settings and in the \"Find new recipes\" flow. */}

        {/* Step 3: Sign in / Register */}
        {step === 3 && (
          <>
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white/95">Create account or sign in</h1>
              <p className="text-white/60 text-sm mt-1">Then we’ll take you to your recipes</p>
            </div>
            <div className="flex rounded-2xl p-1 mb-4 ring-1 ring-white/10" style={{ backgroundColor: 'rgba(0,0,0,0.3)' }}>
              {['register', 'login'].map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => { setAuthTab(tab); setAuthError('') }}
                  className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition ${
                    authTab === tab ? 'text-stone-900' : 'text-white/60 hover:text-white/80'
                  }`}
                  style={authTab === tab ? { backgroundColor: COLORS.accent } : {}}
                >
                  {tab === 'register' ? 'Create account' : 'Sign in'}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-2 mb-4">
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); handleOAuthClick('google') }}
                className="flex items-center justify-center gap-2 w-full rounded-xl px-4 py-3 text-sm font-medium bg-white text-stone-800 hover:bg-stone-100 transition border border-white/20"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                Continue with Google
              </a>
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); handleOAuthClick('facebook') }}
                className="flex items-center justify-center gap-2 w-full rounded-xl px-4 py-3 text-sm font-medium bg-[#1877F2] text-white hover:bg-[#166FE5] transition border border-[#1877F2]"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                Continue with Facebook
              </a>
            </div>
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/20" /></div>
              <div className="relative flex justify-center text-xs"><span className="px-2 bg-[#1c1c1c] text-white/50">Or with email</span></div>
            </div>
            <form onSubmit={handleAuthSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('email')}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="you@example.com"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('password')}</label>
                <input
                  type={authTab === 'login' ? (showPassword ? 'text' : 'password') : (showPassword ? 'text' : 'password')}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete={authTab === 'login' ? 'current-password' : 'new-password'}
                  placeholder="••••••••"
                  className={inputCls}
                />
              </div>
              {authTab === 'register' && (
                <div>
                  <label className="block text-sm font-semibold text-white/80 mb-1.5">{t('confirmPassword')}</label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={passwordConfirm}
                    onChange={(e) => setPasswordConfirm(e.target.value)}
                    required
                    placeholder="••••••••"
                    className={inputCls}
                  />
                </div>
              )}
              {authTab === 'register' && (
                <div ref={turnstileContainerRef} className="flex justify-center" />
              )}
              {authError && <p className="text-amber-400 text-sm">{authError}</p>}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="remember"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded border-white/30"
                />
                <label htmlFor="remember" className="text-sm text-white/70">Keep me signed in</label>
              </div>
              {authTab === 'register' && (
                <div className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    id="legal"
                    checked={agreedToLegal}
                    onChange={(e) => setAgreedToLegal(e.target.checked)}
                    className="mt-1 rounded border-white/30"
                    required
                  />
                  <label htmlFor="legal" className="text-sm text-white/70">
                    I agree to the{' '}
                    <Link to="/terms" className="underline hover:text-white">Terms of Service</Link>
                    {' '}and{' '}
                    <Link to="/privacy" className="underline hover:text-white">Privacy Policy</Link>
                  </label>
                </div>
              )}
              <button
                type="submit"
                disabled={authLoading || (authTab === 'register' && (!turnstileToken || !agreedToLegal))}
                className="w-full rounded-xl px-4 py-3 text-sm font-semibold text-stone-900 transition disabled:opacity-50"
                style={{ backgroundColor: COLORS.accent }}
              >
                {authLoading ? (t('loading') || 'Loading…') : (authTab === 'register' ? 'Create account' : 'Sign in')}
              </button>
            </form>
            <div className="mt-4 flex justify-between">
              <button type="button" onClick={() => setStep(2)} className="text-sm text-white/60 hover:text-white/80">
                Back
              </button>
              <Link to="/signin" className="text-sm text-white/60 hover:text-white/80">Already have an account? Sign in here</Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
