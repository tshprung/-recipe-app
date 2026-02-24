import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

function Field({ label, hint, value, onChange }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-stone-600 mb-1.5">
        {label}
        {hint && <span className="ml-1.5 text-xs font-normal text-stone-400">({hint})</span>}
      </label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent focus:bg-white transition-colors"
      />
    </div>
  )
}

function SettingsCard({ icon, title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-stone-100 shadow-sm overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-stone-100 bg-stone-50">
        <span className="text-xl">{icon}</span>
        <h3 className="text-sm font-bold text-stone-600 uppercase tracking-widest">{title}</h3>
      </div>
      <div className="p-5 space-y-4">
        {children}
      </div>
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

  const set = key => v => setForm(f => ({ ...f, [key]: v }))

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
    <div className="max-w-lg">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-stone-800">Ustawienia</h2>
        <p className="text-stone-400 text-sm mt-1">Konfiguracja tłumaczenia i lokalizacji</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <SettingsCard icon="🇮🇱" title="Język źródłowy">
          <Field label="Język" hint="np. he" value={form.source_language} onChange={set('source_language')} />
          <Field label="Kraj"  hint="np. IL" value={form.source_country}  onChange={set('source_country')}  />
        </SettingsCard>

        <SettingsCard icon="🇵🇱" title="Język docelowy">
          <Field label="Język"  hint="np. pl"      value={form.target_language} onChange={set('target_language')} />
          <Field label="Kraj"   hint="np. PL"      value={form.target_country}  onChange={set('target_country')}  />
          <Field label="Miasto" hint="np. Wrocław" value={form.target_city}     onChange={set('target_city')}     />
        </SettingsCard>

        {error && (
          <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
            <span>⚠️</span> {error}
          </div>
        )}

        <div className="flex items-center gap-4 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="bg-amber-500 hover:bg-amber-600 text-white rounded-xl px-6 py-2.5 text-sm font-bold disabled:opacity-50 transition-all hover:shadow-lg hover:shadow-amber-200 active:scale-95"
          >
            {saving ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Zapisywanie…
              </span>
            ) : 'Zapisz ustawienia'}
          </button>
          {saved && (
            <span className="text-sm text-emerald-600 font-semibold flex items-center gap-1">
              ✓ Zapisano
            </span>
          )}
        </div>
      </form>

      {/* Account info */}
      <div className="mt-8 bg-white rounded-2xl border border-stone-100 shadow-sm p-5">
        <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest mb-3">Konto</h3>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-bold">
            {user?.email?.[0]?.toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-semibold text-stone-700">{user?.email}</p>
            <p className="text-xs text-stone-400">
              Zarejestrowano: {user?.created_at ? new Date(user.created_at).toLocaleDateString('pl-PL', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
