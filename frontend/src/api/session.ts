/**
 * Session bootstrap API for optimized app initialization.
 * Combines multiple queries into single round-trips.
 */

import type { User } from '@/types/auth'
import type { League } from '@/types/league'
import type { NflWeek, NflGame, NflPick } from '@/types/nfl'
import { apiFetch } from './client'

/** All data needed to initialize the authenticated app. */
export interface SessionBootstrap {
  user: User
  league: League | null
  currentWeek: NflWeek | null
}

/** Fetches user + league + current week in a single request. */
export async function fetchSessionBootstrap(): Promise<SessionBootstrap> {
  return apiFetch<SessionBootstrap>('/bootstrap')
}

/** Picks card: current week + games + user's picks in a single request. */
export interface CurrentPicksCard {
  week: NflWeek
  games: NflGame[]
  picks: NflPick[]
}

/** Fetches week + games + picks for the current week in a single request. */
export async function fetchCurrentPicksCard(): Promise<CurrentPicksCard> {
  return apiFetch<CurrentPicksCard>('/picks/card/current')
}
