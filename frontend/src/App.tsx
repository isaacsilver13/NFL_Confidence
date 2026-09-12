import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './features/auth/ProtectedRoute'
import { AppLayout } from './layouts/AppLayout'
import { LoginPage } from './pages/LoginPage'

// Lazy-loaded pages for code splitting
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const JoinLeaguePage = lazy(() =>
  import('./pages/JoinLeaguePage').then((m) => ({ default: m.JoinLeaguePage })),
)
const LeagueSettingsPage = lazy(() =>
  import('./pages/LeagueSettingsPage').then((m) => ({ default: m.LeagueSettingsPage })),
)

function PageLoader() {
  return null // Show nothing while loading; page will render when ready
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
          <Route path="/picks" element={<Navigate to="/#picks" replace />} />
          <Route path="/leaderboard" element={<Navigate to="/#leaderboard" replace />} />
          <Route path="/standings" element={<Navigate to="/#standings" replace />} />
          <Route path="/profile" element={<Navigate to="/#profile" replace />} />
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
