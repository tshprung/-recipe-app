import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { useShoppingList } from '../context/ShoppingListContext'

export default function Navbar() {
  const { user, logout, trialToken, trialRemainingActions, leaveTrial } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const location = useLocation()
  const { recipeIds, openPanel } = useShoppingList()

  function handleLogout() {
    logout()
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

  return (
    <nav className="bg-black/70 backdrop-blur border-b border-white/10 shadow-sm sticky top-0 z-10 print:hidden pt-[env(safe-area-inset-top)] text-stone-50">
      <div className="max-w-5xl mx-auto px-3 sm:px-4 min-h-[56px] sm:h-16 flex items-center justify-between gap-2">

        {/* Logo + What can I make */}
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
        <Link
          to="/what-can-i-make"
          className={`hidden sm:flex items-center px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
            location.pathname === '/what-can-i-make'
              ? 'bg-amber-500/15 text-amber-300'
              : 'text-stone-300 hover:bg-stone-800/60 hover:text-stone-50'
          }`}
        >
          {t('whatCanIMakeNav')}
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
          <Link
            to="/settings"
            className={`min-h-[44px] flex items-center px-2.5 sm:px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
            isSettings
              ? 'bg-amber-500/15 text-amber-300'
              : 'text-stone-300 hover:bg-stone-800/60 hover:text-stone-50'
            }`}
          >
            {t('settings')}
          </Link>

          <div className="w-px h-5 bg-stone-700 mx-0.5 sm:mx-1 hidden sm:block" />

          <div className="flex items-center gap-1.5 sm:gap-2.5">
            {user ? (
              <>
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white text-sm font-bold shadow-sm flex-shrink-0">
                  {initials}
                </div>
                <span className="text-sm text-stone-300 hidden md:block max-w-[160px] truncate">
                  {user.email}
                </span>
                <button
                  onClick={handleLogout}
                  className="min-h-[44px] px-2.5 sm:px-3 py-2 rounded-xl text-sm font-medium text-stone-300 hover:bg-red-500/15 hover:text-red-300 transition-colors"
                >
                  {t('logOut')}
                </button>
              </>
            ) : (
              <>
                <span className="text-xs text-stone-500 hidden sm:inline">Trial</span>
                <Link
                  to="/signin"
                  className="min-h-[44px] px-2.5 sm:px-3 py-2 rounded-xl text-sm font-medium text-amber-400 hover:text-amber-300 transition-colors"
                >
                  {t('signIn')}
                </Link>
                <Link
                  to="/register"
                  className="min-h-[44px] px-2.5 sm:px-3 py-2 rounded-xl text-sm font-medium text-stone-300 hover:text-stone-50 hover:bg-stone-700/50 transition-colors"
                >
                  {t('register')}
                </Link>
                {isTrial && (
                  <button
                    type="button"
                    onClick={() => {
                      leaveTrial()
                      navigate('/', { replace: true })
                    }}
                    className="min-h-[44px] px-2.5 sm:px-3 py-2 rounded-xl text-sm font-medium text-stone-400 hover:text-stone-200 transition-colors"
                  >
                    {t('signOut')}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
