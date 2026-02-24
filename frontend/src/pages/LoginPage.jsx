import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const [tab, setTab] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      tab === 'login' ? await login(email, password) : await register(email, password)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Decorative blobs */}
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-amber-200/40 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-orange-200/40 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/4 w-64 h-64 bg-rose-200/20 rounded-full blur-3xl pointer-events-none" />

      <div className="relative bg-white rounded-3xl shadow-2xl shadow-orange-100 w-full max-w-md p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl shadow-lg shadow-orange-200 text-3xl mb-4">
            🍳
          </div>
          <h1 className="text-2xl font-bold text-stone-800">Recipe Translator</h1>
          <p className="text-stone-400 text-sm mt-1">Tłumaczymy przepisy z hebrajskiego na polski</p>
        </div>

        {/* Tab switcher */}
        <div className="flex bg-stone-100 rounded-2xl p-1 mb-6">
          {['login', 'register'].map(t => (
            <button
              key={t}
              onClick={() => { setTab(t); setError('') }}
              className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition-all ${
                tab === t
                  ? 'bg-white text-stone-800 shadow-sm'
                  : 'text-stone-400 hover:text-stone-600'
              }`}
            >
              {t === 'login' ? 'Logowanie' : 'Rejestracja'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="you@example.com"
              className="w-full border border-stone-200 rounded-xl px-4 py-3 text-sm bg-stone-50 text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-stone-600 mb-1.5">Hasło</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              className="w-full border border-stone-200 rounded-xl px-4 py-3 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
              <span className="flex-shrink-0">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-amber-500 hover:bg-amber-600 active:scale-[0.98] text-white rounded-xl py-3 text-sm font-bold disabled:opacity-50 transition-all hover:shadow-lg hover:shadow-amber-200 mt-2"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Ładowanie…
              </span>
            ) : tab === 'login' ? 'Zaloguj się →' : 'Utwórz konto →'}
          </button>
        </form>
      </div>
    </div>
  )
}
