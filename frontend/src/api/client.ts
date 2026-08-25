/**
 * Thin fetch wrapper around the backend's `/api/v1` JSON envelope
 * ({"data": ..., "message": ...} / {"error": {"code", "message", "details"}}).
 *
 * The access token is kept in memory only (never localStorage, to limit XSS blast
 * radius) and attached as a Bearer header. The refresh token lives in an httpOnly
 * cookie the browser sends automatically (`credentials: 'include'`); on a 401 this
 * client transparently calls POST /auth/refresh once and retries the original request.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL

interface ApiSuccessBody<T> {
  data: T
  message: string | null
}

interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: unknown[]
  }
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown[]

  constructor(status: number, code: string, message: string, details: unknown[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

interface ApiFetchOptions extends RequestInit {
  /** Internal flag to prevent infinite refresh-retry loops. */
  skipAuthRetry?: boolean
}

async function parseResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null)

  if (!response.ok) {
    const errorBody = body as ApiErrorBody | null
    throw new ApiError(
      response.status,
      errorBody?.error?.code ?? 'UNKNOWN_ERROR',
      errorBody?.error?.message ?? response.statusText,
      errorBody?.error?.details ?? [],
    )
  }

  return (body as ApiSuccessBody<T>).data
}

let refreshInFlight: Promise<boolean> | null = null

async function refreshAccessToken(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      })
      if (!response.ok) {
        setAccessToken(null)
        return false
      }
      const body = (await response.json()) as ApiSuccessBody<{ accessToken: string }>
      setAccessToken(body.data.accessToken)
      return true
    } catch {
      setAccessToken(null)
      return false
    } finally {
      refreshInFlight = null
    }
  })()
  return refreshInFlight
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { skipAuthRetry, headers, ...rest } = options

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
  })

  if (response.status === 401 && !skipAuthRetry) {
    const refreshed = await refreshAccessToken()
    if (refreshed) {
      return apiFetch<T>(path, { ...options, skipAuthRetry: true })
    }
  }

  return parseResponse<T>(response)
}
