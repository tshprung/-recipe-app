import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { TrialExhaustedModal } from '../components/TrialExhaustedModal'
import { DISH_TYPES, DIET_OPTIONS, TIME_OPTIONS } from '../constants'
import { getErrorMessage } from '../utils/errors'

export default function DiscoverPage() {
  const { t } = useLanguage()
  const { user, trialToken, refreshUser, syncTrialRemaining } = useAuth()
  const navigate = useNavigate()
  const [dishTypes, setDishTypes] = useState([])
  const [dietFilters, setDietFilters] = useState([])
  const [maxTime, setMaxTime] = useState(null)
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState(null)
  const [error, setError] = useState(null)
  const [addingTitle, setAddingTitle] = useState(null)
  const [savedId, setSavedId] = useState(null)
  const [savedTitle, setSavedTitle] = useState(null)
  const [showTrialExhausted, setShowTrialExhausted] = useState(false)

  function toggleDish(type) {
    setDishTypes(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type])
  }

  function toggleDiet(key) {
    setDietFilters(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key])
  }

  function handleFind(e) {
    e.preventDefault()
    setError(null)
    setSuggestions(null)
    setLoading(true)
    api
      .post('/recipes/discover', {
        dish_types: dishTypes.length ? dishTypes : null,
        diet_filters: dietFilters.length ? dietFilters : null,
        max_time_minutes: maxTime || null,
      })
      .then(data => {
        setSuggestions(data.suggestions || [])
        if (typeof data.remaining_actions === 'number') syncTrialRemaining(data.remaining_actions)
        refreshUser()
      })
      .catch(e => {
        if (e.status === 402 || e.trialExhausted) {
          syncTrialRemaining(0)
          setShowTrialExhausted(true)
        } else setError(getErrorMessage(e, t))
      })
      .finally(() => setLoading(false))
  }

  async function handleSaveToMyRecipes(sug) {
    if (!user) return
    setAddingTitle(sug.title)
    setSavedId(null)
    try {
      const created = await api.post('/recipes/from-ai-suggestion', {
        title: sug.title,
        ingredients: sug.ingredients ?? [],
        steps: sug.steps ?? [],
      })
      setSavedId(created.id)
      setSavedTitle(sug.title)
      refreshUser()
    } catch (e) {
      setError(getErrorMessage(e, t))
    } finally {
      setAddingTitle(null)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-stone-800 mb-2">{t('discover')}</h2>
      <p className="text-stone-500 text-sm mb-6">{t('discoverHint')}</p>

      <form onSubmit={handleFind} className="space-y-4 mb-8">
        <div>
          <span className="block text-sm font-semibold text-stone-600 mb-2">{t('dishTypes')}</span>
          <div className="flex flex-wrap gap-2">
            {DISH_TYPES.map(type => (
              <button
                key={type}
                type="button"
                onClick={() => toggleDish(type)}
                className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                  dishTypes.includes(type)
                    ? 'bg-amber-500 text-white'
                    : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="block text-sm font-semibold text-stone-600 mb-2">{t('dietFilters')}</span>
          <div className="flex flex-wrap gap-2">
            {DIET_OPTIONS.map(({ key, labelKey }) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={dietFilters.includes(key)}
                  onChange={() => toggleDiet(key)}
                  className="rounded border-stone-300 text-amber-500 focus:ring-amber-400"
                />
                <span className="text-sm text-stone-700">{t(labelKey)}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('maxTime')}</label>
          <select
            value={maxTime ?? ''}
            onChange={e => setMaxTime(e.target.value === '' ? null : parseInt(e.target.value, 10))}
            className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-stone-800 bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
          >
            {TIME_OPTIONS.map(opt => (
              <option key={String(opt.value)} value={opt.value ?? ''}>
                {t(opt.labelKey)}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full min-h-[48px] bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-xl font-bold text-sm transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              {t('finding')}
            </span>
          ) : (
            t('findRecipesForMe')
          )}
        </button>
      </form>

      {suggestions && suggestions.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-stone-800">{t('suggestions')}</h3>
          {suggestions.map((sug, i) => (
            <div
              key={i}
              className="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden p-4"
            >
              <h4 className="font-bold text-stone-800">{sug.title}</h4>
              <p className="text-xs text-stone-500 mt-1">
                {sug.ingredients?.length ?? 0} ingredients · {(sug.steps?.length ?? 0)} steps
              </p>
              <div className="mt-3 flex items-center gap-2">
                {user ? (
                  <>
                    <button
                      type="button"
                      onClick={() => handleSaveToMyRecipes(sug)}
                      disabled={addingTitle === sug.title}
                      className="text-sm font-semibold text-amber-600 hover:text-amber-700 disabled:opacity-50"
                    >
                      {addingTitle === sug.title ? '…' : savedTitle === sug.title ? t('saved') : t('addToMyRecipes')}
                    </button>
                    {savedTitle === sug.title && savedId && (
                      <button
                        type="button"
                        onClick={() => navigate(`/recipes/${savedId}`)}
                        className="text-sm font-medium text-stone-600 hover:underline"
                      >
                        {t('viewRecipe')}
                      </button>
                    )}
                  </>
                ) : (
                  <span className="text-sm text-stone-500">{t('signInToSaveRecipes')}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {suggestions && suggestions.length === 0 && !loading && (
        <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
          <p className="text-stone-500 font-medium">{t('noSuggestions')}</p>
          <p className="text-sm text-stone-400 mt-1">{t('tryDifferentFilters')}</p>
        </div>
      )}

      {showTrialExhausted && (
        <TrialExhaustedModal onClose={() => setShowTrialExhausted(false)} />
      )}
    </div>
  )
}
