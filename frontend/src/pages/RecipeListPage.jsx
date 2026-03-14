import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { api, getRecipeImageUrl } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
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
  const { t } = useLanguage()
  const { isInList, actionLoadingId } = useShoppingList()
  const [imageError, setImageError] = useState(false)
  const accent = CARD_ACCENTS[recipe.id % CARD_ACCENTS.length]
  const inList = isInList(recipe.id)
  const isActioning = actionLoadingId === recipe.id
  const prep = recipe.prep_time_minutes
  const cook = recipe.cook_time_minutes
  const total = (typeof prep === 'number' ? prep : 0) + (typeof cook === 'number' ? cook : 0)
  const imageUrl = getRecipeImageUrl(recipe.image_url)

  return (
    <div
      onClick={() => navigate(`/recipes/${recipe.id}`, { state: { recipe } })}
      className="bg-white rounded-2xl shadow-sm hover:shadow-xl border border-stone-100 overflow-hidden cursor-pointer transition-all duration-200 group hover:-translate-y-1 flex flex-col"
    >
      {/* Accent strip */}
      <div className={`h-1.5 bg-gradient-to-r ${accent}`} />

      <div className="p-5 flex flex-col flex-1">
        <div className="flex gap-4 flex-1 min-h-0">
          <div className="flex-1 min-w-0 flex flex-col">
        {/* Title */}
        <h3 className="font-bold text-stone-800 text-base leading-snug mb-1 line-clamp-2 group-hover:text-amber-700 transition-colors">
          {recipe.title_pl}
        </h3>

        {/* Author (e.g. starter recipes from famous cooks) */}
        {(recipe.author_name || recipe.author_bio) && (
          <p className="text-xs text-stone-500 mb-2 line-clamp-1">
            {recipe.author_name && <span className="font-medium text-stone-600">By {recipe.author_name}</span>}
            {recipe.author_name && recipe.author_bio && ' · '}
            {recipe.author_bio && <span className="italic">{recipe.author_bio}</span>}
          </p>
        )}

        {/* Diet tags (e.g. Kosher) */}
        {recipe.diet_tags?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {recipe.diet_tags.map((key, i) => (
              <span key={`d-${i}`} className="text-xs font-medium rounded-full px-2.5 py-0.5 bg-emerald-100 text-emerald-800">
                {key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
              </span>
            ))}
          </div>
        )}
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
          </div>
          {/* Recipe image: small thumbnail top-right */}
          <div className="shrink-0 w-20 h-20 rounded-xl overflow-hidden bg-stone-100 flex items-center justify-center">
            {imageUrl && !imageError ? (
              <img src={imageUrl} alt="" className="w-full h-full object-cover" onError={() => setImageError(true)} />
            ) : (
              <span className="text-2xl text-stone-300" aria-hidden>🍽</span>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-stone-100 mt-2 space-y-2">
          {/* Quick glance: time + rating */}
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs text-stone-500 flex items-center gap-2">
              {total > 0 && <span title="Total time">⏳ {total} min</span>}
            </div>
            {recipe.user_rating ? (
              <div className="text-xs text-amber-600 font-semibold" title={`Rating: ${recipe.user_rating}/5`}>
                {'★'.repeat(recipe.user_rating)}{'☆'.repeat(5 - recipe.user_rating)}
              </div>
            ) : (
              <div className="text-xs text-stone-300">★★★★★</div>
            )}
          </div>

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
              <>✓ {t('onShoppingList')}</>
            ) : (
              <>+ {t('addToList')}</>
            )}
          </button>

          {/* Favorite + Delete */}
          <div className="flex justify-between items-center">
            <button
              onClick={e => { e.stopPropagation(); onToggleFavorite(recipe) }}
              className={`text-xl transition-all hover:scale-110 ${recipe.is_favorite ? 'text-yellow-400' : 'text-stone-200 hover:text-yellow-300'}`}
              title={recipe.is_favorite ? t('removeFromFavorites') : t('addToFavorites')}
            >
              ★
            </button>
            <button
              onClick={e => { e.stopPropagation(); onDelete(recipe) }}
              className="text-stone-300 hover:text-red-400 transition-colors text-sm p-1 rounded-lg hover:bg-red-50"
              title={t('deleteRecipe')}
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
  const { t } = useLanguage()
  return (
    <div className="flex flex-col items-center justify-center py-16 sm:py-24 px-4 text-center">
      <div className="text-6xl sm:text-7xl mb-4 sm:mb-6 select-none">🥘</div>
      <h3 className="text-lg sm:text-xl font-bold text-stone-700 mb-2">
        {t('emptyCookbookTitle')}
      </h3>
      <p className="text-stone-400 max-w-sm mb-6 sm:mb-8 leading-relaxed text-sm sm:text-base">
        {t('emptyCookbookSubtitle')}
      </p>
      <button
        onClick={onAdd}
        className="min-h-[48px] bg-amber-500 hover:bg-amber-600 text-white px-6 py-3 rounded-2xl font-bold hover:shadow-lg hover:shadow-amber-200 transition-all active:scale-95 flex items-center justify-center gap-2"
      >
        <span className="text-lg">+</span>
        {t('addYourFirstRecipe')}
      </button>
    </div>
  )
}

