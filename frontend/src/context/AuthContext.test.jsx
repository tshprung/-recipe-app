import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AuthProvider, useAuth } from './AuthContext'
import { TRIAL_RECIPES_KEY, TRIAL_REMAINING_KEY, TRIAL_TOKEN_KEY } from '../constants/storageKeys'

// Minimal component that exposes leaveTrial for testing
function TestConsumer() {
  const { leaveTrial } = useAuth()
  return <button type="button" onClick={leaveTrial}>Sign out</button>
}

describe('AuthContext leaveTrial', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.clear()
    sessionStorage.clear()
  })
  afterEach(() => {
    vi.useRealTimers()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('clears trial token and related storage so refresh does not restore trial', () => {
    localStorage.setItem(TRIAL_TOKEN_KEY, 'trial-token-123')
    localStorage.setItem(TRIAL_REMAINING_KEY, '3')
    localStorage.setItem(TRIAL_RECIPES_KEY, '[]')

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    )
    expect(localStorage.getItem(TRIAL_TOKEN_KEY)).toBe('trial-token-123')

    act(() => {
      screen.getByRole('button', { name: 'Sign out' }).click()
    })

    expect(localStorage.getItem(TRIAL_TOKEN_KEY)).toBeNull()
    expect(localStorage.getItem(TRIAL_RECIPES_KEY)).toBeNull()
    // TRIAL_REMAINING_KEY is cleared (setTrialRemainingStorage(null) removes it)
    expect(localStorage.getItem(TRIAL_REMAINING_KEY)).toBeNull()
  })
})
