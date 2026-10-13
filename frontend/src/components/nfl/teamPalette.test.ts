import { describe, expect, it } from 'vitest'
import { getTeamPalette } from './teamPalette'

describe('getTeamPalette', () => {
  it('returns the configured palette for a known team code', () => {
    expect(getTeamPalette('KC')).toEqual({ background: '#e31837', foreground: '#ffffff' })
  })

  it('is case-insensitive and trims whitespace', () => {
    expect(getTeamPalette('  kc  ')).toEqual({ background: '#e31837', foreground: '#ffffff' })
  })

  it('returns a sensible fallback palette for an unknown team code', () => {
    expect(getTeamPalette('XXX')).toEqual({ background: '#526777', foreground: '#ffffff' })
  })
  it('has a palette for every NFL team (no fallback gray)', () => {
    const teams =
      'ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LAC LAR LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS'.split(
        ' ',
      )
    for (const team of teams) expect(getTeamPalette(team).background).not.toBe('#526777')
  })
})
