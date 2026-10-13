export interface TeamPalette {
  background: string
  foreground: string
}

// Hex values follow the NFL Record & Fact Book / team logo-slick colors as aggregated by
// teamcolorcodes.com (WAS #5A1414/#FFB612 matches the Commanders' 2026 logo slick).
const TEAM_PALETTES: Record<string, TeamPalette> = {
  // AFC East
  BAL: { background: '#241773', foreground: '#ffffff' },
  BUF: { background: '#c60c30', foreground: '#ffffff' },
  MIA: { background: '#008d97', foreground: '#ffffff' },
  NE: { background: '#002244', foreground: '#ffffff' },
  NYJ: { background: '#125740', foreground: '#ffffff' },
  // AFC Central
  CIN: { background: '#fb4f14', foreground: '#111827' },
  CLE: { background: '#311c1c', foreground: '#ff3c00' },
  PIT: { background: '#101820', foreground: '#ffb612' },
  HOU: { background: '#eb6e1f', foreground: '#003831' },
  // AFC West
  DEN: { background: '#002244', foreground: '#fb4f14' },
  KC: { background: '#e31837', foreground: '#ffffff' },
  LAC: { background: '#0080c6', foreground: '#ffc52f' },
  LV: { background: '#000000', foreground: '#a5a5a5' },
  // AFC South
  IND: { background: '#002c5f', foreground: '#a2aaad' },
  JAX: { background: '#006687', foreground: '#000000' },
  TB: { background: '#092c5f', foreground: '#d50a0a' },
  TEN: { background: '#0c2c56', foreground: '#a2aaad' },
  // NFC East
  DAL: { background: '#003594', foreground: '#ffffff' },
  PHI: { background: '#004c54', foreground: '#ffffff' },
  WAS: { background: '#5a1414', foreground: '#ffb612' },
  // NFC South
  ATL: { background: '#a71930', foreground: '#ffffff' },
  CAR: { background: '#0085ca', foreground: '#101820' },
  NO: { background: '#d3bc8d', foreground: '#101820' },
  NYG: { background: '#0b2265', foreground: '#a71930' },
  // NFC Central
  CHI: { background: '#c83803', foreground: '#ffffff' },
  DET: { background: '#0076b6', foreground: '#b0b7bc' },
  GB: { background: '#203731', foreground: '#ffb612' },
  MIN: { background: '#4f2683', foreground: '#ffc52f' },
  // NFC West
  ARI: { background: '#97233f', foreground: '#ffb612' },
  LAR: { background: '#003594', foreground: '#ffd100' },
  SF: { background: '#aa0000', foreground: '#ffffff' },
  SEA: { background: '#0c2c56', foreground: '#69be28' },
}

const FALLBACK_PALETTE: TeamPalette = { background: '#526777', foreground: '#ffffff' }

export function getTeamPalette(code: string): TeamPalette {
  return TEAM_PALETTES[code.trim().toUpperCase()] ?? FALLBACK_PALETTE
}
