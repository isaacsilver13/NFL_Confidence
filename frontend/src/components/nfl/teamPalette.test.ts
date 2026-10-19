import { describe, expect, it } from 'vitest'
import { ALL_TEAM_CODES } from '@/assets/teamLogos'
import { getTeamPalette, getTeamSelectionStyle } from './teamPalette'

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

  it('maps the WSH alias to Washington', () => {
    expect(getTeamPalette('WSH')).toEqual(getTeamPalette('WAS'))
  })

  it('uses the secondary color for teams whose primary is black', () => {
    expect(getTeamPalette('LV').background).toBe('#a5acaf')
    expect(getTeamPalette('JAX').background).toBe('#d7a22a')
  })
  it('provides a team palette and readable selected text for all 32 teams', () => {
    const luminance = (hex: string) => {
      const linear = [1, 3, 5].map((offset) => {
        const value = parseInt(hex.slice(offset, offset + 2), 16) / 255
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
      })
      return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722
    }
    for (const team of ALL_TEAM_CODES) {
      const style = getTeamSelectionStyle(team)
      expect(style.backgroundColor, team).not.toBe(getTeamPalette('unknown').background)
      const values = [luminance(style.backgroundColor), luminance(style.color)].sort(
        (a, b) => a - b,
      )
      expect((values[1] + 0.05) / (values[0] + 0.05), team).toBeGreaterThanOrEqual(4.5)
    }
    expect(getTeamSelectionStyle('WSH')).toEqual(getTeamSelectionStyle('WAS'))
  })
})
