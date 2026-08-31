import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TeamLogo } from './TeamLogo'

describe('TeamLogo', () => {
  it('renders a known team abbreviation', () => {
    render(<TeamLogo code="BUF" />)
    expect(screen.getByText('BUF')).toBeInTheDocument()
  })

  it('falls back cleanly for an unknown team code', () => {
    render(<TeamLogo code="xyz" />)
    expect(screen.getByText('XYZ')).toBeInTheDocument()
  })
})
