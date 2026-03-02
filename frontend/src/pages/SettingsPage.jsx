import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
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
  const { user, setUser, logout } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    target_language: user?.target_language ?? 'pl',
    target_country:  user?.target_country  ?? 'PL',
    target_city:     user?.target_city     ?? 'Wrocław',
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)
  const [error, setError]   = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

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
        <h2 className="text-2xl font-bold text-stone-800">{t('settings')}</h2>
        <p className="text-stone-400 text-sm mt-1">{t('translationAndLocation')}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <SettingsCard icon="🌐" title={t('translateTo')}>
          <Field label={t('language')} hint={t('hintLanguage')} value={form.target_language} onChange={set('target_language')} />
          <Field label={t('country')}  hint={t('hintCountry')} value={form.target_country}  onChange={set('target_country')}  />
          <Field label={t('city')}     hint={t('hintCity')} value={form.target_city}     onChange={set('target_city')}     />
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
                {t('saving')}
              </span>
            ) : t('saveSettings')}
          </button>
          {saved && (
            <span className="text-sm text-emerald-600 font-semibold flex items-center gap-1">
              ✓ {t('saved')}
            </span>
          )}
        </div>
      </form>

      {/* Account info */}
      <div className="mt-8 bg-white rounded-2xl border border-stone-100 shadow-sm p-5">
        <h3 className="text-xs font-bold text-stone-400 uppercase tracking-widest mb-3">{t('account')}</h3>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-bold">
              {user?.email?.[0]?.toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-semibold text-stone-700">{user?.email}</p>
              <p className="text-xs text-stone-400">
                {t('joined')}: {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'}
              </p>
              <p className="text-xs text-stone-400 mt-1">
                {user?.is_verified ? t('verified') : t('unverified')}
              </p>
            </div>
          </div>
          {!user?.is_verified && (
            <button
              type="button"
              onClick={async () => {
                try {
                  await api.post('/auth/resend-verification')
                  alert(t('resendVerification'))
                } catch (err) {
                  alert(err.message || t('verifyError'))
                }
              }}
              className="text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-xl px-3 py-2 transition-colors"
            >
              {t('resendVerification')}
            </button>
          )}
        </div>
      </div>

      {/* Delete account */}
      <div className="mt-8 bg-white rounded-2xl border border-red-100 shadow-sm p-5">
        <h3 className="text-xs font-bold text-red-500 uppercase tracking-widest mb-3">{t('deleteAccount')}</h3>
        <p className="text-sm text-stone-600 mb-3">
          {t('deleteAccountConfirm')}
        </p>
        <div className="space-y-3">
          <p className="text-sm text-stone-600">
            {t('typeDelete')}
          </p>
          <input
            type="text"
            value={deleteConfirm}
            onChange={e => setDeleteConfirm(e.target.value)}
            placeholder="DELETE"
            className="w-full border border-stone-200 rounded-xl px-4 py-2.5 text-sm bg-stone-50 text-stone-800 focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent"
          />
          {deleteError && (
            <p className="text-sm text-red-600">{deleteError}</p>
          )}
          <button
            type="button"
            disabled={deleteConfirm !== 'DELETE' || deleting}
            onClick={async () => {
              if (deleteConfirm !== 'DELETE') return
              setDeleting(true)
              setDeleteError('')
              try {
                await api.delete('/users/me')
                logout()
                navigate('/', { replace: true })
              } catch (err) {
                setDeleteError(err.message || t('verifyError'))
              } finally {
                setDeleting(false)
              }
            }}
            className="bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-6 py-2.5 text-sm font-bold transition-all hover:shadow-lg hover:shadow-red-200 active:scale-95"
          >
            {deleting ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                {t('deleting')}
              </span>
            ) : t('deleteAccountButton')}
          </button>
        </div>
      </div>
    </div>
  )
}
