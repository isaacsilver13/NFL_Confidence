export interface League {
  id: string
  name: string
  season: number
  memberCount: number
  commissionerName: string
  inviteCode: string
  isActive: boolean
}

export interface LeagueMember {
  id: string
  userId: string
  displayName: string
  email: string
  avatarUrl: string | null
  role: 'owner' | 'member'
  joinedAt: string
}

export interface Invite {
  id: string
  email: string
  expiresAt: string
}

export interface CreateLeagueInput {
  name: string
  season: number
}
