import type { TokenResponse, User } from '@/types/auth'
import { apiFetch, setAccessToken } from './client'

const API_BASE_URL = import.meta.env.VITE_API_URL

/** Full-page navigation target for "Continue with Google" (not a fetch call). */
export function googleLoginUrl(): string {
  return `${API_BASE_URL}/auth/google/login`
}

/** Local-only login bypass; the backend rejects this outside local dev. */
export async function devLogin(): Promise<TokenResponse> {
  const data = await apiFetch<TokenResponse>('/auth/dev-login', { method: 'POST' })
  setAccessToken(data.accessToken)
  return data
}

export async function fetchCurrentUser(): Promise<User> {
  return apiFetch<User>('/auth/me')
}

export async function logout(): Promise<void> {
  await apiFetch<null>('/auth/logout', { method: 'POST' })
  setAccessToken(null)
}
