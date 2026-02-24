import { useState } from 'react'
import { api } from '../api/client'

export default function AddRecipeModal({ onClose, onCreated }) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!text.trim()) return
    setError('')
    setLoading(true)
    try {
      const recipe = await api.post('/recipes/', { raw_input: text.trim() })
      onCreated(recipe)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50 p-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Dodaj Przepis</h2>
              <p className="text-sm text-gray-500 mt-0.5">Wklej przepis w języku hebrajskim</p>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">
              ×
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <textarea
              dir="rtl"
              value={text}
              onChange={e => setText(e.target.value)}
              rows={10}
              placeholder="הדביק את המתכון כאן..."
              className="w-full border border-gray-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none leading-relaxed"
              autoFocus
              required
            />

            {error && (
              <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mt-2">{error}</p>
            )}

            <div className="flex gap-3 mt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 border border-gray-200 text-gray-700 rounded-xl py-2.5 text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                Anuluj
              </button>
              <button
                type="submit"
                disabled={loading || !text.trim()}
                className="flex-1 bg-indigo-600 text-white rounded-xl py-2.5 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Przetwarzanie…' : 'Przetłumacz →'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
