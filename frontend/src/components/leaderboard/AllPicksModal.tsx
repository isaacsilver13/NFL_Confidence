import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { fetchAllPicksForWeek } from '@/api/nfl'
import type { AllPicks, MemberPicks } from '@/types/nfl'
import { Button } from '@/components/ui/Button'
import { SortableTh } from '@/components/ui/SortableTable'
import { useTableSort, type SortColumn } from '@/components/ui/useTableSort'

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
    <table className="w-full min-w-[640px] border-collapse text-sm">
      <thead>
        <tr className="bg-surface-muted dark:bg-slate-900 dev-dark:bg-surface-elevated">
          <SortableTh
            label="Member"
            columnKey="member"
            sort={sort}
            className="sticky left-0 z-10 bg-surface-muted px-3 py-2 dark:bg-slate-900 dev-dark:bg-surface-elevated"
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
            <tr
              key={member.userId}
              className="border-t border-slate-200 dark:border-slate-800 dev-dark:border-border"
            >
              <td className="sticky left-0 z-10 bg-surface px-3 py-2 font-semibold whitespace-nowrap dark:bg-slate-900 dev-dark:bg-surface-elevated">
                {member.displayName}
              </td>
              {data.games.map((game) => {
                const pick = picksByGame.get(game.id)
                return (
                  <td key={game.id} className="px-3 py-2 text-center whitespace-nowrap">
                    {pick ? `${pick.team} (${pick.confidence})` : '—'}
                  </td>
                )
              })}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export function AllPicksModal({ week, onClose }: { week: number; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const { data, isPending, error } = useQuery({
    queryKey: ['picks', 'all', week],
    queryFn: () => fetchAllPicksForWeek(week),
    staleTime: 60_000,
    retry: false,
  })

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
        className="w-full max-w-4xl rounded-2xl border border-slate-200 bg-surface p-5 shadow-lg dark:border-slate-800 dev-dark:border-border dark:bg-slate-900 dev-dark:bg-surface-elevated"
      >
        <div className="flex items-center justify-between gap-3">
          <h2
            id="all-picks-title"
            className="text-lg font-black text-primary dark:text-white dev-dark:text-ink"
          >
            Everyone&apos;s picks — Week {week}
          </h2>
          <Button ref={closeRef} type="button" variant="quiet" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="mt-4 max-h-[70vh] overflow-auto">
          {isPending && (
            <p className="text-sm text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
              Loading everyone&apos;s picks…
            </p>
          )}
          {error && (
            <p className="text-sm text-danger">
              {error instanceof ApiError ? error.message : "Could not load everyone's picks."}
            </p>
          )}
          {data && <PicksTable data={data} />}
        </div>
      </div>
    </div>
  )
}
