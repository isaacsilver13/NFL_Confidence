import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { fetchAllPicksForWeek } from '@/api/nfl'
import type { AllPicks, MemberPicks, NflGame, NflPick } from '@/types/nfl'
import { Button } from '@/components/ui/Button'
import { SortableTh } from '@/components/ui/SortableTable'
import { useTableSort, type SortColumn } from '@/components/ui/useTableSort'
import { allGamesSettled, pickOutcome, type CellOutcome } from './pickOutcome'

const OUTCOME_CELL_CLASS: Record<CellOutcome, string> = {
  correct: 'bg-success/15 font-semibold text-success',
  wrong: 'bg-danger/10 font-semibold text-danger',
  pending: '',
}

const OUTCOME_MARK: Record<CellOutcome, string> = { correct: '✓', wrong: '✗', pending: '' }
const OUTCOME_LABEL: Record<CellOutcome, string> = {
  correct: 'Correct',
  wrong: 'Wrong',
  pending: '',
}

function PickCell({ pick, game }: { pick: NflPick | undefined; game: NflGame }) {
  const outcome = pick ? pickOutcome(pick, game) : 'pending'
  return (
    <td className={`px-3 py-2 text-center whitespace-nowrap ${OUTCOME_CELL_CLASS[outcome]}`}>
      {pick ? `${pick.team} (${pick.confidence})` : '—'}
      {outcome !== 'pending' && (
        <>
          <span aria-hidden="true"> {OUTCOME_MARK[outcome]}</span>
          <span className="sr-only"> — {OUTCOME_LABEL[outcome]}</span>
        </>
      )}
    </td>
  )
}

/** One member's picks, one game per row so the table scrolls down instead of sideways. */
function MemberPicksTable({ data }: { data: AllPicks }) {
  const picksByGame = new Map((data.members[0]?.picks ?? []).map((pick) => [pick.gameId, pick]))
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="bg-surface-muted dark:bg-night-card">
          <th scope="col" className="sticky top-0 px-3 py-2 text-left font-bold">
            Game
          </th>
          <th scope="col" className="sticky top-0 px-3 py-2 text-center font-bold">
            Pick
          </th>
        </tr>
      </thead>
      <tbody>
        {data.games.map((game) => (
          <tr key={game.id} className="border-t border-slate-200 dark:border-night-line">
            <th scope="row" className="px-3 py-2 text-left font-semibold whitespace-nowrap">
              {game.awayTeam} @ {game.homeTeam}
            </th>
            <PickCell pick={picksByGame.get(game.id)} game={game} />
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function PicksTable({ data }: { data: AllPicks }) {
  const columns: Record<string, SortColumn<MemberPicks>> = {
    member: { value: (member) => member.displayName },
  }
  for (const game of data.games) {
    columns[game.id] = {
      value: (member) => member.picks.find((pick) => pick.gameId === game.id)?.confidence ?? null,
      numeric: true,
    }
  }
  const sort = useTableSort(data.members, columns)

  return (
    <table
      className={`w-full border-collapse text-sm ${data.games.length > 1 ? 'min-w-[640px]' : ''}`}
    >
      <thead>
        <tr className="bg-surface-muted dark:bg-night-card">
          <SortableTh
            label="Member"
            columnKey="member"
            sort={sort}
            className="sticky left-0 z-10 bg-surface-muted px-3 py-2 dark:bg-night-card"
          />
          {data.games.map((game) => (
            <SortableTh
              key={game.id}
              label={`${game.awayTeam} @ ${game.homeTeam}`}
              columnKey={game.id}
              sort={sort}
              align="center"
              className="px-3 py-2 whitespace-nowrap"
            />
          ))}
        </tr>
      </thead>
      <tbody>
        {sort.sortedRows.map((member) => {
          const picksByGame = new Map(member.picks.map((pick) => [pick.gameId, pick]))
          return (
            <tr key={member.userId} className="border-t border-slate-200 dark:border-night-line">
              <td className="sticky left-0 z-10 bg-surface px-3 py-2 font-semibold whitespace-nowrap dark:bg-night-card">
                {member.displayName}
              </td>
              {data.games.map((game) => {
                return <PickCell key={game.id} pick={picksByGame.get(game.id)} game={game} />
              })}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

/** All members, with a game filter: one game at a time fits a phone without sideways scrolling. */
function EveryonePicks({ data }: { data: AllPicks }) {
  const [gameId, setGameId] = useState('all')
  const games = gameId === 'all' ? data.games : data.games.filter((game) => game.id === gameId)
  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm font-bold text-ink-muted dark:text-night-text">
        Show game
        <select
          value={gameId}
          onChange={(event) => setGameId(event.target.value)}
          className="min-h-11 rounded-xl border border-slate-300 bg-surface px-3 text-ink dark:border-night-line-strong dark:bg-night-card dark:text-night-ink-soft"
        >
          <option value="all">All games</option>
          {data.games.map((game) => (
            <option key={game.id} value={game.id}>
              {game.awayTeam} @ {game.homeTeam}
            </option>
          ))}
        </select>
      </label>
      <PicksTable key={gameId} data={{ ...data, games }} />
    </div>
  )
}

/** Pass `member` to show just that member's picks (the leaderboard's per-member popup). */
export function AllPicksModal({
  week,
  member,
  onClose,
}: {
  week: number
  member?: { id: string; name: string }
  onClose: () => void
}) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const { data, isPending, error } = useQuery({
    queryKey: ['picks', 'all', week],
    queryFn: () => fetchAllPicksForWeek(week),
    staleTime: 60_000,
    // Keep green/red in step with game results until every game is settled.
    refetchInterval: (query) =>
      query.state.data && allGamesSettled(query.state.data.games) ? false : 60_000,
    retry: false,
  })
  const shown =
    data && member ? { ...data, members: data.members.filter((m) => m.userId === member.id) } : data

  useEffect(() => {
    closeRef.current?.focus()
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="all-picks-title"
        onClick={(event) => event.stopPropagation()}
        className={`w-full ${member ? 'max-w-md' : 'max-w-4xl'} rounded-2xl border border-slate-200 bg-surface p-5 shadow-lg dark:border-night-line dark:bg-night-card`}
      >
        <div className="flex items-center justify-between gap-3">
          <h2 id="all-picks-title" className="text-lg font-black text-primary dark:text-night-ink">
            {member ? `${member.name}'s picks` : "Everyone's picks"} — Week {week}
          </h2>
          <Button ref={closeRef} type="button" variant="quiet" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="mt-4 max-h-[70vh] overflow-auto">
          {isPending && (
            <p className="text-sm text-ink-muted dark:text-night-muted">
              {member ? 'Loading picks…' : 'Loading everyone’s picks…'}
            </p>
          )}
          {error && (
            <p className="text-sm text-danger">
              {error instanceof ApiError
                ? error.message
                : member
                  ? 'Could not load picks.'
                  : "Could not load everyone's picks."}
            </p>
          )}
          {shown && (member ? <MemberPicksTable data={shown} /> : <EveryonePicks data={shown} />)}
        </div>
      </div>
    </div>
  )
}
