import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { api } from '../api/client'
import { TARGET_LANGUAGES, COUNTRIES, ALLERGENS, TRIAL_SETTINGS_KEY, LANG_STORAGE_KEY } from '../constants'

function Field({ label, hint, value, onChange }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-stone-600 mb-1.5">
        {label}
        {hint && <span className="ml-1.5 text-xs font-normal text-stone-400">({hint})</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
      />
    </div>
  )
}

function SettingsCard({ icon, title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-stone-100 bg-stone-50">
        <span className="text-xl">{icon}</span>
        <h3 className="text-sm font-bold text-stone-600 uppercase tracking-widest">{title}</h3>
      </div>
      <div className="p-5 space-y-4">
        {children}
      </div>
    </div>
  )
}

export default function SettingsPage() {
  const { user, trialToken, setUser, logout, refreshUser } = useAuth()
  const { t, lang, setLang } = useLanguage()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    ui_language: user?.ui_language ?? 'en',
    target_language: user?.target_language ?? 'pl',
    target_country:  user?.target_country  ?? 'PL',
    target_city:     user?.target_city     ?? 'Wrocław',
    target_zip:      user?.target_zip      ?? '',
    dish_preferences: user?.dish_preferences ?? [],
    household_adults: user?.household_adults ?? null,
    household_kids: user?.household_kids ?? null,
    diet_filters: user?.diet_filters ?? [],
    default_servings: user?.default_servings ?? 1,
    allergens: user?.allergens ?? [],
    custom_allergens_text: user?.custom_allergens_text ?? '',
  })
  const [zipStatus, setZipStatus] = useState(null) // null | 'loading' | 'ok' | 'error'
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)
  const [error, setError]   = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [fetchStarterLoading, setFetchStarterLoading] = useState(false)
  const [fetchStarterMessage, setFetchStarterMessage] = useState(null)

  const set = key => v => setForm(f => ({ ...f, [key]: v }))

  // Sync form from user when user loads/updates (fixes wrong default when user had e.g. English saved)
  useEffect(() => {
    if (user) {
      setForm({
        ui_language: user.ui_language ?? 'en',
        target_language: user.target_language ?? 'pl',
        target_country: user.target_country ?? 'PL',
        target_city: user.target_city ?? 'Wrocław',
        target_zip: user.target_zip ?? '',
        dish_preferences: user.dish_preferences ?? [],
        household_adults: user.household_adults ?? null,
        household_kids: user.household_kids ?? null,
        diet_filters: user.diet_filters ?? [],
        default_servings: user.default_servings ?? 1,
        allergens: user.allergens ?? [],
        custom_allergens_text: user.custom_allergens_text ?? '',
      })
      return
    }
    if (trialToken) {
      try {
        const raw = localStorage.getItem(TRIAL_SETTINGS_KEY)
        if (raw) {
          const saved = JSON.parse(raw)
          setForm(prev => ({
            ...prev,
            ui_language: saved.ui_language ?? prev.ui_language,
            target_language: saved.target_language ?? prev.target_language,
            target_country: saved.target_country ?? prev.target_country,
            target_city: saved.target_city ?? prev.target_city,
            target_zip: saved.target_zip ?? prev.target_zip,
            dish_preferences: Array.isArray(saved.dish_preferences) ? saved.dish_preferences : prev.dish_preferences,
            household_adults: saved.household_adults ?? prev.household_adults,
            household_kids: saved.household_kids ?? prev.household_kids,
            diet_filters: Array.isArray(saved.diet_filters) ? saved.diet_filters : prev.diet_filters,
            default_servings: saved.default_servings ?? prev.default_servings,
            allergens: Array.isArray(saved.allergens) ? saved.allergens : prev.allergens,
            custom_allergens_text: saved.custom_allergens_text ?? prev.custom_allergens_text,
          }))
        }
      } catch (_) {}
    }
  }, [user?.id, user?.ui_language, user?.target_language, user?.target_country, user?.target_city, user?.target_zip, user?.dish_preferences, user?.household_adults, user?.household_kids, user?.diet_filters, user?.default_servings, user?.allergens, user?.custom_allergens_text, trialToken])

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      if (!user && trialToken) {
        try {
          localStorage.setItem(TRIAL_SETTINGS_KEY, JSON.stringify(form))
          if (form.ui_language && form.ui_language !== lang) setLang(form.ui_language)
          localStorage.setItem(LANG_STORAGE_KEY, form.ui_language || 'en')
        } catch (_) {}
        setSaved(true)
        setTimeout(() => setSaved(false), 2500)
        setSaving(false)
        return
      }
      const updated = await api.patch('/users/me/settings', form)
      setUser(updated)
      if (updated?.ui_language && updated.ui_language !== lang) {
        setLang(updated.ui_language)
      }
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function resolveZipToCity() {
    const zip = (form.target_zip || '').trim()
    const country = (form.target_country || '').trim()
    if (!zip || !country) return
    setZipStatus('loading')
    try {
      const data = await api.get(`/meta/resolve-city?country=${encodeURIComponent(country)}&zip=${encodeURIComponent(zip)}`)
      if (data?.city) setForm(f => ({ ...f, target_city: data.city }))
      setZipStatus('ok')
      setTimeout(() => setZipStatus(null), 2000)
    } catch (_) {
      setZipStatus('error')
      setTimeout(() => setZipStatus(null), 3500)
    }
  }

  return (
    <div className="max-w-lg">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-stone-800">{t('settings')}</h2>
        <p className="text-stone-400 text-sm mt-1">{t('translationAndLocation')}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <SettingsCard icon="🗣️" title={t('language')}>
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('appLanguage')}</label>
            <select
              value={form.ui_language}
              onChange={e => setForm(f => ({ ...f, ui_language: e.target.value }))}
              className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
            >
              <option value="en">English</option>
              <option value="he">עברית</option>
              <option value="pl">Polski</option>
            </select>
          </div>
        </SettingsCard>

        <SettingsCard icon="🌐" title={t('translateTo')}>
          <p className="text-sm text-stone-500 mb-3">Choose the language and country you want recipes adapted for.</p>
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('recipeLanguage')}</label>
            <select
              value={form.target_language}
              onChange={e => setForm(f => ({ ...f, target_language: e.target.value }))}
              className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
            >
              {TARGET_LANGUAGES.map(l => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('country')}</label>
            <select
              value={form.target_country}
              onChange={e => setForm(f => ({ ...f, target_country: e.target.value }))}
              className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
            >
              {COUNTRIES.map(c => (
                <option key={c.code} value={c.code}>{c.name}</option>
              ))}
            </select>
          </div>
        </SettingsCard>

        <SettingsCard icon="👨‍👩‍👧‍👦" title={t('cookingAndDiet')}>
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-1.5">
              {t('defaultServingsLabel')}
              <span className="ml-1.5 text-xs font-normal text-stone-400">({t('people')})</span>
            </label>
            <input
              type="number"
              min={1}
              max={24}
              value={form.default_servings}
              onChange={e => setForm(f => ({ ...f, default_servings: parseInt(e.target.value || '1', 10) }))}
              className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
            />
            <p className="text-xs text-stone-400 mt-1.5">
              {t('defaultServingsHint')}
            </p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-2">
              {t('allergensToAvoid')}
              <span className="ml-1.5 text-xs font-normal text-stone-400">({t('optional')})</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              {ALLERGENS.map(a => {
                const checked = (form.allergens || []).includes(a.code)
                return (
                  <label
                    key={a.code}
                    className="flex items-center gap-2 rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-700 cursor-pointer hover:bg-white transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={e => {
                        const next = e.target.checked
                          ? Array.from(new Set([...(form.allergens || []), a.code]))
                          : (form.allergens || []).filter(x => x !== a.code)
                        setForm(f => ({ ...f, allergens: next }))
                      }}
                      className="rounded border-stone-300 text-amber-600 focus:ring-amber-400"
                    />
                    <span>{a.label}</span>
                  </label>
                )
              })}
            </div>
            <div className="mt-3">
              <label className="block text-sm font-semibold text-stone-600 mb-1.5">
                {t('otherAllergens')}
                <span className="ml-1.5 text-xs font-normal text-stone-400">({t('optional')})</span>
              </label>
              <textarea
                value={form.custom_allergens_text}
                onChange={e => setForm(f => ({ ...f, custom_allergens_text: e.target.value }))}
                rows={3}
                className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
                placeholder={t('otherAllergensPlaceholder')}
              />
              <p className="text-xs text-stone-400 mt-1.5">{t('otherAllergensHint')}</p>
            </div>
          </div>
        </SettingsCard>

        <p className="text-xs text-stone-400 px-1">
          Changes affect recipes you add next, diet adaptations you run next, and re-localizations you run next.
        </p>

        {error && (
          <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
            <span>⚠️</span> {error}
          </div>
        )}

        <div className="flex items-center gap-4 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="bg-amber-500 hover:bg-amber-600 text-white rounded-xl px-6 py-2.5 text-sm font-bold disabled:opacity-50 transition-all hover:shadow-lg hover:shadow-amber-200 active:scale-95"
          >
            {saving ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {t('saving')}
              </span>
            ) : t('saveSettings')}
          </button>
          {saved && (
            <span className="text-sm text-emerald-600 font-semibold flex items-center gap-1">
              ✓ {t('saved')}
            </span>
          )}
        </div>
      </form>

      {/* Account info + admin actions (only for registered users, not pure trial) */}
      {user && (
        <>
          <div className="mt-8 bg-white rounded-2xl border border-stone-100 shadow-sm p-5">
            <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest mb-3">{t('account')}</h3>
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-bold">
                  {user.email?.[0]?.toUpperCase()}
                </div>
                <div>
                  <p className="text-sm font-semibold text-stone-700">{user.email}</p>
                  <p className="text-xs text-stone-400">
                    {t('joined')}: {user.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'}
                  </p>
                  <p className="text-xs text-stone-400 mt-1">
                    {user.is_verified ? t('verified') : t('unverified')}
                  </p>
                </div>
              </div>
              {!user.is_verified && (
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await api.post('/auth/resend-verification')
                      alert(t('resendVerification'))
                    } catch (err) {
                      alert(err.message || t('verifyError'))
                    }
                  }}
                  className="text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-xl px-3 py-2 transition-colors"
                >
                  {t('resendVerification')}
                </button>
              )}
            </div>
          </div>

          {/* Fetch starter recipes */}
          <div className="mt-8 bg-white rounded-2xl border border-stone-100 shadow-sm p-5">
            <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest mb-2">{t('fetchStarterRecipes')}</h3>
            <p className="text-sm text-stone-600 mb-3">
              {t('fetchStarterRecipesHint')}
            </p>
            {fetchStarterMessage && (
              <p className={`text-sm mb-3 ${fetchStarterMessage.success ? 'text-emerald-600' : 'text-amber-600'}`}>
                {fetchStarterMessage.text}
              </p>
            )}
            <button
              type="button"
              disabled={fetchStarterLoading}
              onClick={async () => {
                setFetchStarterLoading(true)
                setFetchStarterMessage(null)
                try {
                  await api.post('/users/me/fetch-starter-recipes')
                  setFetchStarterMessage({ success: true, text: t('fetchStarterRecipesDone') })
                  refreshUser?.()
                } catch (err) {
                  setFetchStarterMessage({ success: false, text: err.message || t('somethingWentWrong') })
                } finally {
                  setFetchStarterLoading(false)
                }
              }}
              className="bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-xl px-5 py-2.5 text-sm font-semibold transition"
            >
              {fetchStarterLoading ? t('loading') : t('fetchStarterRecipesButton')}
            </button>
          </div>

          {/* Delete account */}
          <div className="mt-8 bg-white rounded-2xl border border-red-100 shadow-sm p-5">
            <h3 className="text-xs font-bold text-red-500 uppercase tracking-widest mb-3">{t('deleteAccount')}</h3>
            <p className="text-sm text-stone-600 mb-3">
              {t('deleteAccountConfirm')}
            </p>
            <div className="space-y-3">
              <p className="text-sm text-stone-600">
                {t('typeDelete')}
              </p>
              <input
                type="text"
                value={deleteConfirm}
                onChange={e => setDeleteConfirm(e.target.value)}
                placeholder="DELETE"
                className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent"
              />
              {deleteError && (
                <p className="text-sm text-red-600">{deleteError}</p>
              )}
              <button
                type="button"
                disabled={deleteConfirm !== 'DELETE' || deleting}
                onClick={async () => {
                  if (deleteConfirm !== 'DELETE') return
                  setDeleting(true)
                  setDeleteError('')
                  try {
                    await api.delete('/users/me')
                    logout()
                    navigate('/', { replace: true })
                  } catch (err) {
                    setDeleteError(err.message || t('verifyError'))
                  } finally {
                    setDeleting(false)
                  }
                }}
                className="bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-6 py-2.5 text-sm font-bold transition-all hover:shadow-lg hover:shadow-red-200 active:scale-95"
              >
                {deleting ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    {t('deleting')}
                  </span>
                ) : t('deleteAccountButton')}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
