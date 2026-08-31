import { Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './features/auth/ProtectedRoute'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { JoinLeaguePage } from './pages/JoinLeaguePage'
import { LeaderboardPage } from './pages/LeaderboardPage'
import { LeagueSettingsPage } from './pages/LeagueSettingsPage'
import { LoginPage } from './pages/LoginPage'
import { PicksPage } from './pages/PicksPage'
import { ProfilePage } from './pages/ProfilePage'
import { StandingsPage } from './pages/StandingsPage'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/join" element={<JoinLeaguePage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/picks" element={<PicksPage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/standings" element={<StandingsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/league-settings" element={<LeagueSettingsPage />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
