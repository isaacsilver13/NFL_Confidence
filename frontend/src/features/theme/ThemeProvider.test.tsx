import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider, THEME_STORAGE_KEY } from './ThemeProvider'
import { useTheme } from './ThemeContext'

function ThemeProbe() {
  const { theme, toggleTheme } = useTheme()
  return (
    <div>
      <output>{theme}</output>
      <button onClick={toggleTheme}>toggle</button>
    </div>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    // jsdom's localStorage and document.documentElement persist across tests
    // within this file, so reset both before every test.
    localStorage.clear()
    document.documentElement.className = ''
  })

  it('defaults to dark and adds the dark class when localStorage is empty', () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    expect(screen.getByText('dark')).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it("respects a stored 'light' value and does not add the class", () => {
    localStorage.setItem(THEME_STORAGE_KEY, 'light')

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    expect(screen.getByText('light')).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('flips the theme, toggles the class, and persists the new value on toggleTheme', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    expect(screen.getByText('dark')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'toggle' }))

    expect(screen.getByText('light')).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('light')

    await user.click(screen.getByRole('button', { name: 'toggle' }))

    expect(screen.getByText('dark')).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
  })
})
