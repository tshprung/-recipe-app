import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import CookModePage from './CookModePage'
import { LanguageProvider } from '../context/LanguageContext'
import { api } from '../api/client'
import { COOK_MODE_READ_ALOUD_KEY } from '../constants/storageKeys'

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

function renderPage(initialEntries = ['/recipes/1/cook'], initialIndex) {
  return render(
    <LanguageProvider>
      <MemoryRouter initialEntries={initialEntries} initialIndex={initialIndex}>
        <Routes>
          <Route path="/recipes/:id/cook" element={<CookModePage />} />
          <Route path="/recipes/:id" element={<div>Recipe detail</div>} />
        </Routes>
      </MemoryRouter>
    </LanguageProvider>
  )
}

function RecipeDetailWithBack() {
  const navigate = useNavigate()
  return (
    <div>
      <div>Recipe detail</div>
      <button type="button" onClick={() => navigate(-1)}>Back to main</button>
    </div>
  )
}

describe('CookModePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue(MOCK_RECIPE)

    // TTS mocks
    window.speechSynthesis = {
      cancel: vi.fn(),
      speak: vi.fn(),
    }
    window.SpeechSynthesisUtterance = function SpeechSynthesisUtterance(text) {
      this.text = text
      this.lang = 'en'
      this.rate = 1
      this.pitch = 1
    }

    localStorage.removeItem(COOK_MODE_READ_ALOUD_KEY)
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
  }, 15000)

  it('shows no-steps fallback and can return', async () => {
    api.get.mockResolvedValue({ ...MOCK_RECIPE, steps_pl: [] })
    renderPage(['/recipes/1', '/recipes/1/cook'], 1)

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
    expect(screen.getAllByText(/01:0[0-9]/).length).toBeGreaterThan(0)

    await userEvent.click(screen.getByRole('button', { name: 'Pause timer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Resume timer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancel timer' }))

    await waitFor(() => {
      expect(screen.queryByText('Timers')).not.toBeInTheDocument()
    })
  }, 15000)

  it('auto-reads steps and supports Read step button', async () => {
    renderPage()
    await screen.findByText('Tomato Soup')

    // Auto-read first step
    expect(window.speechSynthesis.speak).toHaveBeenCalled()

    // Manual read
    await userEvent.click(screen.getByRole('button', { name: 'Read step' }))
    expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(2)

    // Next step auto-read
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(3)
  })

  it('read aloud toggle disables auto-read and read button', async () => {
    renderPage()
    await screen.findByText('Tomato Soup')
    expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(1)

    await userEvent.click(screen.getByRole('button', { name: /turn off/i }))
    expect(screen.getByRole('button', { name: 'Read step' })).toBeDisabled()

    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(1)
  })

  it('uses global read aloud setting from local storage', async () => {
    localStorage.setItem(COOK_MODE_READ_ALOUD_KEY, '0')
    renderPage()
    await screen.findByText('Tomato Soup')
    expect(window.speechSynthesis.speak).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Read step' })).toBeDisabled()
  })

  it('exit cooking returns through history so back goes to main screen', async () => {
    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={['/', '/recipes/1', '/recipes/1/cook']} initialIndex={2}>
          <Routes>
            <Route path="/" element={<div>Main screen</div>} />
            <Route path="/recipes/:id/cook" element={<CookModePage />} />
            <Route path="/recipes/:id" element={<RecipeDetailWithBack />} />
          </Routes>
        </MemoryRouter>
      </LanguageProvider>
    )

    await screen.findByText('Tomato Soup')
    await userEvent.click(screen.getByRole('button', { name: 'Exit cooking' }))
    await screen.findByText('Recipe detail')

    await userEvent.click(screen.getByRole('button', { name: 'Back to main' }))
    await screen.findByText('Main screen')
  })
})
