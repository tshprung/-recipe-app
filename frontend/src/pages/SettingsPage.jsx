import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

function Field({ label, hint, value, onChange }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {hint && <span className="ml-1 text-xs font-normal text-gray-400">({hint})</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
    </div>
  )
}

export default function SettingsPage() {
  const { user, setUser } = useAuth()
  const [form, setForm] = useState({
    source_language: user?.source_language ?? 'he',
    source_country:  user?.source_country  ?? 'IL',
    target_language: user?.target_language ?? 'pl',
    target_country:  user?.target_country  ?? 'PL',
    target_city:     user?.target_city     ?? 'Wrocław',
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)
  const [error, setError]   = useState('')

  function set(key) {
    return v => setForm(f => ({ ...f, [key]: v }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const updated = await api.patch('/users/me/settings', form)
      setUser(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-md">
      <h2 className="text-xl font-bold text-gray-900 mb-6">Ustawienia</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Source */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            Język źródłowy
          </h3>
          <Field label="Język" hint="np. he" value={form.source_language} onChange={set('source_language')} />
          <Field label="Kraj" hint="np. IL" value={form.source_country}  onChange={set('source_country')}  />
        </div>

        {/* Target */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
            Język docelowy
          </h3>
          <Field label="Język" hint="np. pl" value={form.target_language} onChange={set('target_language')} />
          <Field label="Kraj"  hint="np. PL" value={form.target_country}  onChange={set('target_country')}  />
          <Field label="Miasto" hint="np. Wrocław" value={form.target_city} onChange={set('target_city')} />
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2">{error}</p>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="bg-indigo-600 text-white rounded-xl px-6 py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Zapisywanie…' : 'Zapisz ustawienia'}
          </button>
          {saved && <span className="text-sm text-green-600">Zapisano ✓</span>}
        </div>
      </form>

      <div className="mt-8 pt-6 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          Konto: <span className="text-gray-600">{user?.email}</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Zarejestrowano: {user?.created_at ? new Date(user.created_at).toLocaleDateString('pl-PL') : '—'}
        </p>
      </div>
    </div>
  )
}
