import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import ShoppingListModal from '../components/ShoppingListModal'

function Section({ title, children }) {
  return (
    <div className="mb-8">
      <h2 className="text-base font-semibold text-gray-900 mb-3 pb-2 border-b border-gray-100">
        {title}
      </h2>
      {children}
    </div>
  )
}

function IngredientItem({ ing }) {
  const label = typeof ing === 'object' ? `${ing.amount ?? ''} ${ing.name ?? ''}`.trim() : ing
  return (
    <li className="flex items-start gap-2 text-sm text-gray-700 py-1">
      <span className="text-indigo-400 mt-0.5 flex-shrink-0">•</span>
      <span>{label}</span>
    </li>
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
  const [showShopping, setShowShopping] = useState(false)
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
      const updated = await api.patch(`/recipes/${id}/favorite`, {
        is_favorite: !recipe.is_favorite,
      })
      setRecipe(updated)
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) return <div className="text-center py-16 text-gray-400">Ładowanie…</div>
  if (error)   return (
    <div className="text-center py-16">
      <p className="text-red-500 mb-4">{error}</p>
      <button onClick={() => navigate(-1)} className="text-sm text-indigo-600 hover:underline">← Wróć</button>
    </div>
  )

  const hasIngredientsPl = recipe.ingredients_pl?.length > 0
  const hasSteps         = recipe.steps_pl?.length > 0
  const hasSubstitutions   = Object.keys(recipe.substitutions ?? {}).length > 0
  const hasNotes           = Object.keys(recipe.notes ?? {}).length > 0

  return (
    <div className="max-w-2xl mx-auto pb-12">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          ← Wróć
        </button>
        <button
          onClick={handleToggleFavorite}
          className={`text-2xl transition-colors ${recipe.is_favorite ? 'text-yellow-400' : 'text-gray-200 hover:text-yellow-300'}`}
          title={recipe.is_favorite ? 'Usuń z ulubionych' : 'Dodaj do ulubionych'}
        >
          ★
        </button>
      </div>

      {/* Title block */}
      <div className="mb-8">
        {showOriginal ? (
          <div className="grid grid-cols-2 gap-6 mb-3">
            <div>
              <p className="text-xs font-medium text-gray-400 mb-1">Polski</p>
              <h1 className="text-xl font-bold text-gray-900 leading-tight">{recipe.title_pl}</h1>
            </div>
            <div className="text-right" dir="rtl">
              <p className="text-xs font-medium text-gray-400 mb-1" dir="ltr">עברית</p>
              <h1 className="text-xl font-bold text-gray-600 leading-tight">{recipe.title_original}</h1>
            </div>
          </div>
        ) : (
          <h1 className="text-2xl font-bold text-gray-900 leading-tight mb-3">{recipe.title_pl}</h1>
        )}

        <div className="flex flex-wrap gap-1">
          {recipe.tags?.map((tag, i) => (
            <span key={i} className="text-xs bg-indigo-50 text-indigo-600 rounded-full px-3 py-1">
              {tag}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-between mt-3">
          <p className="text-xs text-gray-400">
            Dodano: {new Date(recipe.created_at).toLocaleDateString('pl-PL')}
            {' · '}
            {recipe.source_language.toUpperCase()} → {recipe.target_language.toUpperCase()}
          </p>
          {recipe.title_original && (
            <button
              onClick={() => setShowOriginal(v => !v)}
              className="text-xs text-gray-400 hover:text-indigo-600 transition-colors flex items-center gap-1"
            >
              <span>{showOriginal ? '✕ Ukryj oryginał' : '⇔ Pokaż oryginał'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Placeholder when translation is pending */}
      {!hasIngredientsPl && !hasSteps && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-8 text-sm text-amber-700">
          Tłumaczenie w toku — treść przepisu pojawi się wkrótce.
        </div>
      )}

      {/* Ingredients */}
      {hasIngredientsPl && (
        <Section title="Składniki">
          {showOriginal ? (
            <div>
              <div className="grid grid-cols-2 gap-4 pb-1.5 mb-1 border-b border-gray-200">
                <span className="text-xs font-medium text-gray-400">Polski</span>
                <span className="text-xs font-medium text-gray-400 text-right">עברית</span>
              </div>
              {recipe.ingredients_pl.map((ing, i) => {
                const pl = typeof ing === 'object' ? `${ing.amount ?? ''} ${ing.name ?? ''}`.trim() : ing
                const orig = recipe.ingredients_original?.[i]
                const he = orig ? (typeof orig === 'object' ? `${orig.amount ?? ''} ${orig.name ?? ''}`.trim() : orig) : ''
                return (
                  <div key={i} className="grid grid-cols-2 gap-4 py-1.5 border-b border-gray-50 last:border-0">
                    <span className="text-sm text-gray-700">{pl}</span>
                    <span dir="rtl" className="text-sm text-gray-500 text-right">{he}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <ul className="divide-y divide-gray-50">
              {recipe.ingredients_pl.map((ing, i) => <IngredientItem key={i} ing={ing} />)}
            </ul>
          )}
        </Section>
      )}

      {/* Steps */}
      {hasSteps && (
        <Section title="Przygotowanie">
          <ol className="space-y-4">
            {recipe.steps_pl.map((step, i) => (
              <li key={i} className="flex gap-4 text-sm text-gray-700">
                <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xs font-semibold">
                  {i + 1}
                </span>
                <span className="pt-0.5 leading-relaxed">{step}</span>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {/* Substitutions */}
      {hasSubstitutions && (
        <Section title="Zamienniki składników">
          <dl className="space-y-2">
            {Object.entries(recipe.substitutions).map(([orig, sub]) => (
              <div key={orig} className="flex gap-2 text-sm">
                <dt className="font-medium text-gray-500 flex-shrink-0">{orig}:</dt>
                <dd className="text-gray-700">{sub}</dd>
              </div>
            ))}
          </dl>
        </Section>
      )}

      {/* Notes */}
      {hasNotes && (
        <Section title="Uwagi">
          <div className="space-y-1 text-sm text-gray-700">
            {Object.entries(recipe.notes).map(([k, v]) => (
              <p key={k}>{typeof v === 'string' ? v : `${k}: ${JSON.stringify(v)}`}</p>
            ))}
          </div>
        </Section>
      )}

      {/* User notes */}
      <Section title="Moje notatki">
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={4}
          placeholder="Dodaj własne notatki do tego przepisu…"
          className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
        />
        <div className="flex items-center gap-3 mt-2">
          <button
            onClick={handleSaveNotes}
            className="bg-indigo-600 text-white rounded-xl px-4 py-1.5 text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Zapisz
          </button>
          {notesSaved && <span className="text-sm text-green-600">Zapisano ✓</span>}
        </div>
      </Section>

      {/* Shopping list */}
      <button
        onClick={() => setShowShopping(true)}
        className="w-full border-2 border-indigo-200 text-indigo-600 rounded-xl py-3 text-sm font-semibold hover:bg-indigo-50 transition-colors"
      >
        🛒 Lista zakupów
      </button>

      {showShopping && (
        <ShoppingListModal
          ingredients={recipe.ingredients_pl}
          title={recipe.title_pl}
          onClose={() => setShowShopping(false)}
        />
      )}
    </div>
  )
}
