import type { NflGame, NflPick, NflWeek, PickHistory, SavePicksInput } from '@/types/nfl'
import { apiFetch } from './client'

export function fetchCurrentWeek(): Promise<NflWeek> {
  return apiFetch<NflWeek>('/weeks/current')
}

export function fetchCurrentGames(): Promise<NflGame[]> {
  return apiFetch<NflGame[]>('/games/current')
}

export function fetchCurrentPicks(): Promise<NflPick[]> {
  return apiFetch<NflPick[]>('/picks/current')
}

export function fetchPickHistory(): Promise<PickHistory> {
  return apiFetch<PickHistory>('/picks/history')
}

export function savePicks(input: SavePicksInput): Promise<NflPick[]> {
  return apiFetch<NflPick[]>('/picks', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
