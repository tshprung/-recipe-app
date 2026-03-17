import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { useShoppingList } from '../context/ShoppingListContext'
import { DIET_OPTIONS, TIME_OPTIONS } from '../constants'
import { getErrorMessage } from '../utils/errors'

export default function MealPlanPage() {
  const { t } = useLanguage()
  const { user, trialToken, refreshUser } = useAuth()
  const { refreshRecipeIds } = useShoppingList()
  const [plan, setPlan] = useState(null)
  const [loadingLatest, setLoadingLatest] = useState(true)
  const [generateLoading, setGenerateLoading] = useState(false)
  const [replaceIndex, setReplaceIndex] = useState(null)
  const [addToListLoading, setAddToListLoading] = useState(false)
  const [error, setError] = useState(null)
  const [addListSuccess, setAddListSuccess] = useState(false)

  // Form state for generating
  const [numDays, setNumDays] = useState(7)
  const [dietFilters, setDietFilters] = useState(() => user?.diet_filters ?? [])
  const [maxTime, setMaxTime] = useState(null)
  const [budget, setBudget] = useState('')

  useEffect(() => {
    // Meal plans are currently for logged-in users only.
    if (!user) {
      setPlan(null)
      setLoadingLatest(false)
      return
    }
    api
      .get('/meal-plan/latest')
      .then(data => setPlan(data))
      .catch(() => setPlan(null))
      .finally(() => setLoadingLatest(false))
  }, [user])

  useEffect(() => {
    if (user?.diet_filters && dietFilters.length === 0) setDietFilters(user.diet_filters)
  }, [user?.diet_filters])

  function toggleDiet(key) {
    setDietFilters(prev => (prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]))
  }

  function handleGenerate(e) {
    e.preventDefault()
    setError(null)
    setGenerateLoading(true)
    api
      .post('/meal-plan/generate', {
        num_days: numDays,
        diet_filters: dietFilters.length ? dietFilters : null,
        max_time_minutes: maxTime || null,
        budget: budget.trim() || null,
      })
      .then(data => {
        setPlan(data)
        refreshUser()
      })
      .catch(e => setError(getErrorMessage(e, t)))
      .finally(() => setGenerateLoading(false))
  }

  function handleReplaceDay(dayIndex) {
    setError(null)
    setReplaceIndex(dayIndex)
    api
      .post(`/meal-plan/${plan.id}/replace-day`, { day_index: dayIndex })
      .then(data => {
        setPlan(data)
        refreshUser()
      })
      .catch(e => setError(getErrorMessage(e, t)))
      .finally(() => setReplaceIndex(null))
  }

  function handleAddAllToShoppingList() {
    setError(null)
    setAddListSuccess(false)
    setAddToListLoading(true)
    api
      .post(`/meal-plan/${plan.id}/add-to-shopping-list`)
      .then(() => {
        setAddListSuccess(true)
        refreshRecipeIds?.()
        refreshUser()
      })
      .catch(e => setError(getErrorMessage(e, t)))
      .finally(() => setAddToListLoading(false))
  }

  if (loadingLatest) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="w-10 h-10 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!user && trialToken) {
    return (
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-stone-50 mb-1">{t('mealPlanTitle')}</h1>
        <p className="text-stone-400 text-sm mb-6">{t('mealPlanHint')}</p>
        <div className="bg-stone-900/60 border border-white/10 rounded-2xl p-5">
          <p className="text-sm text-stone-200 font-semibold mb-1">
            {t('signInToSeeMergedIngredients')}
          </p>
          <p className="text-xs text-stone-400">
            Meal planning is available for registered accounts (so we can save your plan and build a full shopping list).
          </p>
          <div className="mt-4 flex flex-col sm:flex-row gap-2">
            <Link
              to="/register"
              className="inline-flex justify-center rounded-xl px-4 py-3 text-sm font-semibold text-black bg-amber-400 hover:bg-amber-300 transition"
            >
              {t('register')}
            </Link>
            <Link
              to="/signin"
              className="inline-flex justify-center rounded-xl px-4 py-3 text-sm font-semibold ring-1 ring-white/10 hover:bg-white/10 transition text-stone-50"
              style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
            >
              {t('signIn')}
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-stone-50 mb-1">{t('mealPlanTitle')}</h1>
      <p className="text-stone-400 text-sm mb-6">{t('mealPlanHint')}</p>

      {plan?.days?.length > 0 ? (
        <>
          <div className="space-y-4 mb-8">
            {plan.days.map((day, idx) => (
              <div
                key={day.date}
                className="bg-white rounded-2xl border border-stone-100 shadow-sm p-4 text-stone-800"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-1">
                      {day.date}
                    </p>
                    <h3 className="font-bold text-lg text-stone-800">{day.meal.name}</h3>
                    {day.meal.short_description && (
                      <p className="text-sm text-stone-600 mt-1">{day.meal.short_description}</p>
                    )}
                    <p className="text-xs text-stone-500 mt-1">
                      ~{day.meal.estimated_time_minutes} min
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleReplaceDay(idx)}
                    disabled={replaceIndex !== null}
                    className="flex-shrink-0 px-3 py-1.5 rounded-xl text-sm font-medium bg-stone-100 text-stone-600 hover:bg-stone-200 disabled:opacity-50"
                  >
                    {replaceIndex === idx ? '…' : t('replaceMeal')}
                  </button>
                </div>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={handleAddAllToShoppingList}
            disabled={addToListLoading}
            className="w-full min-h-[48px] bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-xl font-bold text-sm transition-colors"
          >
            {addToListLoading ? '…' : t('addAllToShoppingList')}
          </button>
          {addListSuccess && (
            <p className="text-sm text-amber-400 mt-2">{t('addedToShoppingList')}</p>
          )}
        </>
      ) : (
        <>
          <p className="text-stone-400 text-sm mb-4">{t('noMealPlan')}</p>
          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-stone-300 mb-1.5">
                {t('numDays')}
              </label>
              <select
                value={numDays}
                onChange={e => setNumDays(Number(e.target.value))}
                className="w-full bg-stone-800 border border-stone-600 rounded-xl px-4 py-2.5 text-stone-100 focus:outline-none focus:ring-2 focus:ring-amber-400"
              >
                <option value={5}>5</option>
                <option value={6}>6</option>
                <option value={7}>7</option>
              </select>
            </div>
            <div>
              <span className="block text-sm font-semibold text-stone-300 mb-2">{t('dietFilters')}</span>
              <div className="flex flex-wrap gap-2">
                {DIET_OPTIONS.map(({ key, labelKey }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleDiet(key)}
                    className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                      dietFilters.includes(key)
                        ? 'bg-amber-500 text-white'
                        : 'bg-stone-800 text-stone-300 hover:bg-stone-700'
                    }`}
                  >
                    {t(labelKey)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-stone-300 mb-1.5">
                {t('maxTime')}
              </label>
              <select
                value={maxTime ?? ''}
                onChange={e => setMaxTime(e.target.value === '' ? null : Number(e.target.value))}
                className="w-full bg-stone-800 border border-stone-600 rounded-xl px-4 py-2.5 text-stone-100 focus:outline-none focus:ring-2 focus:ring-amber-400"
              >
                {TIME_OPTIONS.map(opt => (
                  <option key={String(opt.value)} value={opt.value ?? ''}>
                    {t(opt.labelKey)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-stone-300 mb-1.5">
                {t('budget')}
              </label>
              <input
                type="text"
                value={budget}
                onChange={e => setBudget(e.target.value)}
                placeholder="e.g. low, medium"
                className="w-full bg-stone-800 border border-stone-600 rounded-xl px-4 py-2.5 text-stone-100 placeholder-stone-500 focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
            </div>
            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={generateLoading}
              className="w-full min-h-[48px] bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-xl font-bold text-sm transition-colors"
            >
              {generateLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {t('generating')}
                </span>
              ) : (
                t('generateWeeklyPlan')
              )}
            </button>
          </form>
        </>
      )}

      {plan?.days?.length > 0 && error && (
        <div className="mt-4 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
          {error}
        </div>
      )}
    </div>
  )
}
