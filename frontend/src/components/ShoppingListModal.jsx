import { useState } from 'react'

export default function ShoppingListModal({ ingredients, title, onClose }) {
  const [checked, setChecked] = useState(new Set())

  function toggle(i) {
    setChecked(prev => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })
  }

  const items = (ingredients || []).map(ing =>
    typeof ing === 'object' ? `${ing.amount ?? ''} ${ing.name ?? ''}`.trim() : ing
  )

  const doneCount = checked.size
  const progress = items.length > 0 ? Math.round((doneCount / items.length) * 100) : 0

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-end sm:items-center justify-center z-50 p-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-3xl shadow-2xl shadow-stone-200 w-full max-w-md">
        {/* Header */}
        <div className="p-6 pb-4">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center text-xl shadow-sm">
                🛒
              </div>
              <h2 className="text-lg font-bold text-stone-800">Lista zakupów</h2>
            </div>
            <button
              onClick={onClose}
              className="text-stone-400 hover:text-stone-600 w-8 h-8 flex items-center justify-center rounded-xl hover:bg-stone-100 transition-colors text-xl leading-none"
            >
              ×
            </button>
          </div>
          <p className="text-sm text-stone-400 truncate pl-[52px]">{title}</p>
        </div>

        {/* Progress bar */}
        {items.length > 0 && (
          <div className="px-6 mb-4">
            <div className="flex justify-between text-xs text-stone-400 mb-1.5">
              <span>{doneCount} z {items.length} składników</span>
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

        {/* Items */}
        <div className="px-6 pb-2">
          {items.length === 0 ? (
            <div className="text-center py-10">
              <div className="text-4xl mb-3">🧺</div>
              <p className="text-sm text-stone-400">Brak składników do wyświetlenia</p>
            </div>
          ) : (
            <ul className="space-y-1 max-h-72 overflow-y-auto -mx-2 px-2">
              {items.map((label, i) => (
                <li
                  key={i}
                  onClick={() => toggle(i)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-stone-50 cursor-pointer select-none transition-colors group"
                >
                  <span className={`w-5 h-5 rounded-lg border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                    checked.has(i)
                      ? 'bg-amber-500 border-amber-500'
                      : 'border-stone-300 group-hover:border-amber-400'
                  }`}>
                    {checked.has(i) && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </span>
                  <span className={`text-sm transition-colors ${
                    checked.has(i) ? 'line-through text-stone-300' : 'text-stone-700'
                  }`}>
                    {label}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 pt-4">
          <button
            onClick={onClose}
            className="w-full border-2 border-stone-200 hover:border-amber-300 text-stone-600 hover:text-amber-700 hover:bg-amber-50 rounded-xl py-2.5 text-sm font-semibold transition-all"
          >
            Zamknij
          </button>
        </div>
      </div>
    </div>
  )
}
