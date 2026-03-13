import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { api } from '../api/client'

const API_BASE = (import.meta.env.VITE_API_URL ?? '') + '/api'

const COLORS = { bg: '#111111', card: '#1c1c1c', text: '#F8F8F6', accent: '#8FAF8F', secondary: '#C96A4A' }

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
  { code: 'ja', name: '日本語' },
]

const DISH_TYPES = [
  'pasta', 'pizza', 'chicken', 'beef', 'soups', 'fish', 'salads', 'baking', 'breakfast',
  'vegetarian', 'desserts', 'stews', 'grilling',
]

const ALLERGENS = [
  { code: 'gluten_cereals', label: 'Gluten (cereals)' },
  { code: 'crustaceans', label: 'Crustaceans' },
  { code: 'eggs', label: 'Eggs' },
  { code: 'fish', label: 'Fish' },
  { code: 'peanuts', label: 'Peanuts' },
  { code: 'soybeans', label: 'Soybeans' },
  { code: 'milk', label: 'Milk' },
  { code: 'tree_nuts', label: 'Tree nuts' },
  { code: 'sesame', label: 'Sesame' },
  { code: 'mustard', label: 'Mustard' },
  { code: 'celery', label: 'Celery' },
  { code: 'lupin', label: 'Lupin' },
  { code: 'sulphites', label: 'Sulphites' },
  { code: 'molluscs', label: 'Molluscs' },
]

const DIET_OPTIONS = [
  { key: 'vegetarian', label: 'Vegetarian' },
  { key: 'vegan', label: 'Vegan' },
  { key: 'gluten_free', label: 'Gluten-free' },
  { key: 'dairy_free', label: 'Dairy-free' },
  { key: 'kosher', label: 'Kosher' },
  { key: 'halal', label: 'Halal' },
]

const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'

/** Shown while starter recipes are prepared after registration (product, hints, tips). */
const REGISTER_LOADING_SENTENCES = [
  'Preparing your 3 starter recipes for your region and diet…',
  'This app uses AI to adapt any recipe to your language and dietary needs.',
  'Tip: Paste a recipe URL and we’ll translate and organize it in your cookbook.',
  'You can adapt any recipe to vegan, kosher, gluten-free, and more with one tap.',
  'Use “What can I make?” to get suggestions from ingredients you have at home.',
  'Your recipes stay in one place — scale servings, save favorites, and add notes.',
  'Starter recipes are from famous cooks and tailored to your country and language.',
  'Tip: Add recipes from blogs or sites — we extract the recipe and add it for you.',
  'Diet filters (e.g. Kosher, vegan) are applied when we suggest and adapt recipes.',
  'Almost there…',
]

