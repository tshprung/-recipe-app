import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AddRecipeModal from './AddRecipeModal'
import { LanguageProvider } from '../context/LanguageContext'

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    refreshUser: vi.fn(),
  }),
}))

vi.mock('../api/client', () => ({
  api: {
    post: vi.fn(),
  },
}))

function renderModal(props = {}) {
  return render(
    <LanguageProvider>
      <AddRecipeModal
        onClose={vi.fn()}
        onCreated={vi.fn()}
        {...props}
      />
    </LanguageProvider>
  )
}

describe('AddRecipeModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders modal title', () => {
    renderModal()
    expect(screen.getByText('Add recipe')).toBeInTheDocument()
  })

  it('renders Paste text and Paste URL tab buttons', () => {
    renderModal()
    expect(screen.getByRole('button', { name: 'Paste text' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Paste URL' })).toBeInTheDocument()
  })

  it('renders Cancel button', () => {
    renderModal()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
  })

  it('renders Translate submit button', () => {
    renderModal()
    expect(screen.getByRole('button', { name: /Translate/ })).toBeInTheDocument()
  })

  it('renders recipe placeholder in paste text mode', () => {
    renderModal()
    expect(screen.getByPlaceholderText('Paste your recipe here…')).toBeInTheDocument()
  })
})
