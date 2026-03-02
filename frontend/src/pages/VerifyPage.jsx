import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function VerifyPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState('pending') // 'pending' | 'success' | 'error'
  const [message, setMessage] = useState('')
  const navigate = useNavigate()
  const { user, setUser } = useAuth()

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Brak tokenu weryfikacyjnego.')
      return
    }

    async function run() {
      try {
        await api.post(`/auth/verify?token=${encodeURIComponent(token)}`)
        setStatus('success')
        setMessage('Twój adres email został zweryfikowany. Możesz korzystać z aplikacji.')

        // If user is logged in, refresh their data so is_verified and quota update
        if (user) {
          try {
            const me = await api.get('/users/me')
            setUser(me)
          } catch {
            // ignore refresh errors
          }
        }
      } catch (err) {
        setStatus('error')
        setMessage(err.message || 'Nie udało się zweryfikować adresu email.')
      }
    }

    run()
  }, [token, user, setUser])

  const isSuccess = status === 'success'
  const isError = status === 'error'

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl shadow-orange-100 w-full max-w-md p-8 text-center">
        <div className="mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-emerald-400 to-amber-500 rounded-2xl shadow-lg text-3xl mb-4">
            {status === 'pending' ? '⏳' : isSuccess ? '✅' : '⚠️'}
          </div>
          <h1 className="text-2xl font-bold text-stone-800 mb-1">Weryfikacja email</h1>
          <p className="text-sm text-stone-500">
            {status === 'pending'
              ? 'Sprawdzamy Twój token weryfikacyjny…'
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
            Przejdź do aplikacji
          </button>
        )}

        {isError && (
          <button
            type="button"
            onClick={() => navigate('/')}
            className="mt-6 w-full bg-stone-800 hover:bg-stone-900 text-white rounded-xl py-3 text-sm font-bold transition-colors"
          >
            Wróć do strony głównej
          </button>
        )}
      </div>
    </div>
  )
}

