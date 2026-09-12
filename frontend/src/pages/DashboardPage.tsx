import { lazy, Suspense, useEffect, useState } from 'react'
import { ArrowUpRight, CalendarDays, KeyRound, Users } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { createLeague, joinLeagueWithCode } from '@/api/league'
import { fetchCompletedWeeks, fetchPickHistory } from '@/api/nfl'
import { fetchWeeklyLeaderboard, fetchSeasonStandings } from '@/api/leaderboard'
import { fetchCurrentPicksCard, fetchSessionBootstrap } from '@/api/session'
import { Button } from '@/components/ui/Button'
import { AccordionSection } from '@/components/ui/AccordionSection'

const PicksPage = lazy(() =>
  import('./PicksPage').then((module) => ({ default: module.PicksPage })),
)
const LeaderboardPage = lazy(() =>
  import('./LeaderboardPage').then((module) => ({ default: module.LeaderboardPage })),
)
const StandingsPage = lazy(() =>
  import('./StandingsPage').then((module) => ({ default: module.StandingsPage })),
)
const ProfilePage = lazy(() =>
  import('./ProfilePage').then((module) => ({ default: module.ProfilePage })),
)

const SECTION_IDS = ['picks', 'leaderboard', 'standings', 'profile'] as const
type SectionId = (typeof SECTION_IDS)[number]
const OPEN_SECTIONS_STORAGE_PREFIX = 'nfl-confidence:open-sections:'

