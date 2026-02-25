import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ShoppingListProvider } from './context/ShoppingListContext'
import LoginPage from './pages/LoginPage'
import RecipeListPage from './pages/RecipeListPage'
import RecipeDetailPage from './pages/RecipeDetailPage'
import SettingsPage from './pages/SettingsPage'
import Navbar from './components/Navbar'
import ShoppingListPanel from './components/ShoppingListPanel'

// Decorative food items scattered around the background edges
const FOOD_DECOR = [
  // Top-left
  { e: '🌿', cls: 'top-20 left-3 text-8xl -rotate-12' },
  { e: '🍅', cls: 'top-44 left-12 text-5xl rotate-6' },
  { e: '🧄', cls: 'top-72 left-5 text-4xl -rotate-6' },
  // Top-right
  { e: '🫒', cls: 'top-20 right-4 text-7xl rotate-12' },
  { e: '🌶️', cls: 'top-48 right-14 text-5xl -rotate-6' },
  { e: '🍋', cls: 'top-80 right-5 text-4xl rotate-3' },
  // Middle-left
  { e: '🌾', cls: 'top-[42%] left-2 text-7xl -rotate-6' },
  { e: '🧅', cls: 'top-[56%] left-10 text-4xl rotate-12' },
  // Middle-right
  { e: '🫙', cls: 'top-[40%] right-3 text-6xl rotate-6' },
  { e: '🥕', cls: 'top-[58%] right-12 text-4xl -rotate-12' },
  // Bottom-left
  { e: '🥙', cls: 'bottom-32 left-4 text-7xl rotate-6' },
  { e: '🌿', cls: 'bottom-10 left-16 text-5xl -rotate-3' },
  // Bottom-right
  { e: '🍳', cls: 'bottom-28 right-5 text-7xl -rotate-12' },
  { e: '🥗', cls: 'bottom-8 right-20 text-5xl rotate-6' },
]

function FoodBackground() {
  return (
    <div
      className="fixed inset-0 overflow-hidden pointer-events-none select-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    >
      {FOOD_DECOR.map((item, i) => (
        <span
          key={i}
          className={`absolute block opacity-[0.10] ${item.cls}`}
          style={{ lineHeight: 1 }}
        >
          {item.e}
        </span>
      ))}
    </div>
  )
}

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-stone-400 text-sm font-medium">Ładowanie…</span>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    )
  }

  return (
    <ShoppingListProvider>
      <div className="min-h-screen bg-stone-50">
        <FoodBackground />
        {/* Wrap content in relative z-[1] so it sits above the fixed background */}
        <div className="relative" style={{ zIndex: 1 }}>
          <Navbar />
          <main className="max-w-5xl mx-auto px-4 py-8">
            <Routes>
              <Route path="/"            element={<RecipeListPage />} />
              <Route path="/recipes/:id" element={<RecipeDetailPage />} />
              <Route path="/settings"    element={<SettingsPage />} />
              <Route path="*"            element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
        <ShoppingListPanel />
      </div>
    </ShoppingListProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
