import type { PickBreakdown, SeasonStandings, WeeklyLeaderboard } from '@/types/leaderboard'
import { apiFetch } from './client'

function withQuery(path: string, values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `${path}?${query}` : path
}

export function fetchWeeklyLeaderboard(week?: number): Promise<WeeklyLeaderboard> {
  return apiFetch<WeeklyLeaderboard>(withQuery('/leaderboard/week', { week }))
}

export function fetchSeasonStandings(season?: number): Promise<SeasonStandings> {
  return apiFetch<SeasonStandings>(withQuery('/leaderboard/season', { season }))
}

export function fetchPickBreakdown(): Promise<PickBreakdown> {
  return apiFetch<PickBreakdown>('/leaderboard/pick-breakdown')
}