function sectionFromHash(): SectionId | null {
  const hash = window.location.hash.replace(/^#/, '')
  if (hash === 'profile-picks') return 'profile'
  return SECTION_IDS.includes(hash as SectionId) ? (hash as SectionId) : null
}

function initialOpenSections(userId: string): SectionId[] {
  let storedSections: SectionId[] = ['picks']
  try {
    const stored = window.localStorage.getItem(`${OPEN_SECTIONS_STORAGE_PREFIX}${userId}`)
    if (stored) {
      const parsed = JSON.parse(stored) as unknown
      if (Array.isArray(parsed)) {
        storedSections = parsed.filter((section): section is SectionId =>
          SECTION_IDS.includes(section as SectionId),
        )
      }
    }
  } catch {
    storedSections = ['picks']
  }
  const hashSection = sectionFromHash()
  return hashSection && !storedSections.includes(hashSection)
    ? [...storedSections, hashSection]
    : storedSections
}

function sectionSummary(value: string | undefined, fallback: string): string {
  return value ?? fallback
}

function DashboardSections({ userId }: { userId: string }) {
  const [openSections, setOpenSections] = useState<SectionId[]>(() => initialOpenSections(userId))
  const isOpen = (section: SectionId) => openSections.includes(section)

  useEffect(() => {
    try {
      window.localStorage.setItem(
        `${OPEN_SECTIONS_STORAGE_PREFIX}${userId}`,
        JSON.stringify(openSections),
      )
    } catch {
      return
    }
  }, [openSections, userId])

  useEffect(() => {
    function handleHashChange() {
      const section = sectionFromHash()
      if (section) {
        setOpenSections((current) => (current.includes(section) ? current : [...current, section]))
      }
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  function toggleSection(section: SectionId) {
    setOpenSections((current) => {
      const next = current.includes(section)
        ? current.filter((currentSection) => currentSection !== section)
        : [...current, section]
      const nextLocation = current.includes(section)
        ? `${window.location.pathname}${window.location.search}`
        : `${window.location.pathname}${window.location.search}#${section}`
      window.history.replaceState(null, '', nextLocation)
      return next
    })
  }

  const leaderboardWeeksQuery = useQuery({
    queryKey: ['leaderboard', 'weeks'],
    queryFn: fetchCompletedWeeks,
    enabled: isOpen('leaderboard'),
    staleTime: 10 * 60_000,
  })
  const latestCompletedWeek = leaderboardWeeksQuery.data?.at(-1)?.weekNumber
  const leaderboardQuery = useQuery({
    queryKey: ['leaderboard', 'week', latestCompletedWeek],
    queryFn: () => fetchWeeklyLeaderboard(latestCompletedWeek as number),
    enabled: isOpen('leaderboard') && latestCompletedWeek !== undefined,
    staleTime: 10 * 60_000,
  })
  const standingsQuery = useQuery({
    queryKey: ['leaderboard', 'season'],
    queryFn: () => fetchSeasonStandings(),
    enabled: isOpen('standings'),
    staleTime: 10 * 60_000,
  })
  const picksQuery = useQuery({
    queryKey: ['picks', 'card', 'current'],
    queryFn: fetchCurrentPicksCard,
    enabled: isOpen('picks') || isOpen('profile'),
    staleTime: 10_000,
  })
  const historyQuery = useQuery({
    queryKey: ['picks', 'history'],
    queryFn: fetchPickHistory,
    enabled: isOpen('profile'),
    staleTime: 10 * 60_000,
  })

  const weeklyMember = leaderboardQuery.data?.standings.find((member) => member.memberId === userId)
  const seasonMember = standingsQuery.data?.standings.find((member) => member.memberId === userId)
  const currentPickCount = picksQuery.data?.picks.filter((pick) => !pick.isVoided).length
  const currentGameCount = picksQuery.data?.games.length ?? 16
  const summaries: Record<SectionId, string> = {
    picks: sectionSummary(
      picksQuery.data
        ? `${currentPickCount ?? 0} of ${currentGameCount} picked this week`
        : undefined,
      "Make this week's picks",
    ),
    leaderboard: sectionSummary(
      weeklyMember ? `Your current rank is #${weeklyMember.rank}` : undefined,
      'See the weekly race and your current rank',
    ),
    standings: sectionSummary(
      seasonMember
        ? `Your season pick record is ${seasonMember.correctPicks}-${seasonMember.incorrectPicks}`
        : undefined,
      'See your season record and league standings',
    ),
    profile: sectionSummary(
      picksQuery.data
        ? `${currentPickCount ?? 0} of ${currentGameCount} picked this week`
        : historyQuery.data?.weeks.at(-1)
          ? `Last reviewed: Week ${historyQuery.data.weeks.at(-1)?.weekNumber}`
          : undefined,
      'Review your current and completed-week picks',
    ),
  }

  const sectionContent: Record<SectionId, React.ReactNode> = {
    picks: <PicksPage />,
    leaderboard: <LeaderboardPage />,
    standings: <StandingsPage />,
    profile: <ProfilePage />,
  }
  const sectionTitles: Record<SectionId, string> = {
    picks: 'Picks',
    leaderboard: 'Leaderboard',
    standings: 'Standings',
    profile: 'Profile Picks',
  }

  return (
    <div className="space-y-4" aria-label="League sections">
      {SECTION_IDS.map((section) => (
        <AccordionSection
          key={section}
          id={section}
          title={sectionTitles[section]}
          summary={summaries[section]}
          isOpen={isOpen(section)}
          onToggle={() => toggleSection(section)}
        >
          <Suspense
            fallback={
              <p className="text-slate-600 dark:text-slate-300" aria-live="polite">
                Loading {sectionTitles[section].toLowerCase()}...
              </p>
            }
          >
            {sectionContent[section]}
          </Suspense>
        </AccordionSection>
      ))}
    </div>
  )
}

const CURRENT_SEASON = new Date().getFullYear()

function CreateLeagueForm() {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [season, setSeason] = useState(CURRENT_SEASON)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await createLeague({ name: name.trim(), season })
      await queryClient.invalidateQueries({ queryKey: ['session', 'bootstrap'] })
    } catch {
      setError('Could not create the league. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="max-w-sm space-y-4">
      <div>
        <label htmlFor="league-name" className="mb-1 block text-sm font-medium">
          League name
        </label>
        <input
          id="league-name"
          type="text"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="min-h-11 w-full rounded-md border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <div>
        <label htmlFor="league-season" className="mb-1 block text-sm font-medium">
          Season
        </label>
        <input
          id="league-season"
          type="number"
          required
          value={season}
          onChange={(event) => setSeason(Number(event.target.value))}
          className="min-h-11 w-full rounded-md border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <Button type="submit" disabled={isSubmitting} fullWidth>
        {isSubmitting ? 'Creating…' : 'Create league'}
      </Button>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}

function JoinLeagueForm() {
  const queryClient = useQueryClient()
  const [code, setCode] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await joinLeagueWithCode(code.trim())
      await queryClient.invalidateQueries({ queryKey: ['session', 'bootstrap'] })
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setError('You are already a member of this league.')
      } else if (error instanceof ApiError && error.status === 422) {
        setError('That league passcode is invalid. Please check it and try again.')
      } else {
        setError('Could not join the league. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="max-w-sm space-y-4">
      <div>
        <label htmlFor="league-passcode" className="mb-1 block text-sm font-medium">
          League passcode
        </label>
        <input
          id="league-passcode"
          type="text"
          required
          value={code}
          onChange={(event) => setCode(event.target.value)}
          className="min-h-11 w-full rounded-md border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
        />
      </div>
      <Button type="submit" disabled={isSubmitting} fullWidth>
        <KeyRound size={16} aria-hidden="true" />
        {isSubmitting ? 'Joining…' : 'Join league'}
      </Button>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </form>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const {
    data: bootstrapData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['session', 'bootstrap'],
    queryFn: fetchSessionBootstrap,
    retry: false,
    staleTime: 5 * 60_000,
  })

  const league = bootstrapData?.league ?? null
  const currentWeek = bootstrapData?.currentWeek ?? null
  const user = bootstrapData?.user

  if (isLoading) {
    return null
  }

  if (
    (error instanceof ApiError && error.status === 404) ||
    bootstrapData?.membership.status === 'no_league'
  ) {
    return (
      <div className="animate-fade-in space-y-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">
            Your season starts here
          </p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white">
            Welcome to the pool.
          </h1>
        </div>
        <p className="text-slate-600 dark:text-slate-300">
          No league has been created yet. Create one to get started.
        </p>
        <div className="max-w-md rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <CreateLeagueForm />
        </div>
      </div>
    )
  }

  if (!league) {
    return (
      <div className="animate-fade-in space-y-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">League access</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white">
            Join your pool.
          </h1>
        </div>
        <p className="text-slate-600 dark:text-slate-300">
          You are signed in, but you are not a member yet. Ask the commissioner for the league
          passcode to join.
        </p>
        <div className="max-w-md rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <JoinLeagueForm />
        </div>
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">League hub</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-primary dark:text-white">
            Dashboard
          </h1>
        </div>
        <Button variant="secondary" onClick={() => void navigate('/#picks')}>
          Make picks <ArrowUpRight size={16} aria-hidden="true" />
        </Button>
      </div>
      {league && (
        <div className="overflow-hidden rounded-2xl border border-primary/10 bg-primary p-5 text-white shadow-lg shadow-primary/15">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky">
            {league.season} season
          </p>
          <p className="mt-2 text-2xl font-black">{league.name}</p>
          <div className="mt-5 flex flex-wrap gap-3 text-sm text-slate-200">
            <span className="inline-flex items-center gap-2">
              <Users size={16} aria-hidden="true" /> {league.memberCount} member
              {league.memberCount === 1 ? '' : 's'}
            </span>
            <span className="inline-flex items-center gap-2">
              <CalendarDays size={16} aria-hidden="true" /> Commissioner {league.commissionerName}
            </span>
          </div>
        </div>
      )}
      <div className="rounded-2xl border border-slate-200 bg-surface p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-muted dark:text-slate-400">
          Current week
        </p>
        <p className="mt-2 text-2xl font-black text-primary dark:text-white">
          {currentWeek ? `Week ${currentWeek.weekNumber}` : 'Unavailable'}
        </p>
      </div>
      <DashboardSections userId={user.id} />
    </div>
  )
}
