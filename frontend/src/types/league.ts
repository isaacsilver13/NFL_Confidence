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

export interface LeagueMemberUpdateInput {
  displayName?: string
  role?: LeagueMember['role']
}

export interface MemberPaymentStatus {
  userId: string
  displayName: string
  email: string
  role: LeagueMember['role']
  isPaid: boolean
  markedAt: string | null
  voidedPickCount: number
}

export interface MemberPaymentStatuses {
  week: number
  members: MemberPaymentStatus[]
}

export interface VoidUnpaidPicksResult {
  week: number
  voidedPickCount: number
  affectedMemberCount: number
}
