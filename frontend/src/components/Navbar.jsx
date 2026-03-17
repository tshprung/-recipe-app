import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { useShoppingList } from '../context/ShoppingListContext'

export default function Navbar() {
  const { user, logout, trialToken, trialRemainingActions, leaveTrial } = useAuth()
  const { t, setLang } = useLanguage()
  const navigate = useNavigate()
  const location = useLocation()
  const { recipeIds, openPanel } = useShoppingList()

  function handleLogout() {
    logout()
    setLang('en')
    navigate('/', { replace: true })
  }

  const initials = user?.email?.[0]?.toUpperCase() ?? '?'
  const isSettings = location.pathname === '/settings'
  const listCount = recipeIds.size
  const isTrial = !user && trialToken

  const used = user?.transformations_used ?? 0
  const limit = user?.transformations_limit
  const remaining = limit === -1 ? null : Math.max(0, (limit ?? 0) - used)
  const quotaLabel =
    limit === -1
      ? t('creditsUnlimited')
      : t('creditsRemaining', { count: remaining })
  const trialQuotaLabel = t('creditsRemaining', { count: trialRemainingActions ?? 0 })

  const [menuOpen, setMenuOpen] = useState(false)

  function handleSignOut() {
    if (user) {
      handleLogout()
    } else if (isTrial) {
      leaveTrial()
      setLang('en')
      navigate('/', { replace: true })
    }
  }

  return (
    <nav className="bg-black/70 backdrop-blur border-b border-white/10 shadow-sm sticky top-0 z-10 print:hidden pt-[env(safe-area-inset-top)] text-stone-50">
      <div className="max-w-5xl mx-auto px-3 sm:px-4 min-h-[56px] sm:h-16 flex items-center justify-between gap-2">

        {/* Logo */}
        <div className="flex items-center gap-2 sm:gap-4 min-w-0 flex-shrink">
        <Link to="/" className="flex items-center gap-2 sm:gap-3 group min-w-0 flex-shrink">
          <div className="w-9 h-9 flex-shrink-0 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl flex items-center justify-center shadow-sm text-xl">
            🍳
          </div>
          <div className="leading-none min-w-0">
            <div className="font-bold text-stone-50 group-hover:text-amber-300 transition-colors text-sm sm:text-[15px] truncate">
              {t('appTitle')}
            </div>
            <div className="text-[10px] sm:text-[11px] text-stone-400 mt-0.5 truncate">{t('appSubtitle')}</div>
          </div>
        </Link>
        </div>

        {/* Right side: touch-friendly min sizes, responsive gaps */}
        <div className="flex items-center gap-0.5 sm:gap-1 flex-shrink-0">
          {/* Shopping list button */}
          <button
            onClick={openPanel}
            className="relative min-h-[44px] min-w-[44px] p-2 rounded-xl text-stone-200 hover:bg-amber-500/15 hover:text-amber-300 transition-colors flex items-center justify-center"
            title={t('shoppingList')}
          >
            <span className="text-xl">🛒</span>
            {listCount > 0 && (
              <span className="absolute top-0.5 right-0.5 min-w-[18px] h-[18px] bg-amber-500 text-white rounded-full text-[10px] flex items-center justify-center font-bold px-1">
                {listCount}
              </span>
            )}
          </button>

          {(user || isTrial) && (
            <Link
              to="/meal-plan"
              onClick={(e) => {
                if (location.pathname === '/meal-plan') {
                  e.preventDefault()
                  window.dispatchEvent(new CustomEvent('mealplan:reset-request'))
                }
              }}
              className={`min-h-[44px] flex items-center px-2.5 sm:px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                location.pathname === '/meal-plan'
                  ? 'bg-amber-500/15 text-amber-300'
                  : 'text-stone-300 hover:bg-stone-800/60 hover:text-stone-50'
              }`}
            >
              {t('mealPlan')}
            </Link>
          )}

          <div className="w-px h-5 bg-stone-700 mx-0.5 sm:mx-1 hidden sm:block" />

          {user && (
            <span className="text-xs font-medium text-stone-500 mr-0.5 sm:mr-1 max-w-[64px] sm:max-w-none truncate" title={quotaLabel}>
              {quotaLabel}
            </span>
          )}
          {isTrial && (
            <span className="text-xs font-medium text-amber-400/90 mr-0.5 sm:mr-1" title="Free trial AI actions">
              {trialQuotaLabel}
            </span>
          )}

          {user?.is_admin && (
            <Link
              to="/admin"
              className={`min-h-[44px] flex items-center px-2.5 sm:px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                location.pathname === '/admin'
                  ? 'bg-amber-500/15 text-amber-300'
                  : 'text-stone-300 hover:bg-stone-800/60 hover:text-stone-50'
              }`}
            >
              Admin
            </Link>
          )}

          {/* User / trial account menu */}
          <div className="relative ml-1">
            <button
              type="button"
              onClick={() => setMenuOpen(o => !o)}
              className="min-h-[44px] min-w-[44px] px-2.5 sm:px-3 py-2 rounded-xl text-sm font-medium text-stone-200 hover:bg-stone-800/60 hover:text-stone-50 flex items-center justify-center gap-2"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-xs font-bold">
                {user ? initials : '👤'}
              </span>
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-1 w-40 bg-stone-900 border border-stone-700 rounded-xl shadow-lg py-1 text-sm z-20">
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false)
                    navigate('/settings')
                  }}
                  className={`w-full text-left px-3 py-2 hover:bg-stone-800/80 ${
                    isSettings ? 'text-amber-300' : 'text-stone-100'
                  }`}
                >
                  {t('settings')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false)
                    navigate('/meal-plan')
                  }}
                  className={`w-full text-left px-3 py-2 hover:bg-stone-800/80 ${
                    location.pathname === '/meal-plan' ? 'text-amber-300' : 'text-stone-100'
                  }`}
                >
                  {t('mealPlan')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false)
                    handleSignOut()
                  }}
                  className="w-full text-left px-3 py-2 text-red-300 hover:bg-red-500/10"
                >
                  {t('signOut')}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
