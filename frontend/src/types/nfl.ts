export interface NflWeek {
  id: string
  season: number
  weekNumber: number
  startDate: string
  endDate: string
  status: string
  locksAt?: string | null
  isLocked?: boolean
}

export interface NflGame {
  id: string
  awayTeam: string
  homeTeam: string
  kickoff: string
  status: string
  venueName: string | null
  venueLocation: string | null
  spreadTeam: string | null
  spread: number | null
  awayScore: number | null
  homeScore: number | null
  winningTeam: string | null
  isTie: boolean
}

export interface NflPick {
  id: string
  gameId: string
  team: string
  confidence: number
  submittedAt: string
}

export type PickOutcome = 'correct' | 'incorrect' | 'unscored'

export interface HistoricalPick {
  id: string
  gameId: string
  awayTeam: string
  homeTeam: string
  kickoff: string
  status: string
  team: string
  confidence: number
  submittedAt: string
  winningTeam: string | null
  isTie: boolean
  pointsEarned: number | null
  outcome: PickOutcome
}

export interface HistoricalWeek {
  weekNumber: number
  picks: HistoricalPick[]
}

export interface PickHistory {
  season: number
  weeks: HistoricalWeek[]
}

export interface PickInput {
  gameId: string
  team: string
  confidence: number
}

export interface SavePicksInput {
  week: number
  picks: PickInput[]
}
