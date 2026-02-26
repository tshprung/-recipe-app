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
      new Error('ANTHROPIC_API_KEY is not configured on the server.')
    )
    renderPage()
    await screen.findByText('Zupa Pomidorowa')

    await userEvent.click(screen.getByText(/Dostosuj przepis/))
    await userEvent.click(screen.getByRole('button', { name: 'Wegański' }))

    await waitFor(() => {
      expect(
        screen.getByText(/ANTHROPIC_API_KEY is not configured/)
      ).toBeInTheDocument()
    })
  })
})
