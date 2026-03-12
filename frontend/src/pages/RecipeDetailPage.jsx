import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, getRecipeImageUrl } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

const TAG_COLORS = [
  'bg-amber-100 text-amber-700',
  'bg-orange-100 text-orange-700',
  'bg-rose-100 text-rose-700',
  'bg-emerald-100 text-emerald-700',
  'bg-lime-100 text-lime-700',
  'bg-teal-100 text-teal-700',
]

const NOTE_META = {
  porcje:              { tKey: 'servings',     icon: '🍽' },
  czas_przygotowania:  { tKey: 'prepTime',     icon: '⏱' },
  czas_gotowania:      { tKey: 'cookTime',    icon: '🔥' },
}

const VARIANT_OPTIONS = [
  { key: 'vegetarian', label: 'Vegetarian' },
  { key: 'vegan',      label: 'Vegan' },
  { key: 'dairy_free', label: 'Dairy free' },
  { key: 'gluten_free',label: 'Gluten free' },
  { key: 'kosher',     label: 'Kosher' },
  { key: 'halal',      label: 'Halal' },
  { key: 'nut_free',   label: 'Nut free' },
  { key: 'low_sodium', label: 'Low sodium' },
]

// Badge shown on the recipe hero card for original and each variant
const VARIANT_BADGE = {
  original:    { label: 'Original',    cls: 'bg-stone-100 text-stone-500' },
  vegetarian:  { label: 'Vegetarian', cls: 'bg-emerald-100 text-emerald-700' },
  vegan:       { label: 'Vegan',      cls: 'bg-emerald-100 text-emerald-700' },
  dairy_free:  { label: 'Dairy free', cls: 'bg-sky-100 text-sky-700' },
  gluten_free: { label: 'Gluten free', cls: 'bg-violet-100 text-violet-700' },
  kosher:      { label: 'Kosher',     cls: 'bg-blue-100 text-blue-700' },
  halal:       { label: 'Halal',      cls: 'bg-teal-100 text-teal-700' },
  nut_free:    { label: 'Nut free',   cls: 'bg-amber-100 text-amber-700' },
  low_sodium:  { label: 'Low sodium', cls: 'bg-rose-100 text-rose-700' },
}

// Keywords for auto-detecting ingredient content tags
const CONTENT_KEYWORDS = [
  { label: 'Contains meat', icon: '🥩', words: ['mięso', 'kurczak', 'wołowina', 'wieprzowina', 'indyk', 'boczek', 'kiełbasa', 'wędlina', 'szynka', 'wątróbka', 'żeberka', 'mielone', 'kotlet', 'schab', 'cielęcina', 'kaczka', 'jagnięcina', 'baranina', 'rostbef', 'meat', 'chicken', 'beef', 'pork'] },
  { label: 'Contains dairy', icon: '🧀', words: ['mleko', 'śmietana', 'śmietanka', 'ser', 'masło', 'jogurt', 'twaróg', 'ricotta', 'mozzarella', 'parmezan', 'kefir', 'maślanka', 'brie', 'camembert', 'feta', 'gouda', 'edam', 'milk', 'cream', 'cheese', 'butter'] },
  { label: 'Contains eggs', icon: '🥚', words: ['jajko', 'jajka', 'jaja', 'żółtko', 'egg'] },
  { label: 'Contains fish', icon: '🐟', words: ['ryba', 'łosoś', 'tuńczyk', 'dorsz', 'śledź', 'makrela', 'sardynka', 'pstrąg', 'karp', 'halibut', 'flądra', 'mintaj', 'krewetki', 'kalmary', 'fish', 'salmon', 'tuna'] },
]

function detectContentTags(ingredients) {
  const text = (ingredients || [])
    .map(ing => (typeof ing === 'object' ? `${ing.amount ?? ''} ${ing.name ?? ''}` : ing))
    .join(' ')
    .toLowerCase()
  return CONTENT_KEYWORDS.filter(cat => cat.words.some(w => text.includes(w)))
}

function Section({ title, icon, children }) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        {icon && <span className="text-base">{icon}</span>}
        <h2 className="text-xs font-bold text-stone-400 uppercase tracking-widest">{title}</h2>
      </div>
      {children}
    </div>
  )
}

