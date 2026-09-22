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
})
