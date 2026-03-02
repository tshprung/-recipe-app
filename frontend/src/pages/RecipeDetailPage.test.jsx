import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import RecipeDetailPage from './RecipeDetailPage'
import { api } from '../api/client'

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
  source_language: 'he',
  source_country: 'IL',
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

function renderPage(id = '1') {
  return render(
    <MemoryRouter initialEntries={[`/recipes/${id}`]}>
      <Routes>
        <Route path="/recipes/:id" element={<RecipeDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('RecipeDetailPage — adaptation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockImplementation(path =>
      path.endsWith('/variants') ? Promise.resolve([]) : Promise.resolve(MOCK_RECIPE)
    )
  })

  it('shows Oryginał badge on the original recipe', async () => {
    renderPage()
    // Wait for the recipe to load
    await screen.findByText('Zupa Pomidorowa')
    expect(screen.getByText('Oryginał')).toBeInTheDocument()
  })

  it('clicking Wegański triggers POST /recipes/1/adapt with variant_type: vegan', async () => {
    api.post.mockResolvedValue({
      can_adapt: true,
      variant: MOCK_VEGAN_VARIANT,
      alternatives: [],
    })
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    // Open the adapt dropdown
    await userEvent.click(screen.getByText(/Dostosuj przepis/))
    // Click the Wegański option
    await userEvent.click(screen.getByRole('button', { name: 'Wegański' }))

    expect(api.post).toHaveBeenCalledWith('/recipes/1/adapt', { variant_type: 'vegan' })
  })

  it('after successful adaptation the variant tab and Wegański badge appear', async () => {
    api.post.mockResolvedValue({
      can_adapt: true,
      variant: MOCK_VEGAN_VARIANT,
      alternatives: [],
    })
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    await userEvent.click(screen.getByText(/Dostosuj przepis/))
    await userEvent.click(screen.getByRole('button', { name: 'Wegański' }))

    // The tab bar and badge should now show Wegański
    await waitFor(() => {
      // At least one element with text "Wegański" must appear (tab button or hero badge)
      const hits = screen.getAllByText('Wegański')
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

    await userEvent.click(screen.getByText(/Dostosuj przepis/))
    await userEvent.click(screen.getByRole('button', { name: 'Wegański' }))

    await waitFor(() => {
      expect(screen.getByText('1 cebula bez masła')).toBeInTheDocument()
    })
    // Original ingredient label should no longer be shown (replaced by variant)
    expect(screen.queryByText('1 sztuka cebula')).not.toBeInTheDocument()
  })

  it('shows an error message when the API call fails', async () => {
    api.post.mockRejectedValue(
      new Error('OPENAI_API_KEY is not configured on the server.')
    )
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    await userEvent.click(screen.getByText(/Dostosuj przepis/))
    await userEvent.click(screen.getByRole('button', { name: 'Wegański' }))

    await waitFor(() => {
      expect(
        screen.getByText(/OPENAI_API_KEY is not configured/)
      ).toBeInTheDocument()
    })
  })
})

describe('RecipeDetailPage — error handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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

  it('falls back to Polish message when the error has no message text', async () => {
    api.get.mockRejectedValue(new Error(''))
    renderPage()
    await screen.findByText('Nie znaleziono przepisu')
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
    await userEvent.click(screen.getByText(/Dostosuj przepis/))
    await userEvent.click(screen.getByRole('button', { name: 'Wegański' }))
    await waitFor(() => screen.getAllByText('Wegański'))
  }

  it('"Wróć do oryginału" button is visible when viewing a variant', async () => {
    await adaptToVegan()
    expect(screen.getByText(/Wróć do oryginału/)).toBeInTheDocument()
  })

  it('"Wróć do oryginału" is NOT shown when already on original tab', async () => {
    renderPage()
    await screen.findByText('Zupa Pomidorowa')
    expect(screen.queryByText(/Wróć do oryginału/)).not.toBeInTheDocument()
  })

  it('clicking "Wróć do oryginału" switches back to the original recipe', async () => {
    await adaptToVegan()

    // Currently on the vegan variant — variant ingredient is visible
    expect(screen.getByText('1 cebula bez masła')).toBeInTheDocument()

    await userEvent.click(screen.getByText(/Wróć do oryginału/))

    // Back to original — original ingredient is visible again
    await waitFor(() => {
      expect(screen.queryByText('1 cebula bez masła')).not.toBeInTheDocument()
    })
    // "Oryginał" appears in both the hero badge and the tab bar
    expect(screen.getAllByText('Oryginał').length).toBeGreaterThanOrEqual(1)
  })

  it('tab bar highlights the active tab and allows switching', async () => {
    await adaptToVegan()

    // The Oryginał tab button exists in the tab bar
    const originalTab = screen.getByRole('button', { name: 'Oryginał' })
    expect(originalTab).toBeInTheDocument()

    // Click the Oryginał tab
    await userEvent.click(originalTab)

    // Should be back on original — variant-specific ingredient gone
    await waitFor(() => {
      expect(screen.queryByText('1 cebula bez masła')).not.toBeInTheDocument()
    })
  })
})
