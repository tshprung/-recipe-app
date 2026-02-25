import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { useShoppingList } from '../context/ShoppingListContext'

const CATEGORIES = ['Warzywa i owoce', 'Nabiał', 'Mięso i ryby', 'Przyprawy i sosy', 'Inne']

const CATEGORY_ICONS = {
  'Warzywa i owoce': '🥦',
  'Nabiał': '🧀',
  'Mięso i ryby': '🥩',
  'Przyprawy i sosy': '🫙',
  'Inne': '🛒',
}

export default function ShoppingListPanel() {
  const { isOpen, closePanel, recipeIds } = useShoppingList()

  const [items, setItems] = useState(null)      // null = not yet loaded
  const [itemsLoading, setItemsLoading] = useState(false)
  const [checked, setChecked] = useState(new Set())
  const [emailStatus, setEmailStatus] = useState(null) // null | 'loading' | 'sent' | 'error'
  const [emailError, setEmailError] = useState('')

  // Reload items whenever the panel opens or the recipe set changes (while open)
  useEffect(() => {
    if (!isOpen) return
    setItemsLoading(true)
    setChecked(new Set())
    api.get('/shopping-list/')
      .then(data => setItems(data.items))
      .catch(console.error)
      .finally(() => setItemsLoading(false))
  }, [isOpen, recipeIds.size])

  function toggle(key) {
    setChecked(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  async function handlePrint() {
    window.print()
  }

  async function handleEmail() {
    setEmailStatus('loading')
    setEmailError('')
    try {
      await api.post('/shopping-list/email', {})
      setEmailStatus('sent')
      setTimeout(() => setEmailStatus(null), 3000)
    } catch (e) {
      setEmailError(e.message || 'Błąd wysyłki')
      setEmailStatus('error')
      setTimeout(() => setEmailStatus(null), 4000)
    }
  }

  const allKeys = CATEGORIES.flatMap(cat =>
    (items?.[cat] ?? []).map((_, i) => `${cat}::${i}`)
  )
  const totalCount = allKeys.length
  const doneCount = checked.size
  const progress = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0
  const isEmpty = recipeIds.size === 0

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40 print:hidden"
        onClick={closePanel}
      />

      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-full max-w-sm bg-white shadow-2xl z-50 flex flex-col print:shadow-none print:static print:max-w-none print:h-auto">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-stone-100 flex-shrink-0 print:hidden">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center text-lg shadow-sm">
              🛒
            </div>
            <div>
              <h2 className="font-bold text-stone-800 text-base">Lista zakupów</h2>
              {recipeIds.size > 0 && (
                <p className="text-xs text-stone-400 mt-0.5">
                  {recipeIds.size} {recipeIds.size === 1 ? 'przepis' : 'przepisów'}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={closePanel}
            className="text-stone-400 hover:text-stone-600 w-8 h-8 flex items-center justify-center rounded-xl hover:bg-stone-100 transition-colors text-xl"
          >
            ×
          </button>
        </div>

        {/* Print header (only visible when printing) */}
        <div className="hidden print:block px-6 pt-6 pb-4 border-b border-stone-200">
          <h1 className="text-2xl font-bold text-stone-800">Lista zakupów</h1>
        </div>

        {/* Progress bar */}
        {!isEmpty && !itemsLoading && totalCount > 0 && (
          <div className="px-6 pt-4 pb-2 flex-shrink-0 print:hidden">
            <div className="flex justify-between text-xs text-stone-400 mb-1.5">
              <span>{doneCount} z {totalCount}</span>
              <span className="font-medium text-amber-600">{progress}%</span>
            </div>
            <div className="h-1.5 bg-stone-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-amber-400 to-orange-400 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-16">
              <div className="text-6xl mb-4">🧺</div>
              <p className="font-semibold text-stone-600 mb-1">Lista jest pusta</p>
              <p className="text-sm text-stone-400">Dodaj przepisy, aby zobaczyć składniki</p>
            </div>
          ) : itemsLoading ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <div className="w-8 h-8 border-3 border-amber-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-stone-400">Łączę składniki…</p>
            </div>
          ) : (
            <div className="space-y-5">
              {CATEGORIES.map(cat => {
                const catItems = items?.[cat] ?? []
                if (catItems.length === 0) return null
                return (
                  <div key={cat}>
                    <div className="flex items-center gap-2 mb-2.5">
                      <span className="text-base">{CATEGORY_ICONS[cat]}</span>
                      <span className="text-xs font-bold text-stone-400 uppercase tracking-widest">{cat}</span>
                    </div>
                    <ul className="space-y-0.5">
                      {catItems.map((label, i) => {
                        const key = `${cat}::${i}`
                        const isChecked = checked.has(key)
                        return (
                          <li
                            key={key}
                            onClick={() => toggle(key)}
                            className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-stone-50 cursor-pointer select-none transition-colors group print:hover:bg-transparent print:cursor-default"
                          >
                            <span className={`w-5 h-5 rounded-lg border-2 flex-shrink-0 flex items-center justify-center transition-all print:hidden ${
                              isChecked
                                ? 'bg-amber-500 border-amber-500'
                                : 'border-stone-300 group-hover:border-amber-400'
                            }`}>
                              {isChecked && (
                                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </span>
                            <span className={`text-sm transition-colors print:text-stone-800 ${
                              isChecked ? 'line-through text-stone-300' : 'text-stone-700'
                            }`}>
                              {label}
                            </span>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        {!isEmpty && (
          <div className="border-t border-stone-100 px-6 py-4 flex flex-col gap-2 flex-shrink-0 print:hidden">
            {emailStatus === 'error' && (
              <p className="text-xs text-red-500 text-center">{emailError}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={handlePrint}
                disabled={itemsLoading}
                className="flex-1 flex items-center justify-center gap-2 border-2 border-stone-200 hover:border-amber-300 text-stone-600 hover:text-amber-700 hover:bg-amber-50 rounded-xl py-2.5 text-sm font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {itemsLoading ? (
                  <span className="w-4 h-4 border-2 border-stone-400 border-t-transparent rounded-full animate-spin" />
                ) : (
                  '🖨 Drukuj'
                )}
              </button>
              <button
                onClick={handleEmail}
                disabled={itemsLoading || emailStatus === 'loading'}
                className="flex-1 flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white rounded-xl py-2.5 text-sm font-bold transition-all active:scale-95 disabled:cursor-not-allowed"
              >
                {itemsLoading || emailStatus === 'loading' ? (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : emailStatus === 'sent' ? (
                  '✓ Wysłano!'
                ) : (
                  <>✉ Wyślij na email</>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
