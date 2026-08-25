import { describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { JoinLeaguePage } from './JoinLeaguePage'

vi.mock('@/api/league', () => ({
  joinLeague: vi.fn(),
}))

const { joinLeague } = await import('@/api/league')
const mockedJoinLeague = vi.mocked(joinLeague)

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/join" element={<JoinLeaguePage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('JoinLeaguePage', () => {
  it('shows an error when the invite link has no token', async () => {
    await act(async () => {
      renderAt('/join')
    })

    expect(screen.getByText(/missing a token/i)).toBeInTheDocument()
    expect(mockedJoinLeague).not.toHaveBeenCalled()
  })

  it('shows a success message once the join call resolves', async () => {
    mockedJoinLeague.mockResolvedValueOnce(undefined)

    await act(async () => {
      renderAt('/join?token=abc123')
    })

    await waitFor(() => expect(screen.getByText(/you're in/i)).toBeInTheDocument())
    expect(mockedJoinLeague).toHaveBeenCalledWith('abc123')
  })

  it('shows the API error message when the join call fails', async () => {
    mockedJoinLeague.mockRejectedValueOnce(new ApiError(409, 'CONFLICT', 'Already a member.'))

    await act(async () => {
      renderAt('/join?token=abc123')
    })

    await waitFor(() => expect(screen.getByText('Already a member.')).toBeInTheDocument())
  })
})