export default function RecipeListPage() {
  const { t } = useLanguage()
  const { user, trialToken } = useAuth()
  const location = useLocation()
  const [recipes, setRecipes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [filter, setFilter] = useState('all')
  const [toast, setToast] = useState(null)
  const [collectionList, setCollectionList] = useState([])
  const [selectedCollection, setSelectedCollection] = useState(null)
  const [newCollectionName, setNewCollectionName] = useState('')
  const [creatingCollection, setCreatingCollection] = useState(false)

  const { addRecipe, removeRecipe, isInList, evictFromList } = useShoppingList()

  const fetchRecipes = useCallback(async (collection = null) => {
    // Call API when logged in or in trial (client sends user token or trial token).
    if (!user && !trialToken) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (collection && collection.trim()) params.set('collection', collection.trim())
      const path = params.toString() ? `/recipes/?${params.toString()}` : '/recipes/'
      const data = await api.get(path)
      setRecipes(data)
    } catch (e) {
      console.error(e)
      // Fallback for trial: use state/sessionStorage if API fails (e.g. first paint before token)
      if (!user && trialToken) {
        const state = location.state
        let raw = state?.trialRecipes
        if (!raw?.length) {
          try {
            const stored = localStorage.getItem('trial_recipes')
            raw = stored ? JSON.parse(stored) : null
          } catch (_) {}
        }
        if (raw?.length) {
          const mapped = raw.map((r) => ({
            id: r.id ?? -(r.title?.length ?? 0),
            title_pl: r.title,
            title_original: r.title,
            ingredients_pl: r.ingredients ?? [],
            ingredients_original: r.ingredients ?? [],
            steps_pl: r.steps ?? [],
            tags: r.tags ?? [],
            substitutions: r.substitutions ?? {},
            notes: r.notes ?? {},
            user_notes: r.user_notes ?? null,
            is_favorite: r.is_favorite ?? false,
            raw_input: r.raw_input ?? '',
            detected_language: r.detected_language ?? null,
            target_language: r.target_language ?? '',
            target_country: r.target_country ?? '',
            target_city: r.target_city ?? '',
            created_at: r.created_at ?? new Date().toISOString(),
            author_name: r.author_name ?? null,
            author_bio: r.author_bio ?? null,
            author_image_url: r.author_image_url ?? null,
            prep_time_minutes: r.prep_time_minutes ?? null,
            cook_time_minutes: r.cook_time_minutes ?? null,
            user_rating: r.user_rating ?? null,
            diet_tags: r.diet_tags ?? [],
            image_url: r.image_url ?? null,
            collections: r.collections ?? [],
          }))
          setRecipes(mapped)
        }
      }
    } finally {
      setLoading(false)
    }
  }, [user, trialToken, location.state])

  useEffect(() => {
    if (user || trialToken) {
      api.get('/recipes/collections').then(data => setCollectionList(data.collections || [])).catch(() => setCollectionList([]))
    } else {
      setCollectionList([])
    }
  }, [user, trialToken])

  useEffect(() => {
    if (!user && !trialToken) {
      setLoading(false)
      const state = location.state
      let raw = state?.trialRecipes
      if (!raw?.length) {
        try {
          const stored = localStorage.getItem('trial_recipes')
          raw = stored ? JSON.parse(stored) : null
        } catch (_) {}
      }
      if (raw?.length) {
        const mapped = raw.map((r) => ({
          id: r.id ?? -(r.title?.length ?? 0),
          title_pl: r.title,
          title_original: r.title,
          ingredients_pl: r.ingredients ?? [],
          ingredients_original: r.ingredients ?? [],
          steps_pl: r.steps ?? [],
          tags: r.tags ?? [],
          substitutions: r.substitutions ?? {},
          notes: r.notes ?? {},
          user_notes: r.user_notes ?? null,
          is_favorite: r.is_favorite ?? false,
          raw_input: r.raw_input ?? '',
          detected_language: r.detected_language ?? null,
          target_language: r.target_language ?? '',
          target_country: r.target_country ?? '',
          target_city: r.target_city ?? '',
          created_at: r.created_at ?? new Date().toISOString(),
          author_name: r.author_name ?? null,
          author_bio: r.author_bio ?? null,
          author_image_url: r.author_image_url ?? null,
          prep_time_minutes: r.prep_time_minutes ?? null,
          cook_time_minutes: r.cook_time_minutes ?? null,
          user_rating: r.user_rating ?? null,
          diet_tags: r.diet_tags ?? [],
          image_url: r.image_url ?? null,
          collections: r.collections ?? [],
        }))
        setRecipes(mapped)
      } else {
        setRecipes([])
      }
      return
    }
    fetchRecipes(selectedCollection)
  }, [fetchRecipes, selectedCollection, user, trialToken, location.state])

  async function handleCreateCollection(e) {
    e.preventDefault()
    const name = (newCollectionName || '').trim()
    if (!name || !user) return
    setCreatingCollection(true)
    try {
      const data = await api.post('/recipes/collections', { name })
      setCollectionList(data.collections || [])
      setNewCollectionName('')
      setSelectedCollection(name)
      fetchRecipes(name)
      showToast(t('collectionCreated'))
    } catch (err) {
      showToast(err.message || t('collectionCreateError'))
    } finally {
      setCreatingCollection(false)
    }
  }

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
    if (!confirm(`${t('deleteRecipe')} "${recipe.title_pl}"?`)) return
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
      showToast(t('alreadyOnList'))
      return
    }
    addRecipe(id)
  }

  function handleRemoveFromList(id) {
    removeRecipe(id)
  }

  let visible = recipes
  if (selectedCollection) {
    const coll = selectedCollection.trim().toLowerCase()
    visible = visible.filter(r => (r.collections || []).some(c => String(c).trim().toLowerCase() === coll))
  }
  if (filter === 'favorites') visible = visible.filter(r => r.is_favorite)
  const favCount = recipes.filter(r => r.is_favorite).length

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-stone-800 text-white px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg pointer-events-none">
          {toast}
        </div>
      )}

      {/* Filter by collection + Create collection */}
      <div className="mb-4">
        <span className="text-xs font-semibold text-stone-500 mr-2">{t('filterByCollection')}</span>
        <div className="flex flex-wrap gap-2 mt-1.5 items-center">
          <button
            type="button"
            onClick={() => setSelectedCollection(null)}
            className={`min-h-[36px] px-3 py-1.5 rounded-xl text-sm font-medium transition-colors ${
              selectedCollection === null ? 'bg-amber-500 text-white' : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
            }`}
          >
            {t('allRecipes')}
          </button>
          {collectionList.map(c => (
            <span
              key={c}
              className={`inline-flex items-center rounded-xl overflow-hidden border border-transparent focus-within:ring-2 focus-within:ring-amber-400 ${
                selectedCollection === c ? 'bg-amber-500 text-white' : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
              }`}
            >
              <button
                type="button"
                onClick={() => setSelectedCollection(c)}
                className="min-h-[36px] px-3 py-1.5 text-sm font-medium"
              >
                {c}
              </button>
              {user && (
                <button
                  type="button"
                  onClick={() => {
                    if (!window.confirm(t('deleteCollectionConfirm', { name: c }))) return
                    api.post('/recipes/collections/remove', { name: c }).then(() => {
                      setCollectionList(prev => prev.filter(x => x !== c))
                      if (selectedCollection === c) setSelectedCollection(null)
                      fetchRecipes(selectedCollection === c ? null : selectedCollection)
                      showToast(t('collectionDeleted'))
                    }).catch(err => showToast(err.message || t('collectionDeleteError')))
                  }}
                  className={`min-h-[36px] px-2 py-1.5 transition-colors ${
                    selectedCollection === c ? 'text-white/80 hover:bg-white/20' : 'text-stone-400 hover:text-red-600 hover:bg-red-50'
                  }`}
                  aria-label={t('deleteCollection')}
                  title={t('deleteCollection')}
                >
                  🗑
                </button>
              )}
            </span>
          ))}
          {user && (
            <form onSubmit={handleCreateCollection} className="inline-flex gap-2 items-center">
              <input
                type="text"
                value={newCollectionName}
                onChange={e => setNewCollectionName(e.target.value)}
                placeholder={t('newCollectionPlaceholder')}
                className="min-h-[36px] w-36 rounded-xl border border-stone-200 px-3 py-1.5 text-sm text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400 bg-white"
                aria-label={t('createCollection')}
              />
              <button
                type="submit"
                disabled={creatingCollection || !newCollectionName.trim()}
                className="min-h-[36px] px-3 py-1.5 rounded-xl bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creatingCollection ? '…' : t('createCollection')}
              </button>
            </form>
          )}
        </div>
      </div>

      {/* Header: stack on mobile for better touch targets and spacing */}
      <div className="flex flex-col sm:flex-row sm:flex-wrap gap-4 justify-between items-stretch sm:items-start mb-6 sm:mb-8">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-stone-800">{t('myRecipes')}</h2>
          <p className="text-stone-400 text-sm mt-0.5">
            {recipes.length === 0 ? t('noRecipes') : `${recipes.length} ${recipes.length === 1 ? t('recipe') : t('recipesCount')}`}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Filter pills: touch-friendly min height */}
          <div className="flex bg-white border border-stone-200 rounded-xl overflow-hidden shadow-sm text-sm">
            <button
              onClick={() => setFilter('all')}
              className={`min-h-[44px] px-4 py-2.5 font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-amber-500 text-white'
                  : 'text-stone-500 hover:bg-stone-50'
              }`}
            >
              {t('all')}
            </button>
            <button
              onClick={() => setFilter('favorites')}
              className={`min-h-[44px] px-4 py-2.5 font-medium transition-colors flex items-center gap-1.5 ${
                filter === 'favorites'
                  ? 'bg-amber-500 text-white'
                  : 'text-stone-500 hover:bg-stone-50'
              }`}
            >
              <span>★</span>
              <span>{t('favoritesTab')}</span>
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
            className="min-h-[44px] bg-amber-500 hover:bg-amber-600 text-white rounded-xl px-5 py-2.5 text-sm font-bold hover:shadow-lg hover:shadow-amber-200 transition-all active:scale-95 flex items-center justify-center gap-1.5"
          >
            <span className="text-base leading-none">+</span>
            <span>{t('add')}</span>
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
          <p className="text-stone-500 font-medium mb-1">{t('noFavorites')}</p>
          <p className="text-sm text-stone-400">{t('noFavoritesHint')}</p>
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
