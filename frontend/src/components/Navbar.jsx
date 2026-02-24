import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="font-bold text-gray-900 hover:text-indigo-600 transition-colors">
          Recipe Translator{' '}
          <span className="font-normal text-gray-400 text-sm">עברית → Polski</span>
        </Link>
        <div className="flex items-center gap-5">
          <span className="text-sm text-gray-400 hidden sm:block truncate max-w-[180px]">
            {user?.email}
          </span>
          <Link
            to="/settings"
            className="text-sm text-gray-600 hover:text-indigo-600 transition-colors"
          >
            Ustawienia
          </Link>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-600 hover:text-red-500 transition-colors"
          >
            Wyloguj
          </button>
        </div>
      </div>
    </nav>
  )
}
