import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useShoppingList } from '../context/ShoppingListContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { recipeIds, openPanel } = useShoppingList()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  const initials = user?.email?.[0]?.toUpperCase() ?? '?'
  const isSettings = location.pathname === '/settings'
  const listCount = recipeIds.size

  return (
    <nav className="bg-white border-b border-stone-200 shadow-sm sticky top-0 z-10 print:hidden">
      <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center shadow-sm text-xl">
            🍳
          </div>
          <div className="leading-none">
            <div className="font-bold text-stone-800 group-hover:text-amber-600 transition-colors text-[15px]">
              Recipe Translator
            </div>
            <div className="text-[11px] text-stone-400 mt-0.5">עברית → Polski</div>
          </div>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-1">
          {/* Shopping list button */}
          <button
            onClick={openPanel}
            className="relative p-2 rounded-xl text-stone-500 hover:bg-amber-50 hover:text-amber-600 transition-colors"
            title="Lista zakupów"
          >
            <span className="text-xl">🛒</span>
            {listCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-amber-500 text-white rounded-full text-[10px] flex items-center justify-center font-bold px-1">
                {listCount}
              </span>
            )}
          </button>

          <div className="w-px h-5 bg-stone-200 mx-1" />

          <Link
            to="/settings"
            className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
              isSettings
                ? 'bg-amber-50 text-amber-700'
                : 'text-stone-500 hover:bg-stone-100 hover:text-stone-700'
            }`}
          >
            Ustawienia
          </Link>

          <div className="w-px h-5 bg-stone-200 mx-1" />

          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white text-sm font-bold shadow-sm flex-shrink-0">
              {initials}
            </div>
            <span className="text-sm text-stone-500 hidden md:block max-w-[160px] truncate">
              {user?.email}
            </span>
          </div>

          <button
            onClick={handleLogout}
            className="ml-1 px-3 py-2 rounded-xl text-sm font-medium text-stone-500 hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            Wyloguj
          </button>
        </div>
      </div>
    </nav>
  )
}
