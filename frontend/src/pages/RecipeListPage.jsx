import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import AddRecipeModal from '../components/AddRecipeModal'

function RecipeCard({ recipe, onToggleFavorite, onDelete }) {
  const navigate = useNavigate()

  return (
    <div
      onClick={() => navigate(`/recipes/${recipe.id}`)}
      className="bg-white rounded-xl border border-gray-200 p-4 cursor-pointer hover:shadow-md hover:border-indigo-200 transition-all group"
    >
      <h3 className="font-semibold text-gray-900 mb-1 line-clamp-1 group-hover:text-indigo-700 transition-colors">
        {recipe.title_pl}
      </h3>
      <p dir="rtl" className="text-sm text-gray-400 mb-3 line-clamp-1 text-right">
        {recipe.title_original}
      </p>

      {recipe.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {recipe.tags.slice(0, 4).map((tag, i) => (
            <span key={i} className="text-xs bg-indigo-50 text-indigo-600 rounded-full px-2.5 py-0.5">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex justify-between items-center pt-2 border-t border-gray-100">
        <button
          onClick={e => { e.stopPropagation(); onToggleFavorite(recipe) }}
          className={`text-xl transition-colors ${recipe.is_favorite ? 'text-yellow-400' : 'text-gray-200 hover:text-yellow-300'}`}
          title={recipe.is_favorite ? 'Usuń z ulubionych' : 'Dodaj do ulubionych'}
        >
          ★
        </button>
        <button
          onClick={e => { e.stopPropagation(); onDelete(recipe) }}
          className="text-gray-300 hover:text-red-400 transition-colors text-sm px-1"
          title="Usuń przepis"
        >
          🗑
        </button>
      </div>
    </div>
  )
}

export default function RecipeListPage() {
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [filter, setFilter] = useState('all') // 'all' | 'favorites'

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
    } catch (e) {
      console.error(e)
    }
  }

  const visible = filter === 'favorites'
    ? recipes.filter(r => r.is_favorite)
    : recipes

  return (
    <div>
      {/* Header */}
      <div className="flex flex-wrap gap-3 justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Moje Przepisy</h2>
          <p className="text-sm text-gray-400">{recipes.length} przepisów</p>
        </div>
        <div className="flex gap-2">
          <div className="flex rounded-xl border border-gray-200 overflow-hidden text-sm">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1.5 transition-colors ${filter === 'all' ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Wszystkie
            </button>
            <button
              onClick={() => setFilter('favorites')}
              className={`px-3 py-1.5 transition-colors ${filter === 'favorites' ? 'bg-indigo-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              ★ Ulubione
            </button>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="bg-indigo-600 text-white rounded-xl px-4 py-1.5 text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            + Dodaj
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">Ładowanie…</div>
      ) : visible.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-4xl mb-3">🍽</p>
          <p className="text-gray-500 font-medium mb-1">
            {filter === 'favorites' ? 'Brak ulubionych przepisów' : 'Brak przepisów'}
          </p>
          <p className="text-sm text-gray-400">
            {filter === 'favorites'
              ? 'Oznacz przepis gwiazdką, aby go tu zobaczyć'
              : 'Dodaj swój pierwszy hebrajski przepis'}
          </p>
          {filter === 'all' && (
            <button
              onClick={() => setShowAdd(true)}
              className="mt-4 bg-indigo-600 text-white rounded-xl px-5 py-2 text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              + Dodaj pierwszy przepis
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {visible.map(recipe => (
            <RecipeCard
              key={recipe.id}
              recipe={recipe}
              onToggleFavorite={handleToggleFavorite}
              onDelete={handleDelete}
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
