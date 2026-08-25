export interface User {
  id: string
  displayName: string
  email: string
  avatarUrl: string | null
}

export interface AccessTokenResponse {
  accessToken: string
  tokenType: string
  expiresIn: number
}

export interface TokenResponse extends AccessTokenResponse {
  user: User
}
