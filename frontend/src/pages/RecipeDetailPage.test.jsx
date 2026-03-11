import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import RecipeDetailPage from './RecipeDetailPage'
import { api } from '../api/client'
import { LanguageProvider } from '../context/LanguageContext'
import { AuthProvider } from '../context/AuthContext'

vi.mock('../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const MOCK_RECIPE = {
  id: 1,
  user_id: 1,
  title_pl: 'Zupa Pomidorowa',
  title_original: 'מרק עגבניות',
  ingredients_pl: [
    { amount: '500g', name: 'pomidory' },
    { amount: '1 sztuka', name: 'cebula' },
  ],
  ingredients_original: [],
  steps_pl: ['Podsmaż cebulę.', 'Dodaj pomidory.'],
  tags: ['zupa'],
  substitutions: {},
  notes: {},
  user_notes: null,
  is_favorite: false,
  raw_input: 'test',
  detected_language: 'he',
  target_language: 'pl',
  target_country: 'PL',
  created_at: '2024-01-01T00:00:00Z',
}

const MOCK_VEGAN_VARIANT = {
  id: 10,
  recipe_id: 1,
  variant_type: 'vegan',
  title_pl: 'Zupa Pomidorowa (wegańska)',
  ingredients_pl: ['500g pomidory', '1 cebula bez masła'],
  steps_pl: ['Podsmaż cebulę.', 'Dodaj pomidory.'],
  notes: { ostrzeżenia: [] },
  created_at: '2024-01-01T00:00:00Z',
}

const DEFAULT_USER = {
  id: 1,
  email: 'u@u.com',
  ui_language: 'en',
  target_language: 'pl',
  target_country: 'PL',
  target_city: 'Wrocław',
  target_zip: null,
  transformations_used: 0,
  transformations_limit: 5,
  is_verified: true,
  account_tier: 'free',
  created_at: '2024-01-01T00:00:00Z',
}

function renderPage(id = '1') {
  localStorage.setItem('token', 'test-token')
  return render(
    <AuthProvider>
      <LanguageProvider>
        <MemoryRouter initialEntries={[`/recipes/${id}`]}>
          <Routes>
            <Route path="/recipes/:id" element={<RecipeDetailPage />} />
          </Routes>
        </MemoryRouter>
      </LanguageProvider>
    </AuthProvider>
  )
}

describe('RecipeDetailPage — adaptation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockImplementation(path => {
      if (path === '/users/me') return Promise.resolve(DEFAULT_USER)
      return path.endsWith('/variants') ? Promise.resolve([]) : Promise.resolve(MOCK_RECIPE)
    })
  })

  it('shows Original badge on the original recipe', async () => {
    renderPage()
    // Wait for the recipe to load
    await screen.findByText('Zupa Pomidorowa')
    expect(screen.getByText('Original')).toBeInTheDocument()
  })

  it('selecting Vegan and Apply triggers POST /recipes/1/adapt with variant_type: vegan', async () => {
    api.post.mockResolvedValue({
      can_adapt: true,
      variant: MOCK_VEGAN_VARIANT,
      alternatives: [],
    })
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    await userEvent.click(screen.getByText(/Adapt recipe/))
    await userEvent.click(screen.getByLabelText('Vegan'))
    await userEvent.click(screen.getByRole('button', { name: 'Apply' }))

    expect(api.post).toHaveBeenCalledWith('/recipes/1/adapt', { variant_type: 'vegan' })
  })

  it('after successful adaptation the variant tab and Vegan badge appear', async () => {
    api.post.mockResolvedValue({
      can_adapt: true,
      variant: MOCK_VEGAN_VARIANT,
      alternatives: [],
    })
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    await userEvent.click(screen.getByText(/Adapt recipe/))
    await userEvent.click(screen.getByLabelText('Vegan'))
    await userEvent.click(screen.getByRole('button', { name: 'Apply' }))

    await waitFor(() => {
      const hits = screen.getAllByText('Vegan')
      expect(hits.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('after successful adaptation the displayed ingredients switch to the variant', async () => {
    api.post.mockResolvedValue({
      can_adapt: true,
      variant: MOCK_VEGAN_VARIANT,
      alternatives: [],
    })
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    await userEvent.click(screen.getByText(/Adapt recipe/))
    await userEvent.click(screen.getByLabelText('Vegan'))
    await userEvent.click(screen.getByRole('button', { name: 'Apply' }))

    await waitFor(() => {
      expect(screen.getByText('1 cebula bez masła')).toBeInTheDocument()
    })
    expect(screen.queryByText('1 sztuka cebula')).not.toBeInTheDocument()
  })

  it('shows an error message when the API call fails', async () => {
    api.post.mockRejectedValue(
      new Error('OPENAI_API_KEY is not configured on the server.')
    )
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    await userEvent.click(screen.getByText(/Adapt recipe/))
    await userEvent.click(screen.getByLabelText('Vegan'))
    await userEvent.click(screen.getByRole('button', { name: 'Apply' }))

    await waitFor(() => {
      expect(
        screen.getByText(/OPENAI_API_KEY is not configured/)
      ).toBeInTheDocument()
    })
  })
})

describe('RecipeDetailPage — re-localize', () => {
  const userWithDifferentLocale = {
    id: 1,
    email: 'u@u.com',
    ui_language: 'en',
    target_language: 'en',
    target_country: 'US',
    target_city: 'New York',
    target_zip: null,
    transformations_used: 0,
    transformations_limit: 5,
    is_verified: true,
    account_tier: 'free',
    created_at: '2024-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockImplementation(path => {
      if (path === '/users/me') return Promise.resolve(userWithDifferentLocale)
      if (path.endsWith('/variants')) return Promise.resolve([])
      return Promise.resolve(MOCK_RECIPE)
    })
  })

  it('shows Re-localize button and calls POST /recipes/1/relocalize', async () => {
    api.post.mockResolvedValue({ ...MOCK_RECIPE, title_pl: 'Zupa Pomidorowa 2' })
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    await userEvent.click(screen.getByRole('button', { name: /Re-localize/ }))
    expect(api.post).toHaveBeenCalledWith('/recipes/1/relocalize', {})
  })
})

