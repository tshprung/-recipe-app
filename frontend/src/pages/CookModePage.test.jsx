import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import CookModePage from './CookModePage'
import { LanguageProvider } from '../context/LanguageContext'
import { api } from '../api/client'

vi.mock('../api/client', async importOriginal => {
  const actual = await importOriginal()
  return {
    ...actual,
    api: {
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    },
  }
})

const MOCK_RECIPE = {
  id: 1,
  title_pl: 'Tomato Soup',
  steps_pl: ['Chop onion.', 'Cook onion in oil.', 'Add tomatoes and simmer.'],
}

function renderPage() {
  return render(
    <LanguageProvider>
      <MemoryRouter initialEntries={['/recipes/1/cook']}>
        <Routes>
          <Route path="/recipes/:id/cook" element={<CookModePage />} />
          <Route path="/recipes/:id" element={<div>Recipe detail</div>} />
        </Routes>
      </MemoryRouter>
    </LanguageProvider>
  )
}

describe('CookModePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue(MOCK_RECIPE)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders step flow and finishes cooking', async () => {
    renderPage()
    await screen.findByText('Tomato Soup')
    expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Back' })).toBeDisabled()

    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText(/step 2 of 3/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByRole('button', { name: 'Finish cooking' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Finish cooking' }))
    await screen.findByRole('button', { name: 'Back to recipe' })
  })

  it('shows no-steps fallback and can return', async () => {
    api.get.mockResolvedValue({ ...MOCK_RECIPE, steps_pl: [] })
    renderPage()

    await screen.findByText('This recipe has no cooking steps yet.')
    await userEvent.click(screen.getByRole('button', { name: 'Back to recipe' }))
    await screen.findByText('Recipe detail')
  })

  it('supports timer start, pause, resume and cancel', async () => {
    renderPage()
    await screen.findByText('Tomato Soup')

    const minutesInput = screen.getByLabelText('minutes')
    await userEvent.clear(minutesInput)
    await userEvent.type(minutesInput, '1')
    await userEvent.click(screen.getAllByRole('button', { name: 'Start timer' })[0])

    await screen.findByText('Timers')
    expect(screen.getByText(/01:0[0-9]/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Pause timer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Resume timer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancel timer' }))

    await waitFor(() => {
      expect(screen.queryByText('Timers')).not.toBeInTheDocument()
    })
  })
})
