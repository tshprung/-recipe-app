import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { TrialExhaustedModal } from '../components/TrialExhaustedModal'

const DIET_OPTIONS = [
  { key: 'vegetarian', labelKey: 'vegetarian' },
  { key: 'vegan', labelKey: 'vegan' },
  { key: 'dairy_free', labelKey: 'dairyFree' },
  { key: 'gluten_free', labelKey: 'glutenFree' },
  { key: 'kosher', labelKey: 'kosher' },
  { key: 'halal', labelKey: 'halal' },
  { key: 'nut_free', labelKey: 'nutFree' },
  { key: 'low_sodium', labelKey: 'lowSodium' },
]

export default function WhatCanIMakePage() {
  const { t } = useLanguage()
  const { refreshUser } = useAuth()
  const navigate = useNavigate()
  const [ingredientsText, setIngredientsText] = useState('')
  const [dietFilters, setDietFilters] = useState([])
  const [assumePantry, setAssumePantry] = useState(true)
  const [source, setSource] = useState('my_recipes')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [addedIngredients, setAddedIngredients] = useState([])
  const [addingRecipeId, setAddingRecipeId] = useState(null)
  const [addRecipeSuccess, setAddRecipeSuccess] = useState(null) // { id, title } when added
  const [showTrialExhausted, setShowTrialExhausted] = useState(false)

  const ingredientsList = ingredientsText
    .split(/[\n,]+/)
    .map(s => s.trim())
    .filter(Boolean)

  function toggleDiet(key) {
    setDietFilters(prev => (prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]))
  }

  function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setResult(null)
    const allIngredients = [...ingredientsList, ...addedIngredients]
    if (allIngredients.length === 0 && source === 'my_recipes') {
      setError(t('addAtLeastOneIngredient'))
      return
    }
    setLoading(true)
    api
      .post('/recipes/what-can-i-make', {
        ingredients: allIngredients,
        diet_filters: dietFilters.length ? dietFilters : null,
        assume_pantry: assumePantry,
        source,
      })
      .then(data => {
        setResult(data)
        setLoading(false)
        if (data?.source === 'ai') refreshUser()
      })
      .catch(e => {
        if (e.trialExhausted) setShowTrialExhausted(true)
        else setError(e.message || t('somethingWentWrong'))
        setLoading(false)
      })
  }

  async function handleAddToMyRecipes(sug) {
    setAddingRecipeId(sug.title)
    setAddRecipeSuccess(null)
    try {
      const created = await api.post('/recipes/from-ai-suggestion', {
        title: sug.title,
        ingredients: sug.ingredients ?? [],
        steps: sug.steps ?? [],
      })
      setAddRecipeSuccess({ id: created.id, title: sug.title })
      setTimeout(() => setAddRecipeSuccess(null), 5000)
    } catch (e) {
      setError(e.message || t('somethingWentWrong'))
    } finally {
      setAddingRecipeId(null)
    }
  }

  function handleAddMissing(ingredient) {
    const newAdded = [...addedIngredients, ingredient]
    setAddedIngredients(newAdded)
    setResult(null)
    setError(null)
    setLoading(true)
    const allIngredients = [...ingredientsList, ...newAdded]
    api
      .post('/recipes/what-can-i-make', {
        ingredients: allIngredients,
        diet_filters: dietFilters.length ? dietFilters : null,
        assume_pantry: assumePantry,
        source: 'my_recipes',
      })
      .then(data => {
        setResult(data)
        setLoading(false)
      })
      .catch(e => {
        if (e.trialExhausted) setShowTrialExhausted(true)
        else setError(e.message || t('somethingWentWrong'))
        setLoading(false)
      })
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold text-stone-800 mb-2">{t('whatCanIMake')}</h2>
      <p className="text-stone-500 text-sm mb-6">{t('whatCanIMakeHint')}</p>

      <form onSubmit={handleSubmit} className="space-y-4 mb-8">
        <div>
          <label className="block text-sm font-semibold text-stone-600 mb-1.5">{t('ingredientsIHave')}</label>
          <textarea
            value={ingredientsText}
            onChange={e => setIngredientsText(e.target.value)}
            placeholder={t('ingredientsPlaceholder')}
            rows={4}
            className="w-full border border-stone-200 rounded-xl px-4 py-3 text-sm text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent bg-white resize-none"
          />
          <p className="text-xs text-stone-400 mt-1">{t('ingredientsCommaOrNewline')}</p>
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

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={assumePantry}
            onChange={e => setAssumePantry(e.target.checked)}
            className="rounded border-stone-300 text-amber-500 focus:ring-amber-400"
          />
          <span className="text-sm text-stone-700">{t('assumePantry')}</span>
        </label>

        <div>
          <span className="block text-sm font-semibold text-stone-600 mb-2">{t('source')}</span>
          <div className="flex gap-2">
            <label className={`flex-1 py-2.5 px-4 rounded-xl border text-sm font-medium text-center cursor-pointer transition-colors ${
              source === 'my_recipes' ? 'border-amber-400 bg-amber-50 text-amber-800' : 'border-stone-200 text-stone-500 hover:bg-stone-50'
            }`}>
              <input type="radio" name="source" value="my_recipes" checked={source === 'my_recipes'} onChange={() => setSource('my_recipes')} className="sr-only" />
              {t('myRecipes')}
            </label>
            <label className={`flex-1 py-2.5 px-4 rounded-xl border text-sm font-medium text-center cursor-pointer transition-colors ${
              source === 'ai' ? 'border-amber-400 bg-amber-50 text-amber-800' : 'border-stone-200 text-stone-500 hover:bg-stone-50'
            }`}>
              <input type="radio" name="source" value="ai" checked={source === 'ai'} onChange={() => setSource('ai')} className="sr-only" />
              {t('aiSuggestion')}
            </label>
          </div>
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
            t('findRecipes')
          )}
        </button>
      </form>

      {result?.source === 'my_recipes' && result.matches && (
        <div className="space-y-4">
          {result.matches.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
              <p className="text-stone-500 font-medium mb-1">{t('noMatchingRecipes')}</p>
              <p className="text-sm text-stone-400">{t('tryMoreIngredientsOrSwitchAI')}</p>
            </div>
          ) : (
            result.matches.map(match => (
              <div
                key={match.recipe.id}
                className="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden"
              >
                <div
                  className="p-4 cursor-pointer hover:bg-stone-50 transition-colors"
                  onClick={() => navigate(`/recipes/${match.recipe.id}`)}
                >
                  <h3 className="font-bold text-stone-800">{match.recipe.title_pl}</h3>
                  {match.can_make ? (
                    <p className="text-sm text-emerald-600 font-medium mt-1">{t('youHaveEverything')}</p>
                  ) : match.missing_ingredients?.length > 0 ? (
                    <div className="mt-2">
                      <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide">{t('missingIngredients')}</p>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {match.missing_ingredients.map((ing, i) => (
                          <span key={i} className="inline-flex items-center gap-1 text-xs bg-amber-50 text-amber-800 rounded-lg px-2 py-1 border border-amber-100">
                            {ing}
                            <button
                              type="button"
                              onClick={e => { e.stopPropagation(); handleAddMissing(ing) }}
                              className="text-amber-600 hover:underline font-medium"
                            >
                              {t('iHaveThis')}
                            </button>
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {result?.source === 'ai' && result.suggestions && (
        <div className="space-y-4">
          {result.suggestions.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-2xl border border-stone-100">
              <p className="text-stone-500">{t('noAISuggestions')}</p>
            </div>
          ) : (
            result.suggestions.map((sug, i) => (
              <div key={i} className="bg-white rounded-2xl border border-stone-100 shadow-sm p-5">
                <h3 className="font-bold text-stone-800">{sug.title}</h3>
                {sug.ingredients?.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide">{t('ingredients')}</p>
                    <ul className="list-disc list-inside text-sm text-stone-700 mt-1 space-y-0.5">
                      {sug.ingredients.map((ing, j) => (
                        <li key={j}>{ing}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {sug.steps?.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-stone-500 uppercase tracking-wide">{t('instructions')}</p>
                    <ol className="list-decimal list-inside text-sm text-stone-700 mt-1 space-y-1">
                      {sug.steps.map((step, j) => (
                        <li key={j}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={() => handleAddToMyRecipes(sug)}
                    disabled={addingRecipeId !== null}
                    className="text-sm font-medium text-amber-600 hover:text-amber-700 hover:underline disabled:opacity-50"
                  >
                    {addingRecipeId === sug.title ? t('adding') : addRecipeSuccess?.title === sug.title ? t('addedToRecipes') : t('addToMyRecipes')}
                  </button>
                  {addRecipeSuccess?.title === sug.title && addRecipeSuccess?.id && (
                    <button
                      type="button"
                      onClick={() => navigate(`/recipes/${addRecipeSuccess.id}`)}
                      className="ml-3 text-sm font-medium text-stone-500 hover:underline"
                    >
                      {t('viewRecipe')}
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
      <TrialExhaustedModal open={showTrialExhausted} onClose={() => setShowTrialExhausted(false)} />
    </div>
  )
}
