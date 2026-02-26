import { createContext, useContext, useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import { api } from '../api/client'

const ShoppingListContext = createContext(null)

export function ShoppingListProvider({ children }) {
  const { user } = useAuth()
  const [recipeIds, setRecipeIds] = useState(new Set())
  const [isOpen, setIsOpen] = useState(false)
  const [actionLoadingId, setActionLoadingId] = useState(null)

  useEffect(() => {
    if (!user) {
      setRecipeIds(new Set())
      return
    }
    api.get('/shopping-list/recipes')
      .then(data => setRecipeIds(new Set(data.recipe_ids)))
      .catch(console.error)
  }, [user])

  async function addRecipe(id) {
    setActionLoadingId(id)
    try {
      const data = await api.post('/shopping-list/add', { recipe_id: id })
      setRecipeIds(new Set(data.recipe_ids))
    } finally {
      setActionLoadingId(null)
    }
  }

  async function removeRecipe(id) {
    setActionLoadingId(id)
    try {
      const data = await api.delete(`/shopping-list/remove/${id}`)
      setRecipeIds(new Set(data.recipe_ids))
    } finally {
      setActionLoadingId(null)
    }
  }

  async function clearList() {
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
