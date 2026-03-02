import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

export default function VerifyPage() {
  const { t } = useLanguage()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState('pending') // 'pending' | 'success' | 'error'
  const [message, setMessage] = useState('')
  const navigate = useNavigate()
  const { user, setUser } = useAuth()
  const hasRun = useRef(false)

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage(t('missingToken'))
      return
    }
    // Prevent double execution (e.g. from setUser triggering re-run or Strict Mode)
    if (hasRun.current) return
    hasRun.current = true

    async function run() {
      try {
        await api.post(`/auth/verify?token=${encodeURIComponent(token)}`)
        setStatus('success')
        setMessage(t('verifySuccess'))

        // If user is logged in, refresh their data so is_verified and quota update
        try {
          const me = await api.get('/users/me')
          setUser(me)
        } catch {
          // ignore refresh errors (e.g. not logged in)
        }
      } catch (err) {
        setStatus('error')
        setMessage(err.message || t('verifyError'))
      }
    }

    run()
  }, [token, setUser, t])

  const isSuccess = status === 'success'
  const isError = status === 'error'

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl shadow-orange-100 w-full max-w-md p-8 text-center">
        <div className="mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-emerald-400 to-amber-500 rounded-2xl shadow-lg text-3xl mb-4">
            {status === 'pending' ? '⏳' : isSuccess ? '✅' : '⚠️'}
          </div>
          <h1 className="text-2xl font-bold text-stone-800 mb-1">{t('emailVerification')}</h1>
          <p className="text-sm text-stone-500">
            {status === 'pending'
              ? t('checkingToken')
              : message}
          </p>
        </div>

        {status === 'pending' && (
          <div className="flex items-center justify-center mt-4">
            <div className="w-8 h-8 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {isSuccess && (
          <button
            type="button"
            onClick={() => navigate(user ? '/' : '/')}
            className="mt-6 w-full bg-amber-500 hover:bg-amber-600 text-white rounded-xl py-3 text-sm font-bold transition-colors"
          >
            {t('goToApp')}
          </button>
        )}

        {isError && (
          <button
            type="button"
            onClick={() => navigate('/')}
            className="mt-6 w-full bg-stone-800 hover:bg-stone-900 text-white rounded-xl py-3 text-sm font-bold transition-colors"
          >
            {t('backToHome')}
          </button>
        )}
      </div>
    </div>
  )
}

