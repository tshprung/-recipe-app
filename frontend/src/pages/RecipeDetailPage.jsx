import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'

const TAG_COLORS = [
  'bg-amber-100 text-amber-700',
  'bg-orange-100 text-orange-700',
  'bg-rose-100 text-rose-700',
  'bg-emerald-100 text-emerald-700',
  'bg-lime-100 text-lime-700',
  'bg-teal-100 text-teal-700',
]

const NOTE_META = {
  porcje:              { label: 'Porcje',         icon: '🍽' },
  czas_przygotowania:  { label: 'Przygotowanie',  icon: '⏱' },
  czas_gotowania:      { label: 'Gotowanie',      icon: '🔥' },
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

export default function RecipeDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [recipe, setRecipe] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notes, setNotes] = useState('')
  const [notesSaved, setNotesSaved] = useState(false)
  const [showOriginal, setShowOriginal] = useState(false)

  useEffect(() => {
    api.get(`/recipes/${id}`)
      .then(data => {
        setRecipe(data)
        setNotes(data.user_notes ?? '')
      })
      .catch(() => setError('Nie znaleziono przepisu'))
      .finally(() => setLoading(false))
  }, [id])

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

  if (loading) return (
    <div className="flex justify-center py-20">
      <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (error) return (
    <div className="text-center py-20">
      <div className="text-5xl mb-4">😕</div>
      <p className="text-stone-500 mb-4">{error}</p>
      <button onClick={() => navigate(-1)} className="text-sm text-amber-600 hover:underline font-medium">← Wróć</button>
    </div>
  )

  const hasIngredients   = recipe.ingredients_pl?.length > 0
  const hasSteps         = recipe.steps_pl?.length > 0
  const hasSubstitutions = Object.keys(recipe.substitutions ?? {}).length > 0
  const hasNotes         = Object.keys(recipe.notes ?? {}).length > 0

  return (
    <div className="max-w-2xl mx-auto pb-16">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm font-medium text-stone-500 hover:text-stone-800 bg-white hover:bg-stone-100 border border-stone-200 px-3 py-1.5 rounded-xl transition-colors"
        >
          ← Wróć
        </button>
        <button
          onClick={handleToggleFavorite}
          className={`text-2xl transition-all hover:scale-110 ${recipe.is_favorite ? 'text-yellow-400' : 'text-stone-200 hover:text-yellow-300'}`}
          title={recipe.is_favorite ? 'Usuń z ulubionych' : 'Dodaj do ulubionych'}
        >
          ★
        </button>
      </div>

      {/* Hero / Title card */}
      <div className="bg-white rounded-3xl border border-stone-100 shadow-sm overflow-hidden mb-6">
        <div className="h-2 bg-gradient-to-r from-amber-400 via-orange-400 to-rose-400" />
        <div className="p-6">
          {showOriginal ? (
            <div className="grid grid-cols-2 gap-6 mb-4">
              <div>
                <p className="text-xs font-bold text-stone-400 uppercase tracking-widest mb-2">Polski</p>
                <h1 className="text-xl font-bold text-stone-800 leading-snug">{recipe.title_pl}</h1>
              </div>
              <div className="text-right" dir="rtl">
                <p className="text-xs font-bold text-stone-400 uppercase tracking-widest mb-2" dir="ltr">עברית</p>
                <h1 className="text-xl font-bold text-stone-500 leading-snug">{recipe.title_original}</h1>
              </div>
            </div>
          ) : (
            <h1 className="text-2xl font-bold text-stone-800 leading-snug mb-4">{recipe.title_pl}</h1>
          )}

          {/* Tags */}
          {recipe.tags?.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {recipe.tags.map((tag, i) => (
                <span key={i} className={`text-xs font-semibold rounded-full px-3 py-1 ${TAG_COLORS[i % TAG_COLORS.length]}`}>
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Meta row */}
          <div className="flex items-center justify-between">
            <p className="text-xs text-stone-400">
              {new Date(recipe.created_at).toLocaleDateString('pl-PL', { day: 'numeric', month: 'long', year: 'numeric' })}
            </p>
            {recipe.title_original && (
              <button
                onClick={() => setShowOriginal(v => !v)}
                className="text-xs font-medium text-stone-400 hover:text-amber-600 transition-colors bg-stone-50 hover:bg-amber-50 px-3 py-1.5 rounded-lg border border-stone-100"
              >
                {showOriginal ? '✕ Ukryj oryginał' : '⇔ Pokaż oryginał'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Pending translation */}
      {!hasIngredients && !hasSteps && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl px-5 py-4 mb-6 flex items-center gap-3">
          <span className="text-2xl">⏳</span>
          <p className="text-sm text-amber-700 font-medium">Tłumaczenie w toku — treść pojawi się wkrótce.</p>
        </div>
      )}

      {/* Notes metadata (servings, times) */}
      {hasNotes && (
        <div className="flex flex-wrap gap-3 mb-6">
          {Object.entries(recipe.notes).map(([k, v]) => {
            const meta = NOTE_META[k]
            return (
              <div key={k} className="flex items-center gap-2 bg-white border border-stone-100 shadow-sm rounded-2xl px-4 py-2.5">
                <span className="text-lg">{meta?.icon ?? '📝'}</span>
                <div>
                  <div className="text-xs text-stone-400 font-medium leading-none mb-0.5">{meta?.label ?? k}</div>
                  <div className="text-sm font-bold text-stone-700">{v}</div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Ingredients */}
      {hasIngredients && (
        <Section title="Składniki" icon="🧅">
          <Card>
            {showOriginal ? (
              <div>
                <div className="grid grid-cols-2 gap-4 pb-2 mb-1 border-b border-stone-100">
                  <span className="text-xs font-bold text-stone-400 uppercase tracking-wide">Polski</span>
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
                {recipe.ingredients_pl.map((ing, i) => {
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
        <Section title="Przygotowanie" icon="👨‍🍳">
          <Card>
            <ol className="space-y-5">
              {recipe.steps_pl.map((step, i) => (
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

      {/* Substitutions */}
      {hasSubstitutions && (
        <Section title="Zamienniki składników" icon="🔄">
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
      <Section title="Moje notatki" icon="📝">
        <Card>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={4}
            placeholder="Dodaj własne notatki, wskazówki lub modyfikacje…"
            className="w-full text-sm text-stone-700 placeholder-stone-300 resize-none focus:outline-none leading-relaxed"
          />
          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-stone-100">
            <button
              onClick={handleSaveNotes}
              className="bg-amber-500 hover:bg-amber-600 text-white rounded-xl px-5 py-2 text-sm font-bold transition-all hover:shadow-md hover:shadow-amber-200 active:scale-95"
            >
              Zapisz notatki
            </button>
            {notesSaved && (
              <span className="text-sm text-emerald-600 font-medium flex items-center gap-1">
                <span>✓</span> Zapisano
              </span>
            )}
          </div>
        </Card>
      </Section>

    </div>
  )
}
