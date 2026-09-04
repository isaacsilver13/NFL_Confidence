import { Suspense, lazy } from 'react'
import { LoaderCircle } from 'lucide-react'
import { Route, Routes } from 'react-router-dom'
import { LeagueMemberRoute, ProtectedRoute } from './features/auth/ProtectedRoute'
import { AppLayout } from './layouts/AppLayout'
import { LoginPage } from './pages/LoginPage'

// Lazy-loaded pages for code splitting
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const JoinLeaguePage = lazy(() =>
  import('./pages/JoinLeaguePage').then((m) => ({ default: m.JoinLeaguePage })),
)
const LeaderboardPage = lazy(() =>
  import('./pages/LeaderboardPage').then((m) => ({ default: m.LeaderboardPage })),
)
const LeagueSettingsPage = lazy(() =>
  import('./pages/LeagueSettingsPage').then((m) => ({ default: m.LeagueSettingsPage })),
)
const PicksPage = lazy(() => import('./pages/PicksPage').then((m) => ({ default: m.PicksPage })))
const ProfilePage = lazy(() =>
  import('./pages/ProfilePage').then((m) => ({ default: m.ProfilePage })),
)
const StandingsPage = lazy(() =>
  import('./pages/StandingsPage').then((m) => ({ default: m.StandingsPage })),
)

function PageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center" role="status">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink-muted dark:text-slate-400">
        <LoaderCircle className="h-5 w-5 animate-spin" aria-hidden="true" />
        Loading...
      </div>
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route
          path="/join"
          element={
            <Suspense fallback={<PageLoader />}>
              <JoinLeaguePage />
            </Suspense>
          }
        />
        <Route element={<AppLayout />}>
          <Route
            path="/"
            element={
              <Suspense fallback={<PageLoader />}>
                <DashboardPage />
              </Suspense>
            }
          />
          <Route element={<LeagueMemberRoute />}>
            <Route
              path="/picks"
              element={
                <Suspense fallback={<PageLoader />}>
                  <PicksPage />
                </Suspense>
              }
            />
            <Route
              path="/leaderboard"
              element={
                <Suspense fallback={<PageLoader />}>
                  <LeaderboardPage />
                </Suspense>
              }
            />
            <Route
              path="/standings"
              element={
                <Suspense fallback={<PageLoader />}>
                  <StandingsPage />
                </Suspense>
              }
            />
            <Route
              path="/profile"
              element={
                <Suspense fallback={<PageLoader />}>
                  <ProfilePage />
                </Suspense>
              }
            />
          </Route>
          <Route
            path="/members"
            element={
              <Suspense fallback={<PageLoader />}>
                <LeagueSettingsPage />
              </Suspense>
            }
          />
          <Route
            path="/league-settings"
            element={
              <Suspense fallback={<PageLoader />}>
                <LeagueSettingsPage />
              </Suspense>
            }
          />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
