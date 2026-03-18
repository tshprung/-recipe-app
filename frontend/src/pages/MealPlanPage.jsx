import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
  const navigate = useNavigate()
  const [plan, setPlan] = useState(null)
  const [generateLoading, setGenerateLoading] = useState(false)
  const [replaceIndex, setReplaceIndex] = useState(null)
  const [addToListLoading, setAddToListLoading] = useState(false)
  const [error, setError] = useState(null)
  const [addListSuccess, setAddListSuccess] = useState(false)
  const [openPreviewDate, setOpenPreviewDate] = useState(null)
  const [savingDate, setSavingDate] = useState(null)
  const [savedRecipeIdsByDate, setSavedRecipeIdsByDate] = useState({})
  const [googleCalConnected, setGoogleCalConnected] = useState(false)
  const [googleCalLoading, setGoogleCalLoading] = useState(false)
  const [googleCalExporting, setGoogleCalExporting] = useState(false)
  const [googleCalExported, setGoogleCalExported] = useState(false)

  // Form state for generating
  const [numDays, setNumDays] = useState(7)
  const [mealTypes, setMealTypes] = useState(['dinner'])
  const [proteinTypes, setProteinTypes] = useState(['chicken'])
  const [meatMealsPerWeek, setMeatMealsPerWeek] = useState(3)
  const [fishMealsPerWeek, setFishMealsPerWeek] = useState(1)
  const [dietFilters, setDietFilters] = useState(() => user?.diet_filters ?? [])
  const [maxTime, setMaxTime] = useState(null)
  const [budget, setBudget] = useState('')

  useEffect(() => {
    if (user?.diet_filters && dietFilters.length === 0) setDietFilters(user.diet_filters)
  }, [user?.diet_filters])

  useEffect(() => {
    if (!user) return
    setGoogleCalLoading(true)
    api.get('/calendar/google/status')
      .then((d) => setGoogleCalConnected(!!d?.connected))
      .catch(() => setGoogleCalConnected(false))
      .finally(() => setGoogleCalLoading(false))
  }, [user])

  function isDirty() {
    if (plan?.days?.length) return true
    if (numDays !== 7) return true
    if ((mealTypes?.length ?? 0) !== 1 || mealTypes?.[0] !== 'dinner') return true
    if ((proteinTypes?.length ?? 0) !== 1 || proteinTypes?.[0] !== 'chicken') return true
    if (meatMealsPerWeek !== 3) return true
    if (fishMealsPerWeek !== 1) return true
    if ((dietFilters?.length ?? 0) > 0) return true
    if (maxTime != null) return true
    if ((budget || '').trim()) return true
    return false
  }

  function resetToClean() {
    setError(null)
    setAddListSuccess(false)
    setReplaceIndex(null)
    setOpenPreviewDate(null)
    setSavingDate(null)
    setSavedRecipeIdsByDate({})
    setPlan(null)
    setGoogleCalExported(false)
    setNumDays(7)
    setMealTypes(['dinner'])
    setProteinTypes(['chicken'])
    setMeatMealsPerWeek(3)
    setFishMealsPerWeek(1)
    setDietFilters([])
    setMaxTime(null)
    setBudget('')
  }

  function confirmAndResetIfDirty() {
    if (!isDirty()) {
      resetToClean()
      return
    }
    const ok = window.confirm('Are you sure? This will remove your current Meal Plan and choices.')
    if (ok) resetToClean()
  }

  useEffect(() => {
    function onResetRequest() {
      confirmAndResetIfDirty()
    }
    window.addEventListener('mealplan:reset-request', onResetRequest)
    return () => window.removeEventListener('mealplan:reset-request', onResetRequest)
  }, [plan, numDays, dietFilters, maxTime, budget])

  function toggleDiet(key) {
    setDietFilters(prev => (prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]))
  }

  const MEAL_TYPE_OPTIONS = [
    { key: 'breakfast', label: 'Breakfast' },
    { key: 'second_breakfast', label: 'Second breakfast' },
    { key: 'lunch', label: 'Lunch' },
    { key: 'afternoon_snack', label: 'Afternoon' },
    { key: 'dinner', label: 'Dinner' },
  ]

  const PROTEIN_OPTIONS = [
    { key: 'chicken', label: 'Chicken' },
    { key: 'turkey', label: 'Turkey' },
    { key: 'beef', label: 'Beef' },
    { key: 'fish', label: 'Fish' },
    { key: 'tofu', label: 'Tofu' },
    { key: 'eggs', label: 'Eggs' },
  ]

  function toggleMealType(key) {
    setMealTypes(prev => (prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]))
  }

  function toggleProtein(key) {
    setProteinTypes(prev => (prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]))
  }

  function handleGenerate(e) {
    e.preventDefault()
    setError(null)
    setGenerateLoading(true)
    api
      .post('/meal-plan/generate', {
        num_days: numDays,
        meal_types: mealTypes.length ? mealTypes : ['dinner'],
        protein_types: proteinTypes.length ? proteinTypes : null,
        meat_meals_per_week: meatMealsPerWeek ?? null,
        fish_meals_per_week: fishMealsPerWeek ?? null,
        diet_filters: dietFilters.length ? dietFilters : null,
        max_time_minutes: maxTime || null,
        budget: budget.trim() || null,
      })
      .then(data => {
        setPlan(data)
        setGoogleCalExported(false)
        refreshUser()
      })
      .catch(e => setError(getErrorMessage(e, t)))
      .finally(() => setGenerateLoading(false))
  }

  function handleReplaceMeal(dayIndex, mealIndex) {
    setError(null)
    setReplaceIndex(`${dayIndex}:${mealIndex}`)
    api
      .post(`/meal-plan/${plan.id}/replace-day`, { day_index: dayIndex, meal_index: mealIndex })
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

  async function handleSaveMealToMyRecipes(dayDate, meal) {
    if (!meal?.title) return
    setError(null)
    setSavingDate(dayDate)
    try {
      const created = await api.post('/recipes/from-ai-suggestion', {
        title: meal.title,
        ingredients: meal.ingredients ?? [],
        steps: meal.steps ?? [],
      })
      if (created?.id) {
        setSavedRecipeIdsByDate((prev) => ({ ...prev, [`${dayDate}::${meal.meal_type || 'meal'}`]: created.id }))
      }
      refreshUser?.()
    } catch (e) {
      setError(getErrorMessage(e, t))
    } finally {
      setSavingDate(null)
    }
  }

  if (!user && trialToken) {
    return (
      <div className="max-w-2xl mx-auto">
        <button
          type="button"
          onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
          className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-stone-300 hover:text-stone-100"
        >
          ← Back
        </button>
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

  async function handleConnectGoogleCalendar() {
    setError(null)
    try {
      const d = await api.get('/calendar/google/connect-url')
      if (d?.url) window.location.href = d.url
      else setError('Failed to start Google Calendar connection.')
    } catch (e) {
      setError(getErrorMessage(e, t))
    }
  }

  async function handleExportToGoogleCalendar() {
    if (!plan?.id) return
    setError(null)
    setGoogleCalExported(false)
    setGoogleCalExporting(true)
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
      await api.post(`/calendar/google/export/meal-plan/${plan.id}?timezone_name=${encodeURIComponent(tz)}`)
      setGoogleCalExported(true)
    } catch (e) {
      setError(getErrorMessage(e, t))
    } finally {
      setGoogleCalExporting(false)
    }
  }

  async function handleDisconnectGoogleCalendar() {
    setError(null)
    try {
      await api.delete('/calendar/google/disconnect')
      setGoogleCalConnected(false)
      setGoogleCalExported(false)
    } catch (e) {
      setError(getErrorMessage(e, t))
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <button
        type="button"
        onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
        className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-stone-300 hover:text-stone-100"
      >
        ← Back
      </button>
      <h1 className="text-2xl font-bold text-stone-50 mb-1">{t('mealPlanTitle')}</h1>
      <p className="text-stone-400 text-sm mb-6">{t('mealPlanHint')}</p>

      {user && (
        <div className="mb-6 bg-stone-900/60 border border-white/10 rounded-2xl p-4 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <div className="text-sm">
            <div className="font-semibold text-stone-100">Google Calendar</div>
            <div className="text-xs text-stone-400">
              {googleCalLoading ? 'Checking connection…' : (googleCalConnected ? 'Connected' : 'Not connected')}
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            {!googleCalConnected ? (
              <button
                type="button"
                onClick={handleConnectGoogleCalendar}
                className="min-h-[44px] px-4 py-2 rounded-xl bg-amber-400 text-black font-bold text-sm hover:bg-amber-300 transition"
              >
                Connect Google Calendar
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={handleExportToGoogleCalendar}
                  disabled={!plan?.id || googleCalExporting}
                  className="min-h-[44px] px-4 py-2 rounded-xl bg-amber-400 text-black font-bold text-sm hover:bg-amber-300 transition disabled:opacity-50"
                >
                  {googleCalExporting ? 'Exporting…' : 'Export plan to Calendar'}
                </button>
                <button
                  type="button"
                  onClick={handleDisconnectGoogleCalendar}
                  className="min-h-[44px] px-4 py-2 rounded-xl ring-1 ring-white/10 hover:bg-white/10 transition text-stone-50"
                  style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
                >
                  Disconnect
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {plan?.days?.length > 0 ? (
        <>
          <div className="flex items-center justify-between mb-4">
            <button
              type="button"
              onClick={confirmAndResetIfDirty}
              className="min-h-[40px] px-3 py-2 rounded-xl bg-stone-800 text-stone-200 hover:bg-stone-700 transition-colors text-sm font-semibold"
            >
              Back / Cancel
            </button>
          </div>
          <div className="space-y-4 mb-8">
            {plan.days.map((day, idx) => (
              <div
                key={day.date}
                className="bg-white rounded-2xl border border-stone-100 shadow-sm p-4 text-stone-800"
              >
                <p className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-3">
                  {day.date}
                </p>

                <div className="space-y-4">
                  {(day.meals || []).map((meal, mealIdx) => {
                    const previewKey = `${day.date}::${meal.meal_type || mealIdx}`
                    const savedKey = `${day.date}::${meal.meal_type || 'meal'}`
                    const savedId = savedRecipeIdsByDate[savedKey]
                    return (
                      <div key={previewKey} className="rounded-xl border border-stone-200 p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-stone-500 uppercase tracking-widest mb-1">
                              {(meal.meal_type || 'meal').replaceAll('_', ' ')}
                            </p>
                            <h3 className="font-bold text-lg text-stone-800">{meal.name}</h3>
                            {meal.short_description && (
                              <p className="text-sm text-stone-600 mt-1">{meal.short_description}</p>
                            )}
                            <p className="text-xs text-stone-500 mt-1">
                              ~{meal.estimated_time_minutes} min
                            </p>
                          </div>
                          <div className="flex flex-col gap-2 items-end flex-shrink-0">
                            <button
                              type="button"
                              onClick={() => setOpenPreviewDate((prev) => (prev === previewKey ? null : previewKey))}
                              className="px-3 py-1.5 rounded-xl text-sm font-medium bg-stone-100 text-stone-600 hover:bg-stone-200"
                            >
                              {openPreviewDate === previewKey ? 'Hide details' : 'Preview recipe'}
                            </button>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleSaveMealToMyRecipes(day.date, meal)}
                                disabled={savingDate === day.date || !!savedId}
                                className="px-3 py-1.5 rounded-xl text-sm font-medium bg-stone-100 text-stone-600 hover:bg-stone-200 disabled:opacity-50"
                              >
                                {savingDate === day.date ? t('adding') : savedId ? t('addedToRecipes') : t('addToMyRecipes')}
                              </button>
                              {!!savedId && (
                                <button
                                  type="button"
                                  onClick={() => navigate(`/recipes/${savedId}`)}
                                  className="text-sm font-medium text-stone-600 hover:underline"
                                >
                                  {t('viewRecipe')}
                                </button>
                              )}
                            </div>
                            <button
                              type="button"
                              onClick={() => handleReplaceMeal(idx, mealIdx)}
                              disabled={replaceIndex !== null}
                              className="px-3 py-1.5 rounded-xl text-sm font-medium bg-stone-100 text-stone-600 hover:bg-stone-200 disabled:opacity-50"
                            >
                              {replaceIndex === `${idx}:${mealIdx}` ? '…' : t('replaceMeal')}
                            </button>
                          </div>
                        </div>

                        {openPreviewDate === previewKey && (
                          <div className="mt-4 border-t border-stone-200 pt-4 space-y-4">
                            <div>
                              <p className="text-xs font-semibold text-stone-500 uppercase tracking-widest mb-2">Ingredients</p>
                              <ul className="space-y-1 text-sm text-stone-700 list-disc pl-5">
                                {(meal.ingredients || []).map((ing, i) => (
                                  <li key={i}>{ing}</li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-stone-500 uppercase tracking-widest mb-2">Steps</p>
                              <ol className="space-y-1 text-sm text-stone-700 list-decimal pl-5">
                                {(meal.steps || []).map((step, i) => (
                                  <li key={i}>{step}</li>
                                ))}
                              </ol>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
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
          <div className="flex justify-end mb-3">
            <button
              type="button"
              onClick={confirmAndResetIfDirty}
              className="min-h-[40px] px-3 py-2 rounded-xl bg-stone-800 text-stone-200 hover:bg-stone-700 transition-colors text-sm font-semibold"
            >
              Clear / Start over
            </button>
          </div>
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
              <span className="block text-sm font-semibold text-stone-300 mb-2">Meal types</span>
              <div className="flex flex-wrap gap-2">
                {MEAL_TYPE_OPTIONS.map(({ key, label }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleMealType(key)}
                    className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                      mealTypes.includes(key)
                        ? 'bg-amber-500 text-white'
                        : 'bg-stone-800 text-stone-300 hover:bg-stone-700'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-stone-500 mt-1">Select 1+; the plan will include all selected meal types for each day.</p>
            </div>

            <div>
              <span className="block text-sm font-semibold text-stone-300 mb-2">Protein types (best effort)</span>
              <div className="flex flex-wrap gap-2">
                {PROTEIN_OPTIONS.map(({ key, label }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggleProtein(key)}
                    className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                      proteinTypes.includes(key)
                        ? 'bg-amber-500 text-white'
                        : 'bg-stone-800 text-stone-300 hover:bg-stone-700'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-semibold text-stone-300 mb-1.5">Meat meals per week</label>
                <input
                  type="number"
                  min={0}
                  max={21}
                  value={meatMealsPerWeek}
                  onChange={(e) => setMeatMealsPerWeek(Number(e.target.value))}
                  className="w-full bg-stone-800 border border-stone-600 rounded-xl px-4 py-2.5 text-stone-100 focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-stone-300 mb-1.5">Fish meals per week</label>
                <input
                  type="number"
                  min={0}
                  max={21}
                  value={fishMealsPerWeek}
                  onChange={(e) => setFishMealsPerWeek(Number(e.target.value))}
                  className="w-full bg-stone-800 border border-stone-600 rounded-xl px-4 py-2.5 text-stone-100 focus:outline-none focus:ring-2 focus:ring-amber-400"
                />
              </div>
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
