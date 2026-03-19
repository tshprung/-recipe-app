import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import CookModePage from './CookModePage'
import { LanguageProvider } from '../context/LanguageContext'
import { api } from '../api/client'

class MockSpeechRecognition {
  constructor() {
    this.continuous = false
    this.interimResults = false
    this.lang = 'en'
    this.onresult = null
    this.onend = null
    this.onerror = null
    this._started = false
    globalThis.__lastSpeechRecognition = this
  }

  start() {
    this._started = true
  }

  stop() {
    this._started = false
  }

  emitFinal(transcript) {
    const event = {
      resultIndex: 0,
      results: [
        {
          isFinal: true,
          0: { transcript },
        },
      ],
    }
    this.onresult?.(event)
  }
}

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

    // Speech recognition mocks
    window.SpeechRecognition = MockSpeechRecognition
    window.webkitSpeechRecognition = undefined
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

  it('executes only helper-prefixed voice commands', async () => {
    renderPage()
    await screen.findByText('Tomato Soup')

    const rec = globalThis.__lastSpeechRecognition
    expect(rec).toBeTruthy()

    // Non-prefixed should do nothing
    await act(async () => { rec.emitFinal('next') })
    expect(screen.getByText(/step 1 of 3/i)).toBeInTheDocument()

    // Prefixed next should advance
    await act(async () => { rec.emitFinal('helper next') })
    await screen.findByText(/step 2 of 3/i)

    // Prefixed back should go back
    await act(async () => { rec.emitFinal('helper back') })
    await screen.findByText(/step 1 of 3/i)

    // Repeat should trigger TTS again
    const callsBefore = window.speechSynthesis.speak.mock.calls.length
    await act(async () => { rec.emitFinal('helper repeat') })
    expect(window.speechSynthesis.speak.mock.calls.length).toBeGreaterThan(callsBefore)
  })

  it('helper pause pauses current step timer only when running', async () => {
    renderPage()
    await screen.findByText('Tomato Soup')

    const rec = globalThis.__lastSpeechRecognition
    expect(rec).toBeTruthy()

    // If no timer running, pause should do nothing (no Resume button)
    await act(async () => { rec.emitFinal('helper pause') })
    expect(screen.queryByRole('button', { name: 'Resume timer' })).not.toBeInTheDocument()

    // Start a timer, then pause via voice
    const minutesInput = screen.getByLabelText('minutes')
    await userEvent.clear(minutesInput)
    await userEvent.type(minutesInput, '1')
    await userEvent.click(screen.getAllByRole('button', { name: 'Start timer' })[0])
    await screen.findByRole('button', { name: 'Pause timer' })

    await act(async () => { rec.emitFinal('helper pause') })
    await screen.findByRole('button', { name: 'Resume timer' })
  }, 15000)

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
