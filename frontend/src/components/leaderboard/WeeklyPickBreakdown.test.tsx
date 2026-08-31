import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WeeklyPickBreakdown } from './WeeklyPickBreakdown'

describe('WeeklyPickBreakdown', () => {
  it('renders per-game counts, percentages, median, and team colors', () => {
    render(
      <WeeklyPickBreakdown
        weeks={[
          {
            weekNumber: 1,
            games: [
              {
                gameId: 'game-1',
                awayTeam: 'CHI',
                homeTeam: 'GB',
                medianConfidence: 4.5,
                teamCounts: [
                  { team: 'CHI', userCount: 6 },
                  { team: 'GB', userCount: 2 },
                ],
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByText('Median confidence:')).toBeInTheDocument()
    expect(screen.getByText('4.5')).toBeInTheDocument()
    expect(screen.getByText('CHI: 6 picks')).toBeInTheDocument()
    expect(screen.getByText('GB: 2 picks')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByText('25%')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'CHI 75 percent, GB 25 percent' })).toBeInTheDocument()
  })

  it('shows an empty state for a game without picks', () => {
    render(
      <WeeklyPickBreakdown
        weeks={[
          {
            weekNumber: 1,
            games: [
              {
                gameId: 'game-1',
                awayTeam: 'BUF',
                homeTeam: 'KC',
                medianConfidence: null,
                teamCounts: [
                  { team: 'BUF', userCount: 0 },
                  { team: 'KC', userCount: 0 },
                ],
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByText('No confidence data')).toBeInTheDocument()
    expect(screen.getByText('No picks were submitted for this game.')).toBeInTheDocument()
  })
})