const defaultOnboarding = () => ({
  target_country: 'PL',
  target_language: 'en',
  target_city: '',
  target_zip: '',
  dish_preferences: [],
  ui_language: 'en',
  default_servings: 4,
  household_adults: null,
  household_kids: null,
  allergens: [],
  custom_allergens_text: '',
  diet_filters: [],
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
  const turnstileContainerRef = useRef(null)
  const turnstileWidgetIdRef = useRef(null)
  const [locationDetecting, setLocationDetecting] = useState(false)
  const [locationError, setLocationError] = useState(null)
  const [postRegisterPreparing, setPostRegisterPreparing] = useState(false)
  const [loadingSentenceIndex, setLoadingSentenceIndex] = useState(0)

  const set = (key) => (value) => setData((d) => ({ ...d, [key]: value }))

  // Rotate sentence every 3.5s while post-register preparing
  useEffect(() => {
    if (!postRegisterPreparing) return
    setLoadingSentenceIndex(0)
    const interval = setInterval(() => {
      setLoadingSentenceIndex((i) => (i + 1) % REGISTER_LOADING_SENTENCES.length)
    }, 3500)
    return () => clearInterval(interval)
  }, [postRegisterPreparing])

  // Step 1: try geo on mount to pre-fill location
  useEffect(() => {
    if (step !== 1) return
    let cancelled = false
    setLocationDetecting(true)
    setLocationError(null)
    api.get('/meta/geo')
      .then((res) => {
        if (cancelled) return
        if (res?.country_code && COUNTRIES.some((c) => c.code === res.country_code)) {
          setData((d) => ({
            ...d,
            target_country: res.country_code,
            target_city: res.city || d.target_city,
            target_zip: res.zip || d.target_zip,
          }))
        }
      })
      .catch(() => { if (!cancelled) setLocationError(null) })
      .finally(() => { if (!cancelled) setLocationDetecting(false) })
    return () => { cancelled = true }
  }, [step])

  async function detectLocation() {
    setLocationError(null)
    setLocationDetecting(true)
    try {
      const res = await api.get('/meta/geo')
      if (res?.country_code && COUNTRIES.some((c) => c.code === res.country_code)) {
        setData((d) => ({
          ...d,
          target_country: res.country_code,
          target_city: res.city || d.target_city,
          target_zip: res.zip || d.target_zip,
        }))
      }
    } catch (e) {
      setLocationError(e?.message || 'Could not detect location')
    } finally {
      setLocationDetecting(false)
    }
  }

  // Zip-to-city lookup removed from onboarding to keep only language + country.

  // Prepare is triggered when user clicks Next on step 2 so diet_filters (e.g. kosher) are included

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
          dish_preferences: data.dish_preferences,
          default_servings: data.default_servings,
          allergens: data.allergens,
          custom_allergens_text: data.custom_allergens_text || undefined,
          household_adults: data.household_adults,
          household_kids: data.household_kids,
          diet_filters: data.diet_filters,
        }
        await register(email, password, turnstileToken || null, settings, rememberMe)
        if (authTab === 'register') alert(t('verificationEmailSent'))
        // Prepare starter recipes only after account exists; show spinner + rotating sentences
        setAuthLoading(false)
        setPostRegisterPreparing(true)
        try {
          await api.post('/users/me/fetch-starter-recipes')
          await refreshUser?.()
        } catch (_) {
          // Non-blocking: user can fetch from Settings later
        }
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
      {/* Post-register: preparing starter recipes — spinner + rotating sentences */}
      {postRegisterPreparing && (
        <div
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center gap-6 px-4"
          style={{ backgroundColor: 'rgba(17,17,17,0.96)' }}
          aria-live="polite"
          aria-busy="true"
        >
          <span
            className="inline-block w-10 h-10 rounded-full border-2 border-white border-t-transparent animate-spin"
            aria-hidden
          />
          <p
            key={loadingSentenceIndex}
            className="text-center text-white/90 text-lg sm:text-xl max-w-md transition-opacity duration-300"
            style={{ minHeight: '2.5rem' }}
          >
            {REGISTER_LOADING_SENTENCES[loadingSentenceIndex]}
          </p>
        </div>
      )}

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
              <p className="text-white/60 text-sm mt-1">Location, language, and what you like to cook (all optional)</p>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">Location</label>
                <div className="flex gap-2 flex-wrap">
                  <select
                    value={data.target_country}
                    onChange={(e) => set('target_country')(e.target.value)}
                    className={inputCls}
                  >
                    {COUNTRIES.map((c) => (
                      <option key={c.code} value={c.code}>{c.name}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={detectLocation}
                    disabled={locationDetecting}
                    className="rounded-xl px-4 py-3 text-sm font-medium text-stone-900 transition disabled:opacity-50 shrink-0"
                    style={{ backgroundColor: COLORS.accent }}
                  >
                    {locationDetecting ? 'Detecting…' : 'Use my location'}
                  </button>
                </div>
                {locationError && <p className="text-amber-400 text-xs mt-1">{locationError}</p>}
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">App / website language</label>
                <select
                  value={data.ui_language}
                  onChange={(e) => set('ui_language')(e.target.value)}
                  className={inputCls}
                >
                  {TARGET_LANGUAGES.slice(0, 8).map((l) => (
                    <option key={l.code} value={l.code}>{l.name}</option>
                  ))}
                </select>
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
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">What type of recipes interest you? (optional)</label>
                <div className="flex flex-wrap gap-2">
                  {DISH_TYPES.map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => toggleDish(type)}
                      className={`rounded-xl px-3 py-2 text-sm font-medium transition ${
                        data.dish_preferences.includes(type)
                          ? 'text-stone-900'
                          : 'text-white/70 hover:text-white/90 ring-1 ring-white/10 hover:ring-white/20'
                      }`}
                      style={data.dish_preferences.includes(type) ? { backgroundColor: COLORS.accent } : { backgroundColor: 'rgba(0,0,0,0.2)' }}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-8 flex justify-end">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="rounded-xl px-5 py-2.5 text-sm font-semibold text-stone-900 shadow transition hover:opacity-95"
                style={{ backgroundColor: COLORS.accent }}
              >
                Next
              </button>
            </div>
          </>
        )}

        {/* Step 2: Household, allergens, diets */}
        {step === 2 && (
          <>
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white/95">Household & diet</h1>
              <p className="text-white/60 text-sm mt-1">All optional — we’ll use this to tailor recipes and servings. After you create an account, we’ll add 3 starter recipes and apply your diet (e.g. Kosher) to them.</p>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-semibold text-white/80 mb-1.5">Adults (optional)</label>
                  <input
                    type="number"
                    min={0}
                    max={20}
                    value={data.household_adults ?? ''}
                    onChange={(e) => set('household_adults')(e.target.value === '' ? null : parseInt(e.target.value, 10))}
                    placeholder="e.g. 2"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-white/80 mb-1.5">Kids (optional)</label>
                  <input
                    type="number"
                    min={0}
                    max={20}
                    value={data.household_kids ?? ''}
                    onChange={(e) => set('household_kids')(e.target.value === '' ? null : parseInt(e.target.value, 10))}
                    placeholder="e.g. 2"
                    className={inputCls}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">Default servings</label>
                <input
                  type="number"
                  min={1}
                  max={24}
                  value={data.default_servings}
                  onChange={(e) => set('default_servings')(parseInt(e.target.value, 10) || 4)}
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">Allergens to avoid (optional)</label>
                <div className="flex flex-wrap gap-2">
                  {ALLERGENS.map((a) => (
                    <button
                      key={a.code}
                      type="button"
                      onClick={() => toggleAllergen(a.code)}
                      className={`rounded-xl px-3 py-2 text-sm font-medium transition ${
                        data.allergens.includes(a.code) ? 'text-stone-900' : 'text-white/70 ring-1 ring-white/10'
                      }`}
                      style={data.allergens.includes(a.code) ? { backgroundColor: COLORS.accent } : { backgroundColor: 'rgba(0,0,0,0.2)' }}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-1.5">Other things to avoid (optional)</label>
                <input
                  type="text"
                  value={data.custom_allergens_text}
                  onChange={(e) => set('custom_allergens_text')(e.target.value)}
                  placeholder="e.g. kiwi, strawberries"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-white/80 mb-2">Diets (optional)</label>
                <div className="flex flex-wrap gap-2">
                  {DIET_OPTIONS.map((d) => (
                    <button
                      key={d.key}
                      type="button"
                      onClick={() => toggleDiet(d.key)}
                      className={`rounded-xl px-3 py-2 text-sm font-medium transition ${
                        data.diet_filters.includes(d.key) ? 'text-stone-900' : 'text-white/70 ring-1 ring-white/10'
                      }`}
                      style={data.diet_filters.includes(d.key) ? { backgroundColor: COLORS.accent } : { backgroundColor: 'rgba(0,0,0,0.2)' }}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-8 flex justify-between">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="rounded-xl px-4 py-2.5 text-sm font-medium text-white/70 hover:text-white ring-1 ring-white/10 hover:ring-white/20 transition"
              >
                Back
              </button>
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
              <button
                type="submit"
                disabled={authLoading || (authTab === 'register' && !turnstileToken)}
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
