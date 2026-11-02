import { describe, expect, it } from 'vitest'
import type { NflGame, NflPick } from '@/types/nfl'
import { allGamesSettled, pickOutcome } from './pickOutcome'

const pick = { team: 'KC' } as NflPick
const game = (patch: Partial<NflGame>) =>
  ({ status: 'final', winningTeam: 'KC', isTie: false, ...patch }) as NflGame

describe('pickOutcome', () => {
  it('is correct or wrong only for a final game with a winner', () => {
    expect(pickOutcome(pick, game({}))).toBe('correct')
    expect(pickOutcome(pick, game({ winningTeam: 'BUF' }))).toBe('wrong')
  })

  it('stays pending for live, tied, cancelled, and winnerless games', () => {
    expect(pickOutcome(pick, game({ status: 'live' }))).toBe('pending')
    expect(pickOutcome(pick, game({ isTie: true }))).toBe('pending')
    expect(pickOutcome(pick, game({ status: 'cancelled', winningTeam: null }))).toBe('pending')
    expect(pickOutcome(pick, game({ winningTeam: null }))).toBe('pending')
  })
})

describe('allGamesSettled', () => {
  it('stops polling only when every game is final or cancelled', () => {
    expect(allGamesSettled([{ status: 'final' }, { status: 'cancelled' }])).toBe(true)
    expect(allGamesSettled([{ status: 'final' }, { status: 'live' }])).toBe(false)
  })
})
