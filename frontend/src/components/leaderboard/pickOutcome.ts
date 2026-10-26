import type { NflGame, NflPick } from '@/types/nfl'

export type CellOutcome = 'correct' | 'wrong' | 'pending'

/** Correct or wrong only once the game is final with a winner; live, tied, and cancelled stay pending. */
export function pickOutcome(pick: NflPick, game: NflGame): CellOutcome {
  if (game.status !== 'final' || game.isTie || !game.winningTeam) return 'pending'
  return pick.team === game.winningTeam ? 'correct' : 'wrong'
}

/** True once no game can change anymore, so the picks table can stop polling. */
export function allGamesSettled(games: Pick<NflGame, 'status'>[]): boolean {
  return games.every((game) => game.status === 'final' || game.status === 'cancelled')
}
