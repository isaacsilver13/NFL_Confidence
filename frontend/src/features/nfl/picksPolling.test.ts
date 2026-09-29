import { describe, expect, it } from 'vitest'
import type { CurrentPicksCard } from '@/api/session'
import type { NflGame, NflWeek } from '@/types/nfl'
import { getPicksCardRefetchInterval, LIVE_GAME_POLL_INTERVAL_MS } from './picksPolling'

const week: NflWeek = {
  id: 'week-1',
  season: 2026,
  weekNumber: 1,
  startDate: '2026-09-01T00:00:00Z',
  endDate: '2026-09-08T00:00:00Z',
  status: 'regular',
}

function game(status: string): NflGame {
  return {
    id: `game-${status}`,
    awayTeam: 'BUF',
    homeTeam: 'KC',
    kickoff: '2026-09-07T20:00:00Z',
    status,
    venueName: null,
    venueLocation: null,
    spreadTeam: null,
    spread: null,
    awayScore: null,
    homeScore: null,
    winningTeam: null,
    isTie: false,
    clock: null,
    period: null,
    awayRecord: null,
    homeRecord: null,
  }
}

function cardWith(games: NflGame[]): CurrentPicksCard {
  return { week, games, picks: [], submission: { submittedAt: null } }
}

describe('getPicksCardRefetchInterval', () => {
  it('returns the live poll interval when a game is live', () => {
    expect(getPicksCardRefetchInterval(cardWith([game('scheduled'), game('live')]))).toBe(
      LIVE_GAME_POLL_INTERVAL_MS,
    )
  })

  it('returns false when no game is live', () => {
    expect(getPicksCardRefetchInterval(cardWith([game('scheduled'), game('final')]))).toBe(false)
  })

  it('returns false for an empty games array', () => {
    expect(getPicksCardRefetchInterval(cardWith([]))).toBe(false)
  })

  it('returns false when data is undefined', () => {
    expect(getPicksCardRefetchInterval(undefined)).toBe(false)
  })
})
