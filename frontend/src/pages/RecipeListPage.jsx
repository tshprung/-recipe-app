import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useShoppingList } from '../context/ShoppingListContext'
import AddRecipeModal from '../components/AddRecipeModal'

const CARD_ACCENTS = [
  'from-amber-400 to-orange-400',
  'from-orange-400 to-rose-400',
  'from-lime-500 to-emerald-400',
  'from-teal-400 to-cyan-400',
  'from-rose-400 to-pink-400',
  'from-violet-400 to-purple-400',
]

const TAG_COLORS = [
  'bg-amber-100 text-amber-700',
  'bg-orange-100 text-orange-700',
  'bg-rose-100 text-rose-700',
  'bg-emerald-100 text-emerald-700',
  'bg-lime-100 text-lime-700',
  'bg-teal-100 text-teal-700',
  'bg-cyan-100 text-cyan-700',
  'bg-violet-100 text-violet-700',
]

function RecipeCard({ recipe, onToggleFavorite, onDelete, onAddToList, onRemoveFromList }) {
  const navigate = useNavigate()
  const { isInList, actionLoadingId } = useShoppingList()
  const accent = CARD_ACCENTS[recipe.id % CARD_ACCENTS.length]
  const inList = isInList(recipe.id)
  const isActioning = actionLoadingId === recipe.id

  return (
    <div
      onClick={() => navigate(`/recipes/${recipe.id}`)}
      className="bg-white rounded-2xl shadow-sm hover:shadow-xl border border-stone-100 overflow-hidden cursor-pointer transition-all duration-200 group hover:-translate-y-1 flex flex-col"
    >
      {/* Accent strip */}
      <div className={`h-1.5 bg-gradient-to-r ${accent}`} />

      <div className="p-5 flex flex-col flex-1">
        {/* Title */}
        <h3 className="font-bold text-stone-800 text-base leading-snug mb-1 line-clamp-2 group-hover:text-amber-700 transition-colors">
          {recipe.title_pl}
        </h3>

        {/* Tags */}
        {recipe.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2 mb-3">
            {recipe.tags.slice(0, 3).map((tag, i) => (
              <span
                key={i}
                className={`text-xs font-medium rounded-full px-2.5 py-0.5 ${TAG_COLORS[i % TAG_COLORS.length]}`}
              >
                {tag}
              </span>
            ))}
            {recipe.tags.length > 3 && (
              <span className="text-xs text-stone-400">+{recipe.tags.length - 3}</span>
            )}
          </div>
        )}

        <div className="flex-1" />

        {/* Footer */}
        <div className="pt-3 border-t border-stone-100 mt-2 space-y-2">
          {/* Add / Remove shopping list button */}
          <button
            onClick={e => {
              e.stopPropagation()
              inList ? onRemoveFromList(recipe.id) : onAddToList(recipe.id)
            }}
            disabled={isActioning}
            className={`w-full flex items-center justify-center gap-1.5 rounded-xl py-1.5 text-xs font-semibold transition-all ${
              inList
                ? 'bg-amber-50 text-amber-700 hover:bg-red-50 hover:text-red-600 border border-amber-200 hover:border-red-200'
                : 'bg-stone-50 text-stone-500 hover:bg-amber-50 hover:text-amber-600 border border-stone-200 hover:border-amber-200'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {isActioning ? (
              <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : inList ? (
              <>✓ Na liście zakupów</>
            ) : (
              <>+ Dodaj do listy</>
            )}
          </button>

          {/* Favorite + Delete */}
          <div className="flex justify-between items-center">
            <button
              onClick={e => { e.stopPropagation(); onToggleFavorite(recipe) }}
              className={`text-xl transition-all hover:scale-110 ${recipe.is_favorite ? 'text-yellow-400' : 'text-stone-200 hover:text-yellow-300'}`}
              title={recipe.is_favorite ? 'Usuń z ulubionych' : 'Dodaj do ulubionych'}
            >
              ★
            </button>
            <button
              onClick={e => { e.stopPropagation(); onDelete(recipe) }}
              className="text-stone-300 hover:text-red-400 transition-colors text-sm p-1 rounded-lg hover:bg-red-50"
              title="Usuń przepis"
            >
              🗑
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function EmptyState({ onAdd }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 px-4 text-center">
      <div className="text-7xl mb-6 select-none">🥘</div>
      <h3 className="text-xl font-bold text-stone-700 mb-2">
        Twoja książka kulinarna jest pusta
      </h3>
      <p className="text-stone-400 max-w-sm mb-8 leading-relaxed">
        Wklej przepis w języku hebrajskim, a my przetłumaczymy go na polski
        i dostosujemy składniki do polskiego rynku.
      </p>
      <button
        onClick={onAdd}
        className="bg-amber-500 hover:bg-amber-600 text-white px-6 py-3 rounded-2xl font-bold hover:shadow-lg hover:shadow-amber-200 transition-all active:scale-95 flex items-center gap-2"
      >
        <span className="text-lg">+</span>
        Dodaj pierwszy przepis
      </button>
    </div>
  )
}

export default function RecipeListPage() {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [filter, setFilter] = useState('all')
  const [toast, setToast] = useState(null)

  const { addRecipe, removeRecipe, isInList, evictFromList } = useShoppingList()

  const fetchRecipes = useCallback(async () => {
    try {
      const data = await api.get('/recipes/')
      setRecipes(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchRecipes() }, [fetchRecipes])

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(null), 2500)
  }

  async function handleToggleFavorite(recipe) {
    try {
      const updated = await api.patch(`/recipes/${recipe.id}/favorite`, {
        is_favorite: !recipe.is_favorite,
      })
      setRecipes(rs => rs.map(r => r.id === updated.id ? updated : r))
    } catch (e) {
      console.error(e)
    }
  }

  async function handleDelete(recipe) {
    if (!confirm(`Usunąć przepis "${recipe.title_pl}"?`)) return
    try {
      await api.delete(`/recipes/${recipe.id}`)
      setRecipes(rs => rs.filter(r => r.id !== recipe.id))
      evictFromList(recipe.id)
    } catch (e) {
      console.error(e)
    }
  }

  function handleAddToList(id) {
    if (isInList(id)) {
      showToast('Przepis już jest na liście zakupów')
      return
    }
    addRecipe(id)
  }

  function handleRemoveFromList(id) {
    removeRecipe(id)
  }

  const visible = filter === 'favorites' ? recipes.filter(r => r.is_favorite) : recipes
  const favCount = recipes.filter(r => r.is_favorite).length

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-stone-800 text-white px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg pointer-events-none">
          {toast}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-wrap gap-4 justify-between items-start mb-8">
        <div>
          <h2 className="text-2xl font-bold text-stone-800">Moje Przepisy</h2>
          <p className="text-stone-400 text-sm mt-0.5">
            {recipes.length === 0 ? 'Brak przepisów' : `${recipes.length} ${recipes.length === 1 ? 'przepis' : 'przepisów'}`}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Filter pills */}
          <div className="flex bg-white border border-stone-200 rounded-xl overflow-hidden shadow-sm text-sm">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-amber-500 text-white'
                  : 'text-stone-500 hover:bg-stone-50'
              }`}
            >
              Wszystkie
            </button>
            <button
              onClick={() => setFilter('favorites')}
              className={`px-4 py-2 font-medium transition-colors flex items-center gap-1.5 ${
                filter === 'favorites'
                  ? 'bg-amber-500 text-white'
                  : 'text-stone-500 hover:bg-stone-50'
              }`}
            >
              <span>★</span>
              <span>Ulubione</span>
              {favCount > 0 && (
                <span className={`text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold ${
                  filter === 'favorites' ? 'bg-white/20' : 'bg-amber-100 text-amber-700'
                }`}>
                  {favCount}
                </span>
              )}
            </button>
          </div>

          <button
            onClick={() => setShowAdd(true)}
            className="bg-amber-500 hover:bg-amber-600 text-white rounded-xl px-5 py-2 text-sm font-bold hover:shadow-lg hover:shadow-amber-200 transition-all active:scale-95 flex items-center gap-1.5"
          >
            <span className="text-base leading-none">+</span>
            <span>Dodaj</span>
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-20">
          <div className="w-10 h-10 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : visible.length === 0 && filter === 'all' ? (
        <EmptyState onAdd={() => setShowAdd(true)} />
      ) : visible.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-5xl mb-4">⭐</div>
          <p className="text-stone-500 font-medium mb-1">Brak ulubionych</p>
          <p className="text-sm text-stone-400">Oznacz przepis gwiazdką, aby go tu zobaczyć</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {visible.map(recipe => (
            <RecipeCard
              key={recipe.id}
              recipe={recipe}
              onToggleFavorite={handleToggleFavorite}
              onDelete={handleDelete}
              onAddToList={handleAddToList}
              onRemoveFromList={handleRemoveFromList}
            />
          ))}
        </div>
      )}

      {showAdd && (
        <AddRecipeModal
          onClose={() => setShowAdd(false)}
          onCreated={recipe => {
            setRecipes(rs => [recipe, ...rs])
            setShowAdd(false)
          }}
        />
      )}
    </div>
  )
}