describe('RecipeDetailPage — error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('token', 'test-token')
  })

  it('shows the actual API error message when the recipe fetch fails', async () => {
    api.get.mockRejectedValue(new Error('Recipe not found'))
    renderPage()
    await screen.findByText('Recipe not found')
  })

  it('shows the actual error message when only the variants fetch fails', async () => {
    api.get.mockImplementation(path =>
      path.endsWith('/variants')
        ? Promise.reject(new Error('Not Found'))
        : Promise.resolve(MOCK_RECIPE)
    )
    renderPage()
    await screen.findByText('Not Found')
  })

  it('falls back to default message when the error has no message text', async () => {
    api.get.mockRejectedValue(new Error(''))
    renderPage()
    await screen.findByText('Recipe not found')
  })
})

describe('RecipeDetailPage — return to original', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockImplementation(path =>
      path.endsWith('/variants') ? Promise.resolve([]) : Promise.resolve(MOCK_RECIPE)
    )
    api.post.mockResolvedValue({
      can_adapt: true,
      variant: MOCK_VEGAN_VARIANT,
      alternatives: [],
    })
  })

  async function adaptToVegan() {
    renderPage()
    await screen.findByText('Zupa Pomidorowa')
    await userEvent.click(screen.getByText(/Adapt recipe/))
    await userEvent.click(screen.getByLabelText('Vegan'))
    await userEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await waitFor(() => screen.getAllByText('Vegan'))
  }

  it('"Back to original" button is visible when viewing a variant', async () => {
    await adaptToVegan()
    expect(screen.getByText(/Back to original/)).toBeInTheDocument()
  })

  it('"Back to original" is NOT shown when already on original tab', async () => {
    renderPage()
    await screen.findByText('Zupa Pomidorowa')
    expect(screen.queryByText(/Back to original/)).not.toBeInTheDocument()
  })

  it('clicking "Back to original" switches back to the original recipe', async () => {
    await adaptToVegan()

    // Currently on the vegan variant — variant ingredient is visible
    expect(screen.getByText('1 cebula bez masła')).toBeInTheDocument()

    await userEvent.click(screen.getByText(/Back to original/))

    // Back to original — original ingredient is visible again
    await waitFor(() => {
      expect(screen.queryByText('1 cebula bez masła')).not.toBeInTheDocument()
    })
    // "Original" appears in both the hero badge and the tab bar
    expect(screen.getAllByText('Original').length).toBeGreaterThanOrEqual(1)
  })

  it('tab bar highlights the active tab and allows switching', async () => {
    await adaptToVegan()

    // The Original tab button exists in the tab bar
    const originalTab = screen.getByRole('button', { name: 'Original' })
    expect(originalTab).toBeInTheDocument()

    // Click the Original tab
    await userEvent.click(originalTab)

    // Should be back on original — variant-specific ingredient gone
    await waitFor(() => {
      expect(screen.queryByText('1 cebula bez masła')).not.toBeInTheDocument()
    })
  })
})
