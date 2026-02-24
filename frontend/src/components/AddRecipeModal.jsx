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
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-end sm:items-center justify-center z-50 p-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-3xl shadow-2xl shadow-stone-200 w-full max-w-lg">
        {/* Header */}
        <div className="flex items-start justify-between p-6 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center text-xl shadow-sm">
              📋
            </div>
            <div>
              <h2 className="text-lg font-bold text-stone-800">Dodaj przepis</h2>
              <p className="text-sm text-stone-400">Wklej tekst po hebrajsku</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-stone-400 hover:text-stone-600 w-8 h-8 flex items-center justify-center rounded-xl hover:bg-stone-100 transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 pb-6">
          <textarea
            dir="rtl"
            value={text}
            onChange={e => setText(e.target.value)}
            rows={10}
            placeholder="הדביק את המתכון כאן..."
            className="w-full border border-stone-200 rounded-2xl px-4 py-3 text-sm bg-stone-50 text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white resize-none leading-relaxed transition-colors"
            autoFocus
            required
          />

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mt-3">
              <span>⚠️</span> {error}
            </div>
          )}

          {loading && (
            <div className="flex items-center gap-3 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 mt-3">
              <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              <p className="text-sm text-amber-700 font-medium">Tłumaczenie przez AI… może potrwać kilka sekund.</p>
            </div>
          )}

          <div className="flex gap-3 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-stone-200 text-stone-600 rounded-xl py-3 text-sm font-semibold hover:bg-stone-50 transition-colors"
            >
              Anuluj
            </button>
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="flex-1 bg-amber-500 hover:bg-amber-600 text-white rounded-xl py-3 text-sm font-bold disabled:opacity-50 transition-all hover:shadow-lg hover:shadow-amber-200 active:scale-[0.98]"
            >
              {loading ? 'Tłumaczenie…' : 'Przetłumacz →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