function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-2xl border border-stone-100 shadow-sm p-5 ${className}`}>
      {children}
    </div>
  )
}

function variantLabelKey(key) {
  if (key === 'dairy_free') return 'dairyFree'
  if (key === 'gluten_free') return 'glutenFree'
  if (key === 'nut_free') return 'nutFree'
  if (key === 'low_sodium') return 'lowSodium'
  return key
}

function variantDisplayLabel(variantType, t) {
  const parts = (variantType || '').split(',').map(s => s.trim()).filter(Boolean)
  if (parts.length === 0) return ''
  if (parts.length === 1) return t(variantLabelKey(parts[0]))
  return parts.map(p => t(variantLabelKey(p))).join(' + ')
}

export default function RecipeDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, refreshUser } = useAuth()
  const { t } = useLanguage()

  const [recipe, setRecipe] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notes, setNotes] = useState('')
  const [notesSaved, setNotesSaved] = useState(false)
  const [showOriginal, setShowOriginal] = useState(false)

  // Adaptation state
  const [variants, setVariants] = useState([])
  const [activeTab, setActiveTab] = useState('original')
  const [adaptLoading, setAdaptLoading] = useState(false)
  const [adaptDropdownOpen, setAdaptDropdownOpen] = useState(false)
  const [selectedAdaptTypes, setSelectedAdaptTypes] = useState([])  // multi-select for Apply
  const [alternatives, setAlternatives] = useState(null)
  const [pendingVariantType, setPendingVariantType] = useState(null)
  const [adaptError, setAdaptError] = useState(null)
  const dropdownRef = useRef(null)

  // Ingredient alternatives: off by default so users don't waste credits by accident
  const [ingredientLookupEnabled, setIngredientLookupEnabled] = useState(false)
  const [altIngredient, setAltIngredient] = useState(null)
  const [altIngredientIndex, setAltIngredientIndex] = useState(null)
  const [altOpen, setAltOpen] = useState(false)
  const [altLoading, setAltLoading] = useState(false)
  const [altData, setAltData] = useState(null)
  const [altError, setAltError] = useState(null)
  const [generateImageLoading, setGenerateImageLoading] = useState(false)

  useEffect(() => {
    Promise.all([
      api.get(`/recipes/${id}`),
      api.get(`/recipes/${id}/variants`),
    ])
      .then(([data, variantData]) => {
        setRecipe(data)
        setNotes(data.user_notes ?? '')
        setVariants(variantData)
      })
      .catch(e => setError(e.message || t('recipeNotFound')))
      .finally(() => setLoading(false))
  }, [id, t])

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setAdaptDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  async function handleSaveNotes() {
    try {
      const updated = await api.patch(`/recipes/${id}/notes`, { user_notes: notes })
      setRecipe(updated)
      setNotesSaved(true)
      setTimeout(() => setNotesSaved(false), 2000)
    } catch (e) {
      console.error(e)
    }
  }

  async function handleToggleFavorite() {
    try {
      const updated = await api.patch(`/recipes/${id}/favorite`, { is_favorite: !recipe.is_favorite })
      setRecipe(updated)
    } catch (e) {
      console.error(e)
    }
  }

  async function handleSetRating(nextRating) {
    try {
      const updated = await api.patch(`/recipes/${id}/meta`, { rating: nextRating })
      setRecipe(updated)
    } catch (e) {
      console.error(e)
    }
  }

  async function handleGenerateImage() {
    if (!recipe?.id || recipe.image_url) return
    setGenerateImageLoading(true)
    try {
      const updated = await api.post(`/recipes/${id}/generate-image`)
      setRecipe(updated)
    } catch (e) {
      console.error(e)
    } finally {
      setGenerateImageLoading(false)
    }
  }

  async function handleAdapt(typesOrSingle) {
    const types = Array.isArray(typesOrSingle) ? typesOrSingle : [typesOrSingle]
    const compositeKey = types.length === 1 ? types[0] : types.join(',')
    setAdaptDropdownOpen(false)
    setAdaptError(null)
    if (variants.find(v => v.variant_type === compositeKey)) {
      setActiveTab(compositeKey)
      return
    }
    setAdaptLoading(true)
    setAlternatives(null)
    setPendingVariantType(compositeKey)
    setSelectedAdaptTypes([])
    try {
      const body = types.length === 1
        ? { variant_type: types[0] }
        : { variant_types: types }
      const result = await api.post(`/recipes/${id}/adapt`, body)
      if (result.can_adapt) {
        setVariants(vs => [...vs, result.variant])
        setActiveTab(result.variant.variant_type)
        await refreshUser()
      } else {
        setAlternatives(result.alternatives)
        if (types.length > 1) setPendingVariantType(types[types.length - 1])
      }
    } catch (e) {
      setAdaptError(e.message || t('failedToAdapt'))
    } finally {
      setAdaptLoading(false)
    }
  }

  async function handleRemoveVariant(variantType) {
    try {
      await api.delete(`/recipes/${id}/variants`, { variant_type: variantType })
      setVariants(vs => vs.filter(v => v.variant_type !== variantType))
      if (activeTab === variantType) setActiveTab('original')
    } catch (e) {
      setAdaptError(e.message || t('failedToAdapt'))
    }
  }

  async function handleAdaptAlternative(alt) {
    setAlternatives(null)
    setAdaptError(null)
    setAdaptLoading(true)
    try {
      const result = await api.post(`/recipes/${id}/adapt`, {
        variant_type: pendingVariantType,
        custom_instruction: alt.instruction,
        custom_title: alt.title,
      })
      if (result.can_adapt) {
        setVariants(vs => [...vs, result.variant])
        setActiveTab(result.variant.variant_type)
        await refreshUser()
      }
    } catch (e) {
      console.error('[handleAdaptAlternative] ERROR:', e)
      setAdaptError(e.message || t('failedToGenerateVariant'))
    } finally {
      setAdaptLoading(false)
    }
  }

  function openIngredientAlternatives(ingredientLabel, ingredientIndex) {
    const label = (typeof ingredientLabel === 'string' ? ingredientLabel : '').trim()
    if (!label) return
    setAltIngredient(label)
    setAltIngredientIndex(typeof ingredientIndex === 'number' ? ingredientIndex : null)
    setAltOpen(true)
    setAltLoading(true)
    setAltData(null)
    setAltError(null)
    const dietFilters = activeTab === 'original' ? [] : activeTab.split(',').map(s => s.trim()).filter(Boolean)
    api.post(`/recipes/${id}/ingredient-alternatives`, { ingredient: label, diet_filters: dietFilters })
      .then(data => {
        setAltData(data?.alternatives ?? [])
        setAltLoading(false)
        refreshUser()
      })
      .catch(e => {
        setAltError(e.message || t('failedToAdapt'))
        setAltLoading(false)
      })
  }

  async function applyIngredientReplacement(newIngredient) {
    if (altIngredientIndex == null) return
    const variantType = activeTab === 'original' ? null : activeTab
    try {
      const updated = await api.post(`/recipes/${id}/replace-ingredient`, {
        variant_type: variantType,
        ingredient_index: altIngredientIndex,
        new_ingredient: newIngredient,
      })
      if (variantType) {
        setVariants(vs => vs.map(v => (v.variant_type === variantType ? { ...v, ingredients_pl: updated.ingredients_pl } : v)))
      } else {
        setRecipe(r => (r ? { ...r, ingredients_pl: updated.ingredients_pl } : r))
      }
      setAltOpen(false)
      setAltIngredient(null)
      setAltIngredientIndex(null)
      setAltData(null)
      setAltError(null)
    } catch (e) {
      setAltError(e.message || t('failedToAdapt'))
    }
  }

  if (loading) return (
    <div className="flex justify-center py-20">
      <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (error) return (
    <div className="text-center py-20">
      <div className="text-5xl mb-4">😕</div>
      <p className="text-stone-500 mb-4">{error}</p>
      <button onClick={() => navigate(-1)} className="text-sm text-amber-600 hover:underline font-medium">← {t('back')}</button>
    </div>
  )

  const displayData = activeTab === 'original' ? recipe : variants.find(v => v.variant_type === activeTab)

  const hasIngredients   = displayData?.ingredients_pl?.length > 0
  const hasSteps         = displayData?.steps_pl?.length > 0
  const hasSubstitutions = activeTab === 'original' && Object.keys(recipe.substitutions ?? {}).length > 0
  const hasNotes         = activeTab === 'original' && Object.keys(recipe.notes ?? {}).length > 0
  const contentTags      = activeTab === 'original' ? detectContentTags(recipe.ingredients_pl) : []
  const variantWarnings  = activeTab !== 'original' ? (displayData?.notes?.ostrzeżenia ?? []) : []
  const adaptationSummary = activeTab !== 'original' ? (displayData?.notes?.adaptation_summary ?? '') : ''

  return (
    <div className="max-w-2xl mx-auto pb-16">
      {/* Ingredient alternatives modal */}
      {altOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={e => {
            if (e.target === e.currentTarget) {
              setAltOpen(false)
              setAltIngredient(null)
              setAltIngredientIndex(null)
              setAltData(null)
              setAltError(null)
            }
          }}
        >
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full max-h-[85vh] flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-stone-100">
              <h3 className="text-lg font-bold text-stone-800">
                {t('alternativesFor')} {altIngredient}
              </h3>
              <button
                type="button"
                onClick={() => { setAltOpen(false); setAltIngredient(null); setAltIngredientIndex(null); setAltData(null); setAltError(null) }}
                className="p-2 rounded-xl text-stone-400 hover:bg-stone-100 hover:text-stone-600 transition-colors"
                aria-label={t('close')}
              >
                ✕
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 min-h-0">
              {altLoading && (
                <div className="flex items-center justify-center py-12">
                  <span className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
                  <span className="ml-3 text-sm text-stone-500">{t('loadingAlternatives')}</span>
                </div>
              )}
              {!altLoading && altError && (
                <p className="text-sm text-red-600 py-4">{altError}</p>
              )}
              {!altLoading && !altError && altData && (
                <ul className="space-y-3">
                  {altData.length === 0 ? (
                    <p className="text-sm text-stone-500">{t('noAlternativesFound')}</p>
                  ) : (
                    altData.map((a, i) => (
                      <li key={i} className="p-3 bg-stone-50 rounded-xl border border-stone-100">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <span className="font-semibold text-stone-800 block">{a.name}</span>
                            {a.notes && <span className="text-xs text-stone-500 block mt-0.5">{a.notes}</span>}
                          </div>
                          <button
                            type="button"
                            onClick={() => applyIngredientReplacement(a.name)}
                            className="flex-shrink-0 text-xs font-bold bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg transition-colors active:scale-95"
                          >
                            {t('replace') || 'Replace'}
                          </button>
                        </div>
                      </li>
                    ))
                  )}
                </ul>
              )}
            </div>
            <div className="p-4 border-t border-stone-100 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => { setAltOpen(false); setAltIngredient(null); setAltIngredientIndex(null); setAltData(null); setAltError(null) }}
                className="text-sm font-semibold text-stone-600 hover:text-stone-800 px-3 py-2 rounded-xl hover:bg-stone-50 transition-colors"
              >
                {t('cancel') || 'Cancel'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top bar */}
      <div className="flex items-center justify-between mb-6 gap-3">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm font-medium text-stone-500 hover:text-stone-800 bg-white hover:bg-stone-100 border border-stone-200 px-3 py-1.5 rounded-xl transition-colors flex-shrink-0"
        >
          ← {t('back')}
        </button>

        {/* Adapt dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setAdaptDropdownOpen(v => !v)}
            disabled={adaptLoading}
            className="flex items-center gap-1.5 text-sm font-medium text-stone-600 hover:text-amber-700 bg-white hover:bg-amber-50 border border-stone-200 hover:border-amber-300 px-3 py-1.5 rounded-xl transition-colors disabled:opacity-60"
          >
            {adaptLoading ? (
              <span className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin inline-block" />
            ) : (
              '✨'
            )}
            {t('adaptRecipe')} ▾
          </button>
          {adaptDropdownOpen && (
            <div className="absolute top-full left-0 mt-1.5 bg-white border border-stone-200 rounded-2xl shadow-lg z-20 py-2 min-w-[200px]">
              <p className="px-4 py-1 text-xs font-semibold text-stone-400 uppercase tracking-wide">
                {t('adaptRecipe')}
              </p>
              {VARIANT_OPTIONS.map(opt => {
                const alreadyHasSingle = variants.some(v => v.variant_type === opt.key)
                const isChecked = selectedAdaptTypes.includes(opt.key)
                return (
                  <label
                    key={opt.key}
                    className="flex items-center gap-3 px-4 py-2 text-sm text-stone-700 hover:bg-amber-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {
                        setSelectedAdaptTypes(prev =>
                          prev.includes(opt.key) ? prev.filter(k => k !== opt.key) : [...prev, opt.key]
                        )
                      }}
                      className="rounded border-stone-300 text-amber-500 focus:ring-amber-400"
                    />
                    <span className="flex-1">{t(variantLabelKey(opt.key))}</span>
                    {alreadyHasSingle && <span className="text-xs text-emerald-500">✓</span>}
                  </label>
                )
              })}
              <div className="border-t border-stone-100 mt-2 pt-2 px-2">
                <button
                  type="button"
                  onClick={() => selectedAdaptTypes.length > 0 && handleAdapt(selectedAdaptTypes)}
                  disabled={selectedAdaptTypes.length === 0 || adaptLoading}
                  className="w-full py-2 rounded-xl text-sm font-semibold bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                >
                  {t('applyAdaptations')}
                </button>
              </div>
            </div>
          )}
        </div>

        <button
          onClick={handleToggleFavorite}
          className={`text-2xl transition-all hover:scale-110 flex-shrink-0 ${recipe.is_favorite ? 'text-yellow-400' : 'text-stone-200 hover:text-yellow-300'}`}
          title={recipe.is_favorite ? t('removeFromFavorites') : t('addToFavorites')}
        >
          ★
        </button>
      </div>

      {/* Hero / Title card */}
      <div className="bg-white rounded-3xl border border-stone-100 shadow-sm overflow-hidden mb-6">
        <div className="h-2 bg-gradient-to-r from-amber-400 via-orange-400 to-rose-400" />
        <div className="p-6">
          <div className="flex flex-col md:flex-row md:items-start gap-6">
            <div className="flex-1 min-w-0">
          {showOriginal && activeTab === 'original' ? (
            <div className="grid grid-cols-2 gap-6 mb-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <p className="text-xs font-bold text-stone-400 uppercase tracking-widest">{t('translated')}</p>
                  <span className={`text-xs font-semibold rounded-full px-2.5 py-0.5 ${VARIANT_BADGE.original.cls}`}>
                    {t('original')}
                  </span>
                </div>
                <h1 className="text-xl font-bold text-stone-800 leading-snug">{recipe.title_pl}</h1>
              </div>
              <div className="text-right" dir="rtl">
                <p className="text-xs font-bold text-stone-400 uppercase tracking-widest mb-2" dir="ltr">עברית</p>
                <h1 className="text-xl font-bold text-stone-500 leading-snug">{recipe.title_original}</h1>
              </div>
            </div>
          ) : (
            <div className="mb-4">
              {(() => {
                const baseKey = (activeTab.split(',')[0] || activeTab).replace(/_alt\d+$/, '')
                const badge = VARIANT_BADGE[baseKey] ?? { cls: 'bg-stone-100 text-stone-500' }
                return (
                  <span className={`inline-block text-xs font-semibold rounded-full px-2.5 py-0.5 mb-2 ${badge.cls}`}>
                    {variantDisplayLabel(activeTab, t)}
                  </span>
                )
              })()}
              <h1 className="text-2xl font-bold text-stone-800 leading-snug">{displayData?.title_pl}</h1>
              {activeTab !== 'original' && (
                <button
                  onClick={() => setActiveTab('original')}
                  className="mt-2 text-xs font-medium text-stone-400 hover:text-amber-600 transition-colors"
                >
                  ← {t('backToOriginal')}
                </button>
              )}
            </div>
          )}

          {/* Author (e.g. starter recipes from famous cooks) — original only */}
          {activeTab === 'original' && (recipe.author_name || recipe.author_bio) && (
            <div className="mb-4 flex items-start gap-3 p-3 rounded-xl bg-amber-50 border border-amber-100">
              {recipe.author_image_url && (
                <img
                  src={recipe.author_image_url}
                  alt={recipe.author_name || ''}
                  className="w-12 h-12 rounded-full object-cover flex-shrink-0"
                />
              )}
              <div className="min-w-0">
                {recipe.author_name && (
                  <p className="text-sm font-semibold text-stone-800">By {recipe.author_name}</p>
                )}
                {recipe.author_bio && (
                  <p className="text-xs text-stone-600 mt-0.5">{recipe.author_bio}</p>
                )}
              </div>
            </div>
          )}

          {/* Diet tags (e.g. Kosher — recipe fits this diet) */}
          {recipe.diet_tags?.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {recipe.diet_tags.map((key, i) => (
                <span key={i} className="text-xs font-semibold rounded-full px-3 py-1 bg-emerald-100 text-emerald-800 border border-emerald-200">
                  {key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </span>
              ))}
            </div>
          )}
          {/* Tags */}
          {recipe.tags?.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3">
              {recipe.tags.map((tag, i) => (
                <span key={i} className={`text-xs font-semibold rounded-full px-3 py-1 ${TAG_COLORS[i % TAG_COLORS.length]}`}>
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Content tags — original recipe only */}
          {contentTags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {contentTags.map(tag => (
                <span key={tag.label} className="text-xs font-medium bg-stone-50 text-stone-500 border border-stone-200 rounded-full px-3 py-1">
                  {tag.icon} {tag.label}
                </span>
              ))}
            </div>
          )}

          {/* Time + rating — fast glance for busy cooks */}
          {activeTab === 'original' && (
            <div className="flex flex-wrap items-center gap-3 mb-4">
              {(() => {
                const prep = recipe.prep_time_minutes
                const cook = recipe.cook_time_minutes
                if (typeof prep === 'number' || typeof cook === 'number') {
                  const total = (typeof prep === 'number' ? prep : 0) + (typeof cook === 'number' ? cook : 0)
                  return (
                    <>
                      {typeof prep === 'number' && (
                        <span className="text-xs font-semibold bg-stone-50 text-stone-600 border border-stone-200 rounded-full px-3 py-1">
                          ⏱ Prep: {prep} min
                        </span>
                      )}
                      {typeof cook === 'number' && (
                        <span className="text-xs font-semibold bg-stone-50 text-stone-600 border border-stone-200 rounded-full px-3 py-1">
                          🔥 Cook: {cook} min
                        </span>
                      )}
                      {total > 0 && (
                        <span className="text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 rounded-full px-3 py-1">
                          ⏳ Total: {total} min
                        </span>
                      )}
                    </>
                  )
                }
                // Fallback to existing notes (display as-is)
                const prepLabel = recipe.notes?.czas_przygotowania
                const cookLabel = recipe.notes?.czas_gotowania
                if (prepLabel || cookLabel) {
                  return (
                    <>
                      {prepLabel && (
                        <span className="text-xs font-semibold bg-stone-50 text-stone-600 border border-stone-200 rounded-full px-3 py-1">
                          ⏱ Prep: {String(prepLabel)}
                        </span>
                      )}
                      {cookLabel && (
                        <span className="text-xs font-semibold bg-stone-50 text-stone-600 border border-stone-200 rounded-full px-3 py-1">
                          🔥 Cook: {String(cookLabel)}
                        </span>
                      )}
                    </>
                  )
                }
                return null
              })()}

              <div className="flex items-center gap-1 ml-auto">
                {[1, 2, 3, 4, 5].map(n => {
                  const active = (recipe.user_rating ?? 0) >= n
                  return (
                    <button
                      key={n}
                      type="button"
                      onClick={() => handleSetRating(recipe.user_rating === n ? null : n)}
                      className={`text-lg leading-none transition-transform hover:scale-110 ${active ? 'text-amber-400' : 'text-stone-200 hover:text-amber-300'}`}
                      title={recipe.user_rating ? `Rating: ${recipe.user_rating}/5` : 'Rate this recipe'}
                      aria-label={`Rate ${n} star${n === 1 ? '' : 's'}`}
                    >
                      ★
                    </button>
                  )
                })}
                <span className="text-xs text-stone-400 ml-1">
                  {recipe.user_rating ? `${recipe.user_rating}/5` : 'Rate'}
                </span>
              </div>
            </div>
          )}

          {/* Meta row */}
          <div className="flex items-center justify-between">
            <p className="text-xs text-stone-400">
              {new Date(recipe.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
            {recipe.title_original && activeTab === 'original' && (
              <button
                onClick={() => {
                  const w = window.open('', '_blank', 'noopener,noreferrer')
                  if (!w) return
                  const lang = (recipe.detected_language || 'en').substring(0, 5)
                  const escaped = (recipe.raw_input || '')
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                  const title = (recipe.title_original || 'Original recipe').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                  w.document.write(
                    `<!DOCTYPE html><html lang="${lang}"><head><meta charset="utf-8"><title>${title}</title><style>body{font-family:system-ui,sans-serif;max-width:42rem;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#1c1917;} pre{white-space:pre-wrap;word-wrap:break-word;}</style></head><body><h1>${title}</h1><pre>${escaped}</pre></body></html>`
                  )
                  w.document.close()
                }}
                className="text-xs font-medium text-stone-400 hover:text-amber-600 transition-colors bg-stone-50 hover:bg-amber-50 px-3 py-1.5 rounded-lg border border-stone-100"
              >
                ⇔ {t('showOriginal')}
              </button>
            )}
          </div>
            </div>
            {/* Recipe dish image: large on detail */}
            {activeTab === 'original' && (
              <div className="shrink-0 w-full md:w-64 flex flex-col gap-2">
                <div className="aspect-square max-h-72 md:max-h-none rounded-2xl overflow-hidden bg-stone-100 flex items-center justify-center">
                  {getRecipeImageUrl(recipe.image_url) ? (
                    <img
                      src={getRecipeImageUrl(recipe.image_url)}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span className="text-6xl text-stone-300" aria-hidden>🍽</span>
                  )}
                </div>
                {!recipe.image_url && (
                  <button
                    type="button"
                    onClick={handleGenerateImage}
                    disabled={generateImageLoading}
                    className="text-xs font-medium text-amber-600 hover:text-amber-700 disabled:opacity-50"
                  >
                    {generateImageLoading ? '…' : t('addRecipePhoto')}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Variant tab bar */}
      {(variants.length > 0 || adaptLoading) && (
        <div className="flex gap-1 mb-6 bg-white border border-stone-100 rounded-2xl p-1 shadow-sm overflow-x-auto">
          <button
            onClick={() => setActiveTab('original')}
            className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-colors flex-shrink-0 ${
              activeTab === 'original'
                ? 'bg-amber-500 text-white shadow-sm'
                : 'text-stone-500 hover:text-stone-800 hover:bg-stone-50'
            }`}
          >
            {t('original')}
          </button>
          {variants.map(v => (
            <div
              key={v.variant_type}
              className={`flex items-center gap-0.5 rounded-xl flex-shrink-0 ${
                activeTab === v.variant_type ? 'bg-amber-500 text-white shadow-sm' : ''
              }`}
            >
              <button
                type="button"
                onClick={() => setActiveTab(v.variant_type)}
                className={`px-3 py-1.5 rounded-l-xl text-sm font-medium transition-colors ${
                  activeTab === v.variant_type
                    ? 'bg-amber-500 text-white'
                    : 'text-stone-500 hover:text-stone-800 hover:bg-stone-50'
                }`}
              >
                {variantDisplayLabel(v.variant_type, t)}
              </button>
              <button
                type="button"
                onClick={e => { e.stopPropagation(); handleRemoveVariant(v.variant_type) }}
                title={t('removeVariant')}
                className={`p-1.5 rounded-r-xl text-xs transition-colors ${
                  activeTab === v.variant_type
                    ? 'text-white hover:bg-amber-600'
                    : 'text-stone-400 hover:text-stone-600 hover:bg-stone-100'
                }`}
                aria-label={t('removeVariant')}
              >
                ✕
              </button>
            </div>
          ))}
          {adaptLoading && (
            <div className="px-3 py-1.5 flex items-center gap-1.5 text-sm text-stone-400 flex-shrink-0">
              <span className="w-3.5 h-3.5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
              {t('adapting')}
            </div>
          )}
        </div>
      )}

      {/* Adaptation error */}
      {adaptError && (
        <div
          role="alert"
          className="bg-red-50 border border-red-200 rounded-2xl px-4 py-3 mb-4 flex items-start gap-3 text-sm text-red-700"
        >
          <span className="text-base flex-shrink-0">⚠️</span>
          <span className="flex-1">{adaptError}</span>
          <button onClick={() => setAdaptError(null)} className="text-red-400 hover:text-red-600 flex-shrink-0">✕</button>
        </div>
      )}

      {/* Alternatives panel */}
      {alternatives !== null && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-6">
          <p className="font-semibold text-amber-800 mb-1">
            {t('cannotAdapt')}{' '}
            <span className="italic">{t(variantLabelKey(pendingVariantType))}</span>.
          </p>
          <p className="text-sm text-amber-700 mb-4">{t('chooseOption')}</p>
          <div className="space-y-3">
            {alternatives.map((alt, i) => (
              <div key={i} className="flex items-center justify-between gap-3 bg-white rounded-xl border border-amber-100 px-4 py-3">
                <div className="min-w-0">
                  <p className="font-semibold text-stone-800 text-sm">{alt.title}</p>
                  <p className="text-xs text-stone-500 mt-0.5">{alt.reason}</p>
                </div>
                <button
                  onClick={() => handleAdaptAlternative(alt)}
                  className="flex-shrink-0 bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition-colors active:scale-95"
                >
                  {t('generate')}
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={() => setAlternatives(null)}
            className="mt-3 text-xs text-stone-400 hover:text-stone-600"
          >
            {t('close')}
          </button>
        </div>
      )}

      {/* Pending translation */}
      {!hasIngredients && !hasSteps && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl px-5 py-4 mb-6 flex items-center gap-3">
          <span className="text-2xl">⏳</span>
          <p className="text-sm text-amber-700 font-medium">{t('translationInProgress')}</p>
        </div>
      )}

      {/* Notes metadata (servings, times) — original only */}
      {hasNotes && (
        <div className="flex flex-wrap gap-3 mb-6">
          {Object.entries(recipe.notes).map(([k, v]) => {
            const meta = NOTE_META[k]
            return (
              <div key={k} className="flex items-center gap-2 bg-white border border-stone-100 shadow-sm rounded-2xl px-4 py-2.5">
                <span className="text-lg">{meta?.icon ?? '📝'}</span>
                <div>
                  <div className="text-xs text-stone-400 font-medium leading-none mb-0.5">{meta?.tKey ? t(meta.tKey) : k}</div>
                  <div className="text-sm font-bold text-stone-700">{v}</div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Variant warnings (e.g. unsubstitutable ingredients flagged by the adaptation model) */}
      {(adaptationSummary || variantWarnings.length > 0) && activeTab !== 'original' && (
        <Section title={t('notes')} icon="📝">
          <div className="space-y-3">
            {adaptationSummary && (
              <div className="bg-stone-50 border border-stone-100 rounded-2xl p-4">
                <p className="text-xs font-semibold text-stone-500 uppercase tracking-widest mb-1.5">{t('adaptationSummary')}</p>
                <p className="text-sm text-stone-700">{adaptationSummary}</p>
              </div>
            )}
            {variantWarnings.length > 0 && (
              <div className="bg-amber-50 border border-amber-100 rounded-2xl p-4 space-y-2">
                {variantWarnings.map((msg, i) => (
                  <p key={i} className="text-sm text-amber-800">{msg}</p>
                ))}
              </div>
            )}
          </div>
        </Section>
      )}

      {/* Ingredients */}
      {hasIngredients && (
        <Section title={t('ingredients')} icon="🧅">
          <Card>
            {!ingredientLookupEnabled ? (
              <div className="mb-3 pb-3 border-b border-stone-100">
                <button
                  type="button"
                  onClick={() => setIngredientLookupEnabled(true)}
                  className="text-sm font-medium text-amber-600 hover:text-amber-700 hover:underline"
                >
                  {t('enableIngredientLookup')}
                </button>
              </div>
            ) : null}
            {showOriginal && activeTab === 'original' ? (
              <div>
                <div className="grid grid-cols-2 gap-4 pb-2 mb-1 border-b border-stone-100">
                  <span className="text-xs font-bold text-stone-400 uppercase tracking-wide">Translated</span>
                  <span className="text-xs font-bold text-stone-400 uppercase tracking-wide text-right">עברית</span>
                </div>
                {recipe.ingredients_pl.map((ing, i) => {
                  const pl = typeof ing === 'object' ? `${ing.amount ?? ''} ${ing.name ?? ''}`.trim() : ing
                  const orig = recipe.ingredients_original?.[i]
                  const he = orig ? (typeof orig === 'object' ? `${orig.amount ?? ''} ${orig.name ?? ''}`.trim() : orig) : ''
                  return (
                    <div key={i} className="grid grid-cols-2 gap-4 py-2 border-b border-stone-50 last:border-0">
                      <div className="flex items-start gap-2 min-w-0">
                        <span className="text-sm text-stone-700 break-words">{pl}</span>
                        {ingredientLookupEnabled && (
                          <button
                            type="button"
                            onClick={() => openIngredientAlternatives(pl, i)}
                            className="flex-shrink-0 p-1.5 rounded-lg text-stone-400 hover:text-amber-700 hover:bg-amber-50 border border-transparent hover:border-amber-200 transition-colors"
                            title={t('ingredientAlternatives')}
                            aria-label={t('ingredientAlternatives')}
                          >
                            ⇄
                          </button>
                        )}
                      </div>
                      <span dir="rtl" className="text-sm text-stone-400 text-right">{he}</span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <ul className="space-y-2">
                {displayData.ingredients_pl.map((ing, i) => {
                  const label = typeof ing === 'object' ? `${ing.amount ?? ''} ${ing.name ?? ''}`.trim() : ing
                  return (
                    <li key={i} className="flex items-start gap-3 text-sm text-stone-700 py-1 border-b border-stone-50 last:border-0">
                      <span className="w-5 h-5 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      <div className="flex items-start justify-between gap-2 flex-1 min-w-0">
                        <span className="text-left break-words">{label}</span>
                        {ingredientLookupEnabled && (
                          <button
                            type="button"
                            onClick={() => openIngredientAlternatives(label, i)}
                            className="flex-shrink-0 p-1.5 rounded-lg text-stone-400 hover:text-amber-700 hover:bg-amber-50 border border-transparent hover:border-amber-200 transition-colors"
                            title={t('ingredientAlternatives')}
                            aria-label={t('ingredientAlternatives')}
                          >
                            ⇄
                          </button>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>
        </Section>
      )}

      {/* Steps */}
      {hasSteps && (
        <Section title={t('instructions')} icon="👨‍🍳">
          <Card>
            <ol className="space-y-5">
              {displayData.steps_pl.map((step, i) => (
                <li key={i} className="flex gap-4">
                  <span className="flex-shrink-0 w-7 h-7 bg-gradient-to-br from-amber-400 to-orange-400 text-white rounded-full flex items-center justify-center text-xs font-bold shadow-sm">
                    {i + 1}
                  </span>
                  <p className="text-sm text-stone-700 leading-relaxed pt-0.5">{step}</p>
                </li>
              ))}
            </ol>
          </Card>
        </Section>
      )}

      {/* Substitutions — original recipe only */}
      {hasSubstitutions && (
        <Section title={t('ingredientSubstitutions')} icon="🔄">
          <div className="bg-amber-50 border border-amber-100 rounded-2xl p-4 space-y-3">
            {Object.entries(recipe.substitutions).map(([orig, sub]) => (
              <div key={orig} className="flex gap-3 text-sm items-start">
                <span className="font-semibold text-amber-800 flex-shrink-0 min-w-0">{orig}</span>
                <span className="text-amber-500 flex-shrink-0">→</span>
                <span className="text-stone-600">{sub}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* User notes */}
      <Section title={t('myNotes')} icon="📝">
        <Card>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={4}
            placeholder={t('notesPlaceholder')}
            className="w-full text-sm text-stone-700 placeholder-stone-300 resize-none focus:outline-none leading-relaxed"
          />
          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-stone-100">
            <button
              onClick={handleSaveNotes}
              className="bg-amber-500 hover:bg-amber-600 text-white rounded-xl px-5 py-2 text-sm font-bold transition-all hover:shadow-md hover:shadow-amber-200 active:scale-95"
            >
              {t('saveNotes')}
            </button>
            {notesSaved && (
              <span className="text-sm text-emerald-600 font-medium flex items-center gap-1">
                <span>✓</span> {t('saved')}
              </span>
            )}
          </div>
        </Card>
      </Section>

    </div>
  )
}
