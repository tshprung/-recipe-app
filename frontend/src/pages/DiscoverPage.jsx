import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { TrialExhaustedModal } from '../components/TrialExhaustedModal'
import { DISH_TYPES, DIET_OPTIONS, TIME_OPTIONS, ALLERGENS } from '../constants'
import { getErrorMessage } from '../utils/errors'

export default function DiscoverPage() {
  const { t, lang } = useLanguage()
  const { user, trialToken, refreshUser, syncTrialRemaining } = useAuth()
  const navigate = useNavigate()
  const [dishTypes, setDishTypes] = useState(() => user?.dish_preferences ?? [])
  const [dietFilters, setDietFilters] = useState(() => user?.diet_filters ?? [])
  const [allergens, setAllergens] = useState(() => user?.allergens ?? [])
  const [customAvoid, setCustomAvoid] = useState(() => user?.custom_allergens_text ?? '')
  const [maxTime, setMaxTime] = useState(null)
  const [keywords, setKeywords] = useState('')
  const [ingredientsText, setIngredientsText] = useState('')
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

  function toggleAllergen(code) {
    setAllergens(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    )
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
        allergens: allergens.length ? allergens : null,
        custom_avoid_text: customAvoid || null,
        keywords: keywords || null,
        ingredients_text: ingredientsText || null,
        target_language: lang || 'en',
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
      if (user) {
        refreshUser()
      }
    } catch (e) {
      setError(getErrorMessage(e, t))
    } finally {
      setAddingTitle(null)
    }
  }

  function SuggestionCard({ suggestion: sug, user, trialToken, addingTitle, savedTitle, savedId, onSave }) {
    const [expanded, setExpanded] = useState(false)
    const hasAccount = !!user
    const inTrial = !user && !!trialToken

    return (
      <div className="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden p-4">
        <h4 className="font-bold text-stone-800">{sug.title}</h4>
        <p className="text-xs text-stone-500 mt-1">
          {sug.ingredients?.length ?? 0} ingredients · {(sug.steps?.length ?? 0)} steps
        </p>

        <button
          type="button"
          onClick={() => setExpanded(e => !e)}
          className="mt-3 text-xs font-medium text-stone-600 hover:text-stone-800 underline"
        >
          {expanded ? 'Hide details' : 'View full recipe'}
        </button>

        {expanded && (
          <div className="mt-3 space-y-3 text-sm text-stone-700">
            <div>
              <div className="font-semibold mb-1">Ingredients</div>
              <ul className="list-disc list-inside space-y-0.5">
                {(sug.ingredients ?? []).map((ing, idx) => (
                  <li key={idx}>{ing}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-semibold mb-1">Steps</div>
              <ol className="list-decimal list-inside space-y-0.5">
                {(sug.steps ?? []).map((step, idx) => (
                  <li key={idx}>{step}</li>
                ))}
              </ol>
            </div>
          </div>
        )}

        <div className="mt-3 flex items-center gap-2">
          {(hasAccount || inTrial) ? (
            <>
              <button
                type="button"
                onClick={onSave}
                disabled={addingTitle === sug.title}
                className="text-sm font-semibold text-amber-600 hover:text-amber-700 disabled:opacity-50"
              >
                {addingTitle === sug.title ? '…' : savedTitle === sug.title ? t('saved') : t('addToMyRecipes')}
              </button>
              {savedTitle === sug.title && savedId && hasAccount && (
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
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-stone-800 mb-2">{t('findNewRecipes')}</h2>
      <p className="text-stone-500 text-sm mb-6">{t('discoverHint')}</p>

      <form onSubmit={handleFind} className="space-y-4 mb-8">
        <div>
          <label className="block text-sm font-semibold text-stone-600 mb-1.5">
            {t('discoverKeywordsLabel')}
          </label>
          <input
            type="text"
            value={keywords}
            onChange={e => setKeywords(e.target.value)}
            placeholder="Passover charoset, quick pasta for two, birthday cake without nuts…"
            className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-stone-800 bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <p className="text-xs text-stone-400 mt-1">{t('discoverKeywordsHint')}</p>
        </div>

        <div>
          <label className="block text-sm font-semibold text-stone-600 mb-1.5">
            {t('discoverIngredientsLabel')} ({t('optional')})
          </label>
          <textarea
            value={ingredientsText}
            onChange={e => setIngredientsText(e.target.value)}
            rows={3}
            placeholder={t('discoverIngredientsHint')}
            className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-stone-800 bg-white focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
          />
        </div>
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
              <button
                key={key}
                type="button"
                onClick={() => toggleDiet(key)}
                className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                  dietFilters.includes(key)
                    ? 'bg-amber-500 text-white'
                    : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                }`}
              >
                {t(labelKey)}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="block text-sm font-semibold text-stone-600 mb-2">{t('allergensToAvoid')} ({t('optional')})</span>
          <div className="flex flex-wrap gap-2">
            {ALLERGENS.map(a => (
              <button
                key={a.code}
                type="button"
                onClick={() => toggleAllergen(a.code)}
                className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                  allergens.includes(a.code)
                    ? 'bg-amber-500 text-white'
                    : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                }`}
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-semibold text-stone-600 mb-1.5">
            {t('otherAllergens')} ({t('optional')})
          </label>
          <input
            type="text"
            value={customAvoid}
            onChange={e => setCustomAvoid(e.target.value)}
            placeholder={t('otherAllergensPlaceholder')}
            className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-stone-800 bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <p className="text-xs text-stone-400 mt-1">{t('otherAllergensHint')}</p>
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
            <SuggestionCard
              key={i}
              suggestion={sug}
              user={user}
              trialToken={trialToken}
              addingTitle={addingTitle}
              savedTitle={savedTitle}
              savedId={savedId}
              onSave={() => handleSaveToMyRecipes(sug)}
            />
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
