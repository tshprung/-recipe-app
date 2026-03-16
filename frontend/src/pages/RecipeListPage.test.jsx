import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import RecipeListPage from './RecipeListPage'
import { api } from '../api/client'
import { LanguageProvider } from '../context/LanguageContext'
import { AuthProvider } from '../context/AuthContext'
import { ShoppingListProvider } from '../context/ShoppingListContext'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    api: {
      ...actual.api,
      get: vi.fn(),
    },
  }
})

function renderPage() {
  return render(
    <AuthProvider>
      <LanguageProvider>
        <ShoppingListProvider>
          <MemoryRouter>
            <RecipeListPage />
          </MemoryRouter>
        </ShoppingListProvider>
      </LanguageProvider>
    </AuthProvider>
  )
}

describe('RecipeListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue([])
  })

  it('renders My recipes heading', async () => {
    renderPage()
    await screen.findByText('My recipes')
    expect(screen.getByText('My recipes')).toBeInTheDocument()
  })

  it('renders Add button and Find new recipes button', async () => {
    renderPage()
    await screen.findByText('My recipes')
    expect(screen.getByRole('button', { name: '+Add' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Find new recipes' })).toBeInTheDocument()
  })

  it('renders empty cookbook state when no recipes', async () => {
    renderPage()
    await screen.findByText('Your cookbook is empty')
    expect(screen.getByText('Your cookbook is empty')).toBeInTheDocument()
  })

  it('renders Add your first recipe button when empty', async () => {
    renderPage()
    await screen.findByText('Your cookbook is empty')
    expect(screen.getByRole('button', { name: '+Add your first recipe' })).toBeInTheDocument()
  })
})
