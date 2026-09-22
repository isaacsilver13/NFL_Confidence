import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ThemeContext, useTheme } from './ThemeContext'

function ThemeProbe() {
  const { theme } = useTheme()
  return <output>{theme}</output>
}

function ThrowingProbe() {
  useTheme()
  return null
}

describe('ThemeContext', () => {
  it('exposes a context object and a useTheme hook', () => {
    expect(ThemeContext).toBeDefined()
    expect(useTheme).toBeInstanceOf(Function)
  })

  it('throws when useTheme is called outside a ThemeProvider', () => {
    // Swallow the expected React error boundary console output for this render.
    expect(() => render(<ThrowingProbe />)).toThrow('useTheme must be used within a ThemeProvider')
  })

  it('returns the provided value when rendered within a ThemeContext.Provider', () => {
    render(
      <ThemeContext.Provider value={{ theme: 'light', toggleTheme: () => {} }}>
        <ThemeProbe />
      </ThemeContext.Provider>,
    )

    expect(screen.getByText('light')).toBeInTheDocument()
  })
})
