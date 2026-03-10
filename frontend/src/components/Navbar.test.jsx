import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Navbar from './Navbar'
import { LanguageProvider } from '../context/LanguageContext'

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      email: 'test@example.com',
      transformations_used: 0,
      transformations_limit: 5,
    },
    logout: vi.fn(),
  }),
}))

vi.mock('../context/ShoppingListContext', () => ({
  useShoppingList: () => ({
    recipeIds: new Set(),
    openPanel: vi.fn(),
  }),
}))

function renderNavbar() {
  return render(
    <LanguageProvider>
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    </LanguageProvider>
  )
}

describe('Navbar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders app title and subtitle', () => {
    renderNavbar()
    expect(screen.getByText('Recipe Translator')).toBeInTheDocument()
    expect(screen.getByText('Recipe translation')).toBeInTheDocument()
  })

  it('does not render UI language selector on main pages', () => {
    renderNavbar()
    expect(screen.queryByTitle('English')).not.toBeInTheDocument()
  })

  it('renders shopping list button', () => {
    renderNavbar()
    expect(screen.getByTitle('Shopping list')).toBeInTheDocument()
  })

  it('renders Settings link', () => {
    renderNavbar()
    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument()
  })

  it('renders Log out button', () => {
    renderNavbar()
    expect(screen.getByRole('button', { name: 'Log out' })).toBeInTheDocument()
  })

  it('renders recipes quota when user is present', () => {
    renderNavbar()
    expect(screen.getByText('Recipes: 0/5')).toBeInTheDocument()
  })
})
