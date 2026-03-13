import { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import { api } from '../api/client'

const ShoppingListContext = createContext(null)
const TRIAL_SHOPPING_LIST_KEY = 'trial_shopping_list'

function getTrialListFromStorage() {
  try {
    const raw = localStorage.getItem(TRIAL_SHOPPING_LIST_KEY)
    if (!raw) return new Set()
    const arr = JSON.parse(raw)
    return new Set(Array.isArray(arr) ? arr : [])
  } catch (_) {
    return new Set()
  }
}

function setTrialListToStorage(ids) {
  try {
    localStorage.setItem(TRIAL_SHOPPING_LIST_KEY, JSON.stringify([...ids]))
  } catch (_) {}
}

export function ShoppingListProvider({ children }) {
  const { user, trialToken } = useAuth()
  const [recipeIds, setRecipeIds] = useState(new Set())
  const [isOpen, setIsOpen] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState(null)

  useEffect(() => {
    if (user) {
      api.get('/shopping-list/recipes')
        .then(data => setRecipeIds(new Set(data.recipe_ids)))
        .catch(console.error)
      return
    }
    if (trialToken) {
      setRecipeIds(getTrialListFromStorage())
      return
    }
    setRecipeIds(new Set())
  }, [user, trialToken])

  async function addRecipe(id) {
    if (!user && trialToken) {
      setRecipeIds(prev => {
        const next = new Set(prev)
        next.add(id)
        setTrialListToStorage(next)
        return next
      })
      return
    }
    setActionLoadingId(id)
    try {
      const data = await api.post('/shopping-list/add', { recipe_id: id })
      setRecipeIds(new Set(data.recipe_ids))
    } finally {
      setActionLoadingId(null)
    }
  }

  async function removeRecipe(id) {
    if (!user && trialToken) {
      setRecipeIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        setTrialListToStorage(next)
        return next
      })
      return
    }
    setActionLoadingId(id)
    try {
      const data = await api.delete(`/shopping-list/remove/${id}`)
      setRecipeIds(new Set(data.recipe_ids))
    } finally {
      setActionLoadingId(null)
    }
  }

  async function clearList() {
    if (!user && trialToken) {
      setRecipeIds(new Set())
      setTrialListToStorage(new Set())
      return
    }
    await api.delete('/shopping-list/clear')
    setRecipeIds(new Set())
  }

  function evictFromList(id) {
    setRecipeIds(prev => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }

  return (
    <ShoppingListContext.Provider value={{
      recipeIds,
      isOpen,
      openPanel: () => setIsOpen(true),
      closePanel: () => setIsOpen(false),
      addRecipe,
      removeRecipe,
      clearList,
      isInList: id => recipeIds.has(id),
      actionLoadingId,
      evictFromList,
    }}>
      {children}
    </ShoppingListContext.Provider>
  )
}

export function useShoppingList() {
  return useContext(ShoppingListContext)
}
