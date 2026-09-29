import { useEffect, useState, type ReactNode } from 'react'
import { ThemeContext, type Theme } from './ThemeContext'

// Keep this key in sync with the inline bootstrap script in index.html, which
// cannot import this constant since it must run before any module loads.
export const THEME_STORAGE_KEY = 'nfl-confidence:theme'

function readInitialTheme(): Theme {
  // Anything other than an explicit stored 'light' (missing key, null, or any
  // other value) defaults to dark.
  return localStorage.getItem(THEME_STORAGE_KEY) === 'light' ? 'light' : 'dark'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readInitialTheme)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  useEffect(() => {
    // Deployed dev builds get this class from index.html's %VITE_APP_ENV%
    // interpolation before this module even loads; local `npm run dev` has no
    // VITE_APP_ENV set there, so apply it here via Vite's dev-server flag.
    if (import.meta.env.DEV) {
      document.documentElement.classList.add('dev-theme')
    }
  }, [])

  function toggleTheme() {
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark'
      localStorage.setItem(THEME_STORAGE_KEY, next)
      return next
    })
  }

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>
}
