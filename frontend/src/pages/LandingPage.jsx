import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { api, getTrialToken } from '../api/client'
import { COUNTRIES } from '../constants/countries'
import { TARGET_LANGUAGES } from '../constants/languages'
import {
  LANG_STORAGE_KEY,
  TRIAL_DEVICE_ID_KEY,
  TRIAL_RECIPES_KEY,
  TRIAL_REMAINING_KEY,
  TRIAL_SETTINGS_KEY,
} from '../constants/storageKeys'

const COLORS = {
  bg: '#111111',
  card: '#1c1c1c',
  text: '#F8F8F6',
  accent: '#8FAF8F',
  secondary: '#C96A4A',
}

/** Website UI language options (app supports en, he, pl). */
const WEBSITE_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'pl', name: 'Polski' },
  { code: 'he', name: 'עברית' },
]

const FOOD_IMAGES = [
  'https://images.unsplash.com/photo-1473093226795-af9932fe5856?auto=format&fit=crop&w=900&q=70',
  'https://images.unsplash.com/photo-1543353071-087092ec393a?auto=format&fit=crop&w=900&q=70',
  'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=900&q=70',
]

function cn(...xs) {
  return xs.filter(Boolean).join(' ')
}

function Anchor({ id }) {
  return <span id={id} className="block scroll-mt-24" />
}

