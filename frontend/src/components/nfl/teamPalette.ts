export interface TeamPalette {
  background: string
  foreground: string
}

// Background is the team's primary color, or its secondary when the primary is black (LV, JAX).
// Source: NFL Record & Fact Book / logo-slick colors via teamcolorcodes.com. Foreground is the
// team's secondary when it has enough contrast against the background, else white/near-black.
const TEAM_PALETTES: Record<string, TeamPalette> = {
  ARI: { background: '#97233f', foreground: '#ffffff' },
  ATL: { background: '#a71930', foreground: '#ffffff' },
  BAL: { background: '#241773', foreground: '#ffffff' },
  BUF: { background: '#00338d', foreground: '#ffffff' },
  CAR: { background: '#0085ca', foreground: '#101820' },
  CHI: { background: '#0b162a', foreground: '#c83803' },
  CIN: { background: '#fb4f14', foreground: '#101820' },
  CLE: { background: '#311d00', foreground: '#ff3c00' },
  DAL: { background: '#003594', foreground: '#ffffff' },
  DEN: { background: '#fb4f14', foreground: '#002244' },
  DET: { background: '#0076b6', foreground: '#ffffff' },
  GB: { background: '#203731', foreground: '#ffb612' },
  HOU: { background: '#03202f', foreground: '#ffffff' },
  IND: { background: '#002c5f', foreground: '#a2aaad' },
  JAX: { background: '#d7a22a', foreground: '#101820' },
  KC: { background: '#e31837', foreground: '#ffffff' },
  LAC: { background: '#0080c6', foreground: '#ffffff' },
  LAR: { background: '#003594', foreground: '#ffa300' },
  LV: { background: '#a5acaf', foreground: '#101820' },
  MIA: { background: '#008e97', foreground: '#101820' },
  MIN: { background: '#4f2683', foreground: '#ffc62f' },
  NE: { background: '#002244', foreground: '#ffffff' },
  NO: { background: '#d3bc8d', foreground: '#101820' },
  NYG: { background: '#0b2265', foreground: '#ffffff' },
  NYJ: { background: '#125740', foreground: '#ffffff' },
  PHI: { background: '#004c54', foreground: '#a5acaf' },
  PIT: { background: '#ffb612', foreground: '#101820' },
  SEA: { background: '#002244', foreground: '#69be28' },
  SF: { background: '#aa0000', foreground: '#ffffff' },
  TB: { background: '#d50a0a', foreground: '#ffffff' },
  TEN: { background: '#0c2340', foreground: '#4b92db' },
  WAS: { background: '#5a1414', foreground: '#ffb612' },
}

const FALLBACK_PALETTE: TeamPalette = { background: '#526777', foreground: '#ffffff' }

export function getTeamPalette(code: string): TeamPalette {
  return TEAM_PALETTES[code.trim().toUpperCase()] ?? FALLBACK_PALETTE
}
