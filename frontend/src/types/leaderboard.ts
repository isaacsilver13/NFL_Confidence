export interface MemberGamePick {
  gameId: string
  team: string | null
  confidence: number | null
}

export interface LeaderboardMember {
  rank: number
  memberId: string
  memberName: string
  totalPoints: number
  correctPicks: number
  incorrectPicks: number
  weeklyWins: number
  firstPlaceFinishes: number
  secondPlaceFinishes: number
  thirdPlaceFinishes: number
  payoutCents: number
  pointsRemaining: number
  lastTwoGamePicks: MemberGamePick[]
}

export interface CompletedWeek {
  weekNumber: number
  seasonNumber: number
}

export interface GameLabel {
  gameId: string
  awayTeam: string
  homeTeam: string
}

export interface WeeklyLeaderboard {
  week: {
    weekNumber: number
    seasonNumber: number
  }
  standings: LeaderboardMember[]
  lastTwoGames: GameLabel[]
}

export interface SeasonStandings {
  season: number
  standings: LeaderboardMember[]
}

export interface TeamPickCount {
  team: string
  userCount: number
}

export interface GamePickBreakdown {
  gameId: string
  awayTeam: string
  homeTeam: string
  awayRecord: string | null
  homeRecord: string | null
  medianConfidence: number | null
  teamCounts: TeamPickCount[]
}

export interface WeeklyPickBreakdown {
  weekNumber: number
  games: GamePickBreakdown[]
}

export interface PickBreakdown {
  season: number
  weeks: WeeklyPickBreakdown[]
}

export interface GamePickDetail {
  memberName: string
  team: string
  confidence: number
  isCorrect: boolean | null
}

export interface GamePicks {
  gameId: string
  awayTeam: string
  homeTeam: string
  picks: GamePickDetail[]
}