function TrialFormModal({ onClose, onSubmit, error }) {
  const [form, setForm] = useState({
    website_language: 'en',
    recipe_language: 'en',
    country: 'US',
  })
  const [geoLoading, setGeoLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    api.get('/meta/geo')
      .then((data) => {
        if (cancelled || !data?.country_code) return
        const code = (data.country_code || '').toUpperCase()
        if (code) setForm((f) => ({ ...f, country: code }))
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setGeoLoading(false) })
    return () => { cancelled = true }
  }, [])

  const countryOptions = useMemo(() => {
    const list = [...COUNTRIES]
    const hasCode = (code) => list.some((c) => c.code === code)
    if (form.country && !hasCode(form.country)) {
      list.push({ code: form.country, name: `${form.country} (detected)` })
    }
    return list
  }, [form.country])

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    onSubmit(form, () => setSubmitting(false))
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(17,17,17,0.9)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="trial-form-title"
    >
      <div
        className="w-full max-w-md rounded-2xl p-6 shadow-xl border border-white/10"
        style={{ backgroundColor: COLORS.card }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="trial-form-title" className="text-xl font-bold text-white mb-4">
          Start your free trial
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-white/80 mb-1.5">Website language</label>
            <select
              value={form.website_language}
              onChange={(e) => setForm((f) => ({ ...f, website_language: e.target.value }))}
              className="w-full rounded-xl px-4 py-2.5 text-sm bg-white/5 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-offset-0 focus:ring-white/30"
            >
              {WEBSITE_LANGUAGES.map((opt) => (
                <option key={opt.code} value={opt.code}>{opt.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-white/80 mb-1.5">Recipe language</label>
            <select
              value={form.recipe_language}
              onChange={(e) => setForm((f) => ({ ...f, recipe_language: e.target.value }))}
              className="w-full rounded-xl px-4 py-2.5 text-sm bg-white/5 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-offset-0 focus:ring-white/30"
            >
              {TARGET_LANGUAGES.map((opt) => (
                <option key={opt.code} value={opt.code}>{opt.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-white/80 mb-1.5">
              Country {geoLoading && <span className="text-white/50">(detecting…)</span>}
            </label>
            <select
              value={form.country}
              onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))}
              className="w-full rounded-xl px-4 py-2.5 text-sm bg-white/5 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-offset-0 focus:ring-white/30"
            >
              {countryOptions.map((opt) => (
                <option key={opt.code} value={opt.code}>{opt.name}</option>
              ))}
            </select>
          </div>
          {error && <p className="text-sm text-red-300" role="alert">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl px-4 py-2.5 text-sm font-semibold border border-white/20 text-white/90 hover:bg-white/10 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-xl px-4 py-2.5 text-sm font-bold text-black shadow transition hover:opacity-95 disabled:opacity-60"
              style={{ backgroundColor: COLORS.accent }}
            >
              {submitting ? 'Starting…' : 'Start trial'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function LandingPage() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showTrialForm, setShowTrialForm] = useState(false)
  const [trialError, setTrialError] = useState('')
  const year = useMemo(() => new Date().getFullYear(), [])
  const navigate = useNavigate()
  const { setTrialToken } = useAuth()
  const { setLang } = useLanguage()

  async function handleTryForFree() {
    setTrialError('')
    const existingToken = getTrialToken()
    if (existingToken) {
      try {
        const stored = localStorage.getItem(TRIAL_RECIPES_KEY)
        const trialRecipes = stored ? JSON.parse(stored) : []
        const remainingStr = localStorage.getItem(TRIAL_REMAINING_KEY)
        const remaining = remainingStr != null ? parseInt(remainingStr, 10) : 5
        const remainingActions = Number.isFinite(remaining) && remaining >= 0 ? remaining : 5
        setTrialToken(existingToken, remainingActions)
        navigate('/', { state: { trialRecipes, remainingActions }, replace: true })
      } catch (_) {
        setTrialError('Could not restore trial.')
      }
      return
    }
    setShowTrialForm(true)
  }

  async function handleTrialFormSubmit(form, onDone) {
    setTrialError('')
    try {
      const deviceId = typeof localStorage !== 'undefined' ? localStorage.getItem(TRIAL_DEVICE_ID_KEY) : null
      const body = deviceId
        ? { device_id: deviceId }
        : { country: form.country, language: form.recipe_language }
      const data = await api.post('/trial/start', body)
      setTrialToken(data.trial_token, data.remaining_actions ?? 5)
      try {
        localStorage.setItem(TRIAL_RECIPES_KEY, JSON.stringify([]))
        localStorage.setItem(TRIAL_REMAINING_KEY, String(data.remaining_actions ?? 5))
        if (data.device_id) localStorage.setItem(TRIAL_DEVICE_ID_KEY, data.device_id)
        const trialSettings = {
          ui_language: form.website_language,
          target_language: form.recipe_language,
          target_country: form.country,
        }
        localStorage.setItem(TRIAL_SETTINGS_KEY, JSON.stringify(trialSettings))
        setLang(form.website_language)
        localStorage.setItem(LANG_STORAGE_KEY, form.website_language || 'en')
      } catch (_) {}
      setShowTrialForm(false)
      navigate('/', { state: { trialRecipes: [], remainingActions: data.remaining_actions }, replace: true })
    } catch (err) {
      setTrialError(err?.message || 'Could not start trial. Is the backend running?')
    } finally {
      onDone?.()
    }
  }

  useEffect(() => {
    document.documentElement.style.scrollBehavior = 'smooth'
  }, [])

  return (
    <div className="min-h-screen" style={{ backgroundColor: COLORS.bg, color: COLORS.text }}>
      {showTrialForm && (
        <TrialFormModal
          onClose={() => { setShowTrialForm(false); setTrialError('') }}
          onSubmit={handleTrialFormSubmit}
          error={trialError}
        />
      )}

      {/* Global background accents (kept subtle, below the hero image) */}
      <div aria-hidden="true" className="fixed inset-0 -z-20 overflow-hidden">
        <div
          className="absolute top-[40%] -left-48 h-[560px] w-[560px] rounded-full blur-3xl"
          style={{ backgroundColor: COLORS.secondary, opacity: 0.12 }}
        />
        <div
          className="absolute -bottom-56 right-[-180px] h-[640px] w-[640px] rounded-full blur-3xl"
          style={{ backgroundColor: COLORS.accent, opacity: 0.1 }}
        />
      </div>

      {/* Navbar */}
      <header className="sticky top-0 z-50 backdrop-blur bg-black/45 border-b border-white/5">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center justify-between gap-4">
            <Link to="/" className="flex items-center gap-2 min-w-0">
              <span
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl ring-1 ring-white/10 shadow"
                style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
              >
                <span className="text-lg">🍽️</span>
              </span>
              <span className="font-extrabold tracking-tight truncate">
                Intelligent Kitchen Helper
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-6 text-sm text-white/75">
              <a href="#features" className="hover:text-white transition-colors">Features</a>
              <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
              <Link to="/signin" className="hover:text-white transition-colors">Sign In</Link>
            </nav>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => { setMobileOpen(false); handleTryForFree() }}
                className="hidden sm:inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold text-black shadow transition hover:opacity-95"
                style={{ backgroundColor: COLORS.accent }}
              >
                Try for free
              </button>
              <Link
                to="/register"
                className="hidden sm:inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold ring-1 ring-white/10 hover:bg-white/10 transition"
              >
                Register
              </Link>
              <button
                type="button"
                onClick={() => setMobileOpen(v => !v)}
                className="md:hidden inline-flex items-center justify-center rounded-xl px-3 py-2 ring-1 ring-white/10 hover:bg-white/10 transition"
                style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
                aria-label="Open menu"
                aria-expanded={mobileOpen ? 'true' : 'false'}
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          </div>

          {mobileOpen && (
            <div className="md:hidden pb-4">
              <div
                className="mt-2 grid gap-2 rounded-2xl ring-1 ring-white/10 p-3"
                style={{ backgroundColor: 'rgba(28,28,28,0.65)' }}
              >
                <a onClick={() => setMobileOpen(false)} href="#features" className="rounded-xl px-3 py-2 text-sm text-white/80 hover:bg-white/5 hover:text-white transition">Features</a>
                <a onClick={() => setMobileOpen(false)} href="#pricing" className="rounded-xl px-3 py-2 text-sm text-white/80 hover:bg-white/5 hover:text-white transition">Pricing</a>
                <Link onClick={() => setMobileOpen(false)} to="/signin" className="rounded-xl px-3 py-2 text-sm text-white/80 hover:bg-white/5 hover:text-white transition">Sign In</Link>
                <Link
                  onClick={() => setMobileOpen(false)}
                  to="/register"
                  className="mt-1 inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold text-black shadow"
                  style={{ backgroundColor: COLORS.accent }}
                >
                  Register
                </Link>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Hero - food-first with strong overlay for readability */}
      <section
        className="relative overflow-hidden"
        style={{
          backgroundImage: `url(${FOOD_IMAGES[0]})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-black/80 via-black/85 to-black/90" />
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24 pb-16 sm:pb-24">
          <div className="max-w-2xl rounded-3xl bg-black/60 backdrop-blur-sm px-5 sm:px-7 py-6 sm:py-8 shadow-xl shadow-black/40">
            <div
              className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs text-white/80 ring-1 ring-white/10"
              style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
            >
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: COLORS.accent }} />
              Your intelligent kitchen helper
            </div>

            <h1 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight">
              <span style={{ color: COLORS.accent }}>Intelligent Kitchen Helper</span>
            </h1>

            <p className="mt-5 text-base sm:text-lg text-white/80 max-w-xl">
              AI adapts recipes to your language, diet, and ingredients. One cookbook, one shopping list.
            </p>

            <div className="mt-7 flex flex-col sm:flex-row gap-3 sm:items-center">
              <button
                type="button"
                onClick={handleTryForFree}
                className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-extrabold text-black shadow-soft transition hover:opacity-95"
                style={{ backgroundColor: COLORS.accent }}
              >
                Try for free
              </button>
              <Link
                to="/register"
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold text-black/90 shadow-soft transition hover:opacity-95"
                style={{ backgroundColor: 'rgba(255,255,255,0.2)' }}
              >
                Register
              </Link>
              <Link
                to="/signin"
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold ring-1 ring-white/10 hover:bg-white/10 transition"
                style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}
              >
                Sign In
              </Link>
            </div>
            {trialError && <p className="mt-2 text-sm text-red-300" role="alert">{trialError}</p>}

            <p className="mt-3 text-xs text-white/70">
              Free to start — includes <span className="text-white font-semibold">5 AI recipe adaptations</span>.
            </p>

            <div className="mt-6 grid gap-2 text-xs text-white/80">
              {[
                'Works with the food you can buy',
                'Understands your diet and family needs',
                'Keeps all your recipes in one simple place',
              ].map((s) => (
                <div key={s} className="inline-flex items-center gap-2">
                  <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: COLORS.accent }} />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* How it helps you */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-14 sm:mt-20">
        <Anchor id="how" />
        <div className="max-w-2xl">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">How it makes life easier</h2>
          <p className="mt-3 text-white/70">
            Intelligent Kitchen Helper adapts recipes to your kitchen, diet, and ingredients — so you can cook with what you have.
          </p>
        </div>

        <div className="mt-8 grid md:grid-cols-3 gap-5">
          {[
            {
              icon: '🛒',
              title: 'Matches your ingredients',
              body: 'Swaps hard-to-find items with local ingredients you can actually buy.',
            },
            {
              icon: '🥗',
              title: 'Matches your diet',
              body: 'Adapts recipes for vegan, gluten-free, kosher and more without guesswork.',
            },
            {
              icon: '📖',
              title: 'Keeps you organized',
              body: 'One simple recipe book with a unified shopping list across recipes.',
            },
          ].map((c) => (
            <div
              key={c.title}
              className="rounded-2xl p-6 ring-1 ring-white/10 shadow-soft"
              style={{ backgroundColor: COLORS.card }}
            >
              <div className="flex items-center gap-3">
                <span
                  className="inline-flex h-10 w-10 items-center justify-center rounded-xl ring-1 ring-white/10"
                  style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
                >
                  {c.icon}
                </span>
                <div className="font-semibold">{c.title}</div>
              </div>
              <p className="mt-3 text-sm text-white/70">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* What it does in 3 steps */}
      <section id="features" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24">
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div className="max-w-2xl">
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">What it does in 3 simple steps</h2>
            <p className="mt-3 text-white/70">
              From a recipe you found online to something you can cook tonight, with one shopping list.
            </p>
          </div>
            <Link
              to="/register"
              className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold text-black shadow-soft transition hover:opacity-95 w-full sm:w-auto"
              style={{ backgroundColor: COLORS.accent }}
            >
              Register
            </Link>
        </div>

        <div className="mt-8 grid md:grid-cols-3 gap-5">
          {[
            {
              icon: '🔗',
              title: '1. Import recipe',
              body: 'Paste a URL or text. We extract the ingredients and steps for you.',
            },
            {
              icon: '✨',
              title: '2. AI adapts to you',
              body: 'Tell it your diet and country. Your intelligent helper adjusts the recipe to match your reality.',
            },
            {
              icon: '🧺',
              title: '3. Get shopping list',
              body: 'Combine recipes into one clean shopping list you can actually use.',
            },
          ].map((c) => (
            <div
              key={c.title}
              className="rounded-2xl p-6 ring-1 ring-white/10 shadow-soft hover:shadow-soft2 transition"
              style={{ backgroundColor: COLORS.card }}
            >
              <div className="text-sm font-semibold flex items-center gap-2">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
                  {c.icon}
                </span>
                {c.title}
              </div>
              <p className="mt-3 text-sm text-white/70">{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24">
        <div className="max-w-2xl">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Pricing</h2>
          <p className="mt-3 text-white/70">Start free. Upgrade when you want unlimited AI features.</p>
        </div>

        <div className="mt-8 grid lg:grid-cols-2 gap-5">
          <div className="rounded-2xl p-7 ring-1 ring-white/10 shadow-soft hover:shadow-soft2 transition" style={{ backgroundColor: COLORS.card }}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-bold">Free</div>
                <div className="mt-1 text-sm text-white/70">Perfect to try it out</div>
              </div>
              <div className="text-2xl font-extrabold">$0</div>
            </div>
            <ul className="mt-6 space-y-3 text-sm text-white/75">
              <li className="flex items-start gap-2"><span style={{ color: COLORS.accent }}>✓</span> Save recipes</li>
              <li className="flex items-start gap-2"><span style={{ color: COLORS.accent }}>✓</span> <span className="text-white font-semibold">5 AI adaptations</span></li>
              <li className="flex items-start gap-2"><span style={{ color: COLORS.accent }}>✓</span> Unified shopping list</li>
            </ul>
            <Link
              to="/register"
              className="mt-7 inline-flex w-full items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold text-black shadow-soft transition hover:opacity-95"
              style={{ backgroundColor: COLORS.accent }}
            >
              Register
            </Link>
            <p className="mt-3 text-xs text-white/55 text-center">No credit card required.</p>
          </div>

          <div className="relative overflow-hidden rounded-2xl p-7 ring-1 ring-white/10 shadow-soft hover:shadow-soft2 transition" style={{ backgroundColor: COLORS.card }}>
            <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full blur-3xl" style={{ backgroundColor: COLORS.secondary, opacity: 0.18 }} />
            <div className="relative flex items-center justify-between">
              <div>
                <div className="inline-flex items-center gap-2">
                  <div className="text-lg font-bold">Pro</div>
                  <span className="rounded-full px-2 py-0.5 text-xs font-semibold ring-1" style={{ backgroundColor: 'rgba(201,106,74,0.18)', color: COLORS.secondary, borderColor: 'rgba(201,106,74,0.35)' }}>
                    Unlimited
                  </span>
                </div>
                <div className="mt-1 text-sm text-white/70">For power users and families</div>
              </div>
              <div className="text-2xl font-extrabold">∞</div>
            </div>
            <ul className="relative mt-6 space-y-3 text-sm text-white/75">
              <li className="flex items-start gap-2"><span style={{ color: COLORS.secondary }}>✓</span> Unlimited AI adaptations</li>
              <li className="flex items-start gap-2"><span style={{ color: COLORS.secondary }}>✓</span> Advanced ingredient substitutions</li>
              <li className="flex items-start gap-2"><span style={{ color: COLORS.secondary }}>✓</span> Faster AI processing</li>
            </ul>
            <Link
              to="/onboarding"
              className="relative mt-7 inline-flex w-full items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold ring-1 ring-white/10 hover:bg-white/10 transition"
              style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
            >
              Upgrade to Pro
            </Link>
            <p className="mt-3 text-xs text-white/55 text-center">Cancel anytime.</p>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-24 pb-16 sm:pb-24">
        <div
          className="rounded-2xl p-7 sm:p-10 ring-1 ring-white/10 shadow-soft"
          style={{ background: `linear-gradient(90deg, rgba(143,175,143,0.16), rgba(28,28,28,1), rgba(201,106,74,0.16))` }}
        >
          <div className="grid lg:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Your intelligent kitchen helper</h2>
              <p className="mt-3 text-white/70">Let AI adapt recipes to your kitchen, diet, and ingredients.</p>
              <p className="mt-2 text-xs text-white/60">No credit card required.</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 sm:justify-end">
              <Link
                to="/register"
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-extrabold text-black shadow-soft transition hover:opacity-95"
                style={{ backgroundColor: COLORS.accent }}
              >
                Register
              </Link>
              <Link
                to="/signin"
                className="inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold ring-1 ring-white/10 hover:bg-white/10 transition"
                style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
              >
                Sign In
              </Link>
            </div>
          </div>
          <div className="mt-6 text-xs text-white/55">
            Credits: Free includes 5 AI adaptations. Some AI actions use credits, clearly marked. Pro includes unlimited AI features.
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-black/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl ring-1 ring-white/10" style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
                🍽️
              </span>
              <div>
                <div className="font-extrabold">Intelligent Kitchen Helper</div>
                <div className="text-xs text-white/55">AI recipe adaptation for real kitchens.</div>
              </div>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/70">
              <a href="#features" className="hover:text-white transition-colors">Features</a>
              <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
              <a href="#privacy" className="hover:text-white transition-colors">Privacy</a>
              <a href="#contact" className="hover:text-white transition-colors">Contact</a>
            </div>
          </div>
          <div className="mt-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 text-xs text-white/55">
            <div id="privacy">Privacy: we don’t sell your data or recipes.</div>
            <div id="contact">Contact: tshprung@gmail.com</div>
          </div>
          <div className="mt-6 text-xs text-white/45">© {year} Intelligent Kitchen Helper (myrecipes.cloud). All rights reserved.</div>
        </div>
      </footer>
    </div>
  )
}

