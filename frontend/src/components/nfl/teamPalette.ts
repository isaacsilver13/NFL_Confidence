export interface TeamPalette {
  background: string
  foreground: string
}

const TEAM_PALETTES: Record<string, TeamPalette> = {
  // AFC East
  BAL: { background: '#241773', foreground: '#ffffff' },
  BUF: { background: '#c60c30', foreground: '#ffffff' },
  MIA: { background: '#008d97', foreground: '#ffffff' },
  NE: { background: '#002244', foreground: '#ffffff' },
  // AFC Central
  CIN: { background: '#fb4f14', foreground: '#111827' },
  CLE: { background: '#311c1c', foreground: '#ff3c00' },
  PIT: { background: '#27251f', foreground: '#fdb827' },
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
  WAS: { background: '#5a1f1a', foreground: '#ffc52f' },
  NYG: { background: '#0b2265', foreground: '#a71930' },
  // NFC Central
  CHI: { background: '#c83803', foreground: '#ffffff' },
  DET: { background: '#0076b6', foreground: '#b0b7bc' },
  GB: { background: '#203731', foreground: '#ffb612' },
  MIN: { background: '#4f2683', foreground: '#ffc52f' },
  // NFC West
  ARI: { background: '#97233f', foreground: '#ffb612' },
  LAR: { background: '#003831', foreground: '#b0b7bc' },
  SF: { background: '#aa0000', foreground: '#ffffff' },
  SEA: { background: '#0c2c56', foreground: '#69be28' },
}

const FALLBACK_PALETTE: TeamPalette = { background: '#526777', foreground: '#ffffff' }

export function getTeamPalette(code: string): TeamPalette {
  return TEAM_PALETTES[code.trim().toUpperCase()] ?? FALLBACK_PALETTE
}
