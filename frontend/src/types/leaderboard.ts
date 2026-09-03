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
}

export interface CompletedWeek {
  weekNumber: number
  seasonNumber: number
}

export interface WeeklyLeaderboard {
  week: {
    weekNumber: number
    seasonNumber: number
  }
  standings: LeaderboardMember[]
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
