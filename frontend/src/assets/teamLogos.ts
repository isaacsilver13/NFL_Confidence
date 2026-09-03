/**
 * NFL Team Logo Manifest
 *
 * Centralized configuration for all 32 NFL team logos.
 * Each entry maps the ESPN abbreviation to a local PNG asset path.
 *
 * Attribution: Logos are sourced from official NFL team branding.
 * Licensing: Used in accordance with fair use for private league application.
 *
 * Assets are served from frontend/public/logos using the ESPN abbreviation as
 * the filename (for example, /logos/BAL.png).
 */

export interface TeamLogoConfig {
  name: string
  espnCode: string
  logoPath: string
}

// All 32 NFL teams with their official ESPN abbreviations and logo paths
export const TEAM_LOGOS: Record<string, TeamLogoConfig> = {
  // AFC East
  BUF: { name: 'Buffalo Bills', espnCode: 'BUF', logoPath: '/logos/BUF.png' },
  MIA: { name: 'Miami Dolphins', espnCode: 'MIA', logoPath: '/logos/MIA.png' },
  NE: { name: 'New England Patriots', espnCode: 'NE', logoPath: '/logos/NE.png' },
  NYJ: { name: 'New York Jets', espnCode: 'NYJ', logoPath: '/logos/NYJ.png' },

  // AFC North
  BAL: { name: 'Baltimore Ravens', espnCode: 'BAL', logoPath: '/logos/BAL.png' },
  CIN: { name: 'Cincinnati Bengals', espnCode: 'CIN', logoPath: '/logos/CIN.png' },
  CLE: { name: 'Cleveland Browns', espnCode: 'CLE', logoPath: '/logos/CLE.png' },
  PIT: { name: 'Pittsburgh Steelers', espnCode: 'PIT', logoPath: '/logos/PIT.png' },

  // AFC South
  HOU: { name: 'Houston Texans', espnCode: 'HOU', logoPath: '/logos/HOU.png' },
  IND: { name: 'Indianapolis Colts', espnCode: 'IND', logoPath: '/logos/IND.png' },
  JAX: { name: 'Jacksonville Jaguars', espnCode: 'JAX', logoPath: '/logos/JAX.png' },
  TEN: { name: 'Tennessee Titans', espnCode: 'TEN', logoPath: '/logos/TEN.png' },

  // AFC West
  DEN: { name: 'Denver Broncos', espnCode: 'DEN', logoPath: '/logos/DEN.png' },
  KC: { name: 'Kansas City Chiefs', espnCode: 'KC', logoPath: '/logos/KC.png' },
  LAC: { name: 'Los Angeles Chargers', espnCode: 'LAC', logoPath: '/logos/LAC.png' },
  LV: { name: 'Las Vegas Raiders', espnCode: 'LV', logoPath: '/logos/LV.png' },

  // NFC East
  DAL: { name: 'Dallas Cowboys', espnCode: 'DAL', logoPath: '/logos/DAL.png' },
  NYG: { name: 'New York Giants', espnCode: 'NYG', logoPath: '/logos/NYG.png' },
  PHI: { name: 'Philadelphia Eagles', espnCode: 'PHI', logoPath: '/logos/PHI.png' },
  WAS: { name: 'Washington Commanders', espnCode: 'WAS', logoPath: '/logos/WAS.png' },

  // NFC North
  CHI: { name: 'Chicago Bears', espnCode: 'CHI', logoPath: '/logos/CHI.png' },
  DET: { name: 'Detroit Lions', espnCode: 'DET', logoPath: '/logos/DET.png' },
  GB: { name: 'Green Bay Packers', espnCode: 'GB', logoPath: '/logos/GB.png' },
  MIN: { name: 'Minnesota Vikings', espnCode: 'MIN', logoPath: '/logos/MIN.png' },

  // NFC South
  ATL: { name: 'Atlanta Falcons', espnCode: 'ATL', logoPath: '/logos/ATL.png' },
  CAR: { name: 'Carolina Panthers', espnCode: 'CAR', logoPath: '/logos/CAR.png' },
  NO: { name: 'New Orleans Saints', espnCode: 'NO', logoPath: '/logos/NO.png' },
  TB: { name: 'Tampa Bay Buccaneers', espnCode: 'TB', logoPath: '/logos/TB.png' },

  // NFC West
  ARI: { name: 'Arizona Cardinals', espnCode: 'ARI', logoPath: '/logos/ARI.png' },
  LAR: { name: 'Los Angeles Rams', espnCode: 'LAR', logoPath: '/logos/LAR.png' },
  SF: { name: 'San Francisco 49ers', espnCode: 'SF', logoPath: '/logos/SF.png' },
  SEA: { name: 'Seattle Seahawks', espnCode: 'SEA', logoPath: '/logos/SEA.png' },
} as const

export type TeamCode = keyof typeof TEAM_LOGOS

/**
 * Get team logo configuration by ESPN abbreviation.
 * Returns the config if found, or undefined for unknown codes.
 *
 * @param espnCode - The ESPN team abbreviation (e.g., 'KC', 'SF')
 * @returns TeamLogoConfig or undefined
 */
export function getTeamLogoConfig(espnCode: string): TeamLogoConfig | undefined {
  const normalized = espnCode.trim().toUpperCase()
  return TEAM_LOGOS[normalized as TeamCode]
}

/**
 * Get team name by ESPN abbreviation.
 * @param espnCode - The ESPN team abbreviation
 * @returns Full team name or the code if not found
 */
export function getTeamName(espnCode: string): string {
  const config = getTeamLogoConfig(espnCode)
  return config?.name ?? espnCode.toUpperCase()
}

/**
 * Get all team codes (useful for validation or iteration).
 */
export const ALL_TEAM_CODES = Object.keys(TEAM_LOGOS) as TeamCode[]

/**
 * Verify if a team code is valid.
 */
export function isValidTeamCode(code: string): code is TeamCode {
  return code.trim().toUpperCase() in TEAM_LOGOS
}
