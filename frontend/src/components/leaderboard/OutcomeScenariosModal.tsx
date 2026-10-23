import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import { fetchWeeklyOutcomeScenarios } from '@/api/leaderboard'
import { Button } from '@/components/ui/Button'
import type { OutcomeScenario, OutcomeScenarios } from '@/types/leaderboard'

function placeNames(names: string[]): string {
  return names.length > 0 ? names.join(', ') : '—'
}

function gameLabel(game: OutcomeScenarios['sundayGame']): string {
  return `${game.awayTeam} @ ${game.homeTeam}`
}

function ScenariosTable({ data }: { data: OutcomeScenarios }) {
  return (
    <table className="w-full min-w-[760px] text-left text-sm">
      <caption className="sr-only">Possible first, second, and third place finishes</caption>
      <thead className="bg-surface-muted text-xs uppercase tracking-[0.14em] text-ink-muted dark:bg-slate-950 dev-dark:bg-background dark:text-slate-400 dev-dark:text-text-muted">
        <tr>
          <th scope="col" className="px-4 py-3 font-bold">
            Sunday night winner
          </th>
          <th scope="col" className="px-4 py-3 font-bold">
            Monday night winner
          </th>
          <th scope="col" className="px-4 py-3 font-bold">
            1st
          </th>
          <th scope="col" className="px-4 py-3 font-bold">
            2nd
          </th>
          <th scope="col" className="px-4 py-3 font-bold">
            3rd
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-200 dark:divide-slate-800 dev-dark:divide-border">
        {data.scenarios.map((scenario: OutcomeScenario) => (
          <tr key={`${scenario.sundayWinner}-${scenario.mondayWinner}`}>
            <td className="px-4 py-3 font-semibold">{scenario.sundayWinner} wins</td>
            <td className="px-4 py-3 font-semibold">{scenario.mondayWinner} wins</td>
            <td className="px-4 py-3">{placeNames(scenario.firstPlace)}</td>
            <td className="px-4 py-3">{placeNames(scenario.secondPlace)}</td>
            <td className="px-4 py-3">{placeNames(scenario.thirdPlace)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function OutcomeScenariosModal({ week, onClose }: { week: number; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const { data, isPending, error } = useQuery({
    queryKey: ['leaderboard', 'outcome-scenarios', week],
    queryFn: () => fetchWeeklyOutcomeScenarios(week),
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
        aria-labelledby="outcome-scenarios-title"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-5xl rounded-2xl border border-slate-200 bg-surface p-5 shadow-lg dark:border-slate-800 dev-dark:border-border dark:bg-slate-900 dev-dark:bg-surface-elevated"
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2
              id="outcome-scenarios-title"
              className="text-lg font-black text-primary dark:text-white dev-dark:text-ink"
            >
              Possible finishes — Week {week}
            </h2>
            {data && (
              <p className="mt-1 text-sm text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
                {gameLabel(data.sundayGame)} and {gameLabel(data.mondayGame)}
              </p>
            )}
          </div>
          <Button ref={closeRef} type="button" variant="quiet" onClick={onClose}>
            Close
          </Button>
        </div>
        <div className="mt-4 max-h-[70vh] overflow-auto">
          {isPending && (
            <p className="text-sm text-ink-muted dark:text-slate-400 dev-dark:text-text-muted">
              Calculating possible finishes…
            </p>
          )}
          {error && (
            <p className="text-sm text-danger">
              {error instanceof ApiError ? error.message : 'Could not calculate possible finishes.'}
            </p>
          )}
          {data && <ScenariosTable data={data} />}
        </div>
      </div>
    </div>
  )
}
