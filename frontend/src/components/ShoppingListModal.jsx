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

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50 p-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
        <div className="p-6">
          <div className="flex justify-between items-center mb-1">
            <h2 className="text-lg font-bold text-gray-900">Lista zakupów</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
          </div>
          <p className="text-sm text-gray-500 mb-4 truncate">{title}</p>

          {items.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">Brak składników do wyświetlenia</p>
          ) : (
            <>
              <ul className="space-y-1 max-h-80 overflow-y-auto -mx-2 px-2">
                {items.map((label, i) => (
                  <li
                    key={i}
                    onClick={() => toggle(i)}
                    className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-gray-50 cursor-pointer select-none"
                  >
                    <span className={`w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                      checked.has(i) ? 'bg-indigo-600 border-indigo-600' : 'border-gray-300'
                    }`}>
                      {checked.has(i) && <span className="text-white text-xs font-bold">✓</span>}
                    </span>
                    <span className={`text-sm transition-colors ${checked.has(i) ? 'line-through text-gray-400' : 'text-gray-700'}`}>
                      {label}
                    </span>
                  </li>
                ))}
              </ul>
              {checked.size > 0 && (
                <p className="text-xs text-gray-400 text-center mt-3">
                  {checked.size} z {items.length} zaznaczonych
                </p>
              )}
            </>
          )}

          <button
            onClick={onClose}
            className="w-full mt-4 border border-gray-200 text-gray-700 rounded-xl py-2.5 text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            Zamknij
          </button>
        </div>
      </div>
    </div>
  )
}
