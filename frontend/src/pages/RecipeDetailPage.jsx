import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
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
]

// Badge shown on the recipe hero card for original and each variant
const VARIANT_BADGE = {
  original:    { label: 'Original',    cls: 'bg-stone-100 text-stone-500' },
  vegetarian:  { label: 'Vegetarian', cls: 'bg-emerald-100 text-emerald-700' },
  vegan:       { label: 'Vegan',      cls: 'bg-emerald-100 text-emerald-700' },
  dairy_free:  { label: 'Dairy free', cls: 'bg-sky-100 text-sky-700' },
  gluten_free: { label: 'Gluten free', cls: 'bg-violet-100 text-violet-700' },
  kosher:      { label: 'Kosher',     cls: 'bg-blue-100 text-blue-700' },
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
  return key
}

export default function RecipeDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
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
  const [alternatives, setAlternatives] = useState(null)
  const [pendingVariantType, setPendingVariantType] = useState(null)
  const [adaptError, setAdaptError] = useState(null)
  const dropdownRef = useRef(null)

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

  async function handleAdapt(type) {
    console.log('[handleAdapt] button clicked, type:', type)
    setAdaptDropdownOpen(false)
    setAdaptError(null)
    if (variants.find(v => v.variant_type === type)) {
      console.log('[handleAdapt] variant already cached, switching tab')
      setActiveTab(type)
      return
    }
    setAdaptLoading(true)
    setAlternatives(null)
    setPendingVariantType(type)
    try {
      console.log('[handleAdapt] calling POST /recipes/' + id + '/adapt')
      const result = await api.post(`/recipes/${id}/adapt`, { variant_type: type })
      console.log('[handleAdapt] API response:', result)
      if (result.can_adapt) {
        console.log('[handleAdapt] can_adapt=true, variant:', result.variant)
        setVariants(vs => [...vs, result.variant])
        setActiveTab(result.variant.variant_type)
      } else {
        console.log('[handleAdapt] can_adapt=false, alternatives:', result.alternatives)
        setAlternatives(result.alternatives)
      }
    } catch (e) {
      console.error('[handleAdapt] ERROR:', e)
      setAdaptError(e.message || t('failedToAdapt'))
    } finally {
      setAdaptLoading(false)
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
      }
    } catch (e) {
      console.error('[handleAdaptAlternative] ERROR:', e)
      setAdaptError(e.message || t('failedToGenerateVariant'))
    } finally {
      setAdaptLoading(false)
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

  return (
    <div className="max-w-2xl mx-auto pb-16">
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
            <div className="absolute top-full left-0 mt-1.5 bg-white border border-stone-200 rounded-2xl shadow-lg z-20 py-1.5 min-w-[180px]">
              {VARIANT_OPTIONS.map(opt => {
                const alreadyHas = variants.find(v => v.variant_type === opt.key)
                return (
                  <button
                    key={opt.key}
                    onClick={() => handleAdapt(opt.key)}
                    className="w-full text-left px-4 py-2 text-sm text-stone-700 hover:bg-amber-50 hover:text-amber-700 transition-colors flex items-center justify-between"
                  >
                    {t(variantLabelKey(opt.key))}
                    {alreadyHas && <span className="text-xs text-emerald-500 font-medium">✓</span>}
                  </button>
                )
              })}
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
                const baseKey = activeTab.replace(/_alt\d+$/, '')
                const badge = VARIANT_BADGE[baseKey] ?? { cls: 'bg-stone-100 text-stone-500' }
                return (
                  <span className={`inline-block text-xs font-semibold rounded-full px-2.5 py-0.5 mb-2 ${badge.cls}`}>
                    {t(variantLabelKey(baseKey))}
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

          {/* Meta row */}
          <div className="flex items-center justify-between">
            <p className="text-xs text-stone-400">
              {new Date(recipe.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
            {recipe.title_original && activeTab === 'original' && (
              <button
                onClick={() => setShowOriginal(v => !v)}
                className="text-xs font-medium text-stone-400 hover:text-amber-600 transition-colors bg-stone-50 hover:bg-amber-50 px-3 py-1.5 rounded-lg border border-stone-100"
              >
                {showOriginal ? `✕ ${t('hideOriginal')}` : `⇔ ${t('showOriginal')}`}
              </button>
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
            <button
              key={v.variant_type}
              onClick={() => setActiveTab(v.variant_type)}
              className={`px-3 py-1.5 rounded-xl text-sm font-medium transition-colors flex-shrink-0 ${
                activeTab === v.variant_type
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'text-stone-500 hover:text-stone-800 hover:bg-stone-50'
              }`}
            >
              {t(variantLabelKey(v.variant_type))}
            </button>
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
      {variantWarnings.length > 0 && (
        <Section title={t('notes')} icon="⚠️">
          <div className="bg-amber-50 border border-amber-100 rounded-2xl p-4 space-y-2">
            {variantWarnings.map((msg, i) => (
              <p key={i} className="text-sm text-amber-800">{msg}</p>
            ))}
          </div>
        </Section>
      )}

      {/* Ingredients */}
      {hasIngredients && (
        <Section title={t('ingredients')} icon="🧅">
          <Card>
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
                      <span className="text-sm text-stone-700">{pl}</span>
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
                      {label}
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
