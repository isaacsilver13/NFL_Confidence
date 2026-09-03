import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TeamLogo } from './TeamLogo'
import {
  TEAM_LOGOS,
  ALL_TEAM_CODES,
  getTeamLogoConfig,
  getTeamName,
  isValidTeamCode,
} from '../../assets/teamLogos'

describe('Team Logo Manifest', () => {
  // Verify all 32 NFL teams are configured
  const EXPECTED_TEAM_COUNT = 32
  const EXPECTED_TEAMS = [
    // AFC East
    'BUF',
    'MIA',
    'NE',
    'NYJ',
    // AFC North
    'BAL',
    'CIN',
    'CLE',
    'PIT',
    // AFC South
    'HOU',
    'IND',
    'JAX',
    'TEN',
    // AFC West
    'DEN',
    'KC',
    'LAC',
    'LV',
    // NFC East
    'DAL',
    'NYG',
    'PHI',
    'WAS',
    // NFC North
    'CHI',
    'DET',
    'GB',
    'MIN',
    // NFC South
    'ATL',
    'CAR',
    'NO',
    'TB',
    // NFC West
    'ARI',
    'LAR',
    'SF',
    'SEA',
  ]

  it('should have exactly 32 teams', () => {
    expect(Object.keys(TEAM_LOGOS)).toHaveLength(EXPECTED_TEAM_COUNT)
  })

  it('should include all expected NFL teams', () => {
    EXPECTED_TEAMS.forEach((code) => {
      expect(TEAM_LOGOS).toHaveProperty(code)
      expect(TEAM_LOGOS[code as keyof typeof TEAM_LOGOS]).toBeDefined()
    })
  })

  it('should have valid configuration for each team', () => {
    Object.entries(TEAM_LOGOS).forEach(([code, config]) => {
      expect(config.name).toBeTruthy()
      expect(config.espnCode).toBe(code)
      expect(config.logoPath).toMatch(/^\/logos\/[A-Z]+\.png$/)
    })
  })

  it('ALL_TEAM_CODES should match manifest', () => {
    expect(ALL_TEAM_CODES).toHaveLength(EXPECTED_TEAM_COUNT)
    expect(new Set(ALL_TEAM_CODES)).toEqual(new Set(Object.keys(TEAM_LOGOS)))
  })

  it('should handle case-insensitive lookups', () => {
    const config = getTeamLogoConfig('kc')
    expect(config).toBeDefined()
    expect(config?.espnCode).toBe('KC')
    expect(config?.name).toBe('Kansas City Chiefs')
  })

  it('should handle whitespace in lookups', () => {
    const config = getTeamLogoConfig('  SF  ')
    expect(config).toBeDefined()
    expect(config?.espnCode).toBe('SF')
  })

  it('should return undefined for invalid team codes', () => {
    expect(getTeamLogoConfig('XXX')).toBeUndefined()
    expect(getTeamLogoConfig('INVALID')).toBeUndefined()
  })

  it('should validate team codes correctly', () => {
    expect(isValidTeamCode('KC')).toBe(true)
    expect(isValidTeamCode('kc')).toBe(true)
    expect(isValidTeamCode('  SF  ')).toBe(true)
    expect(isValidTeamCode('XXX')).toBe(false)
    expect(isValidTeamCode('INVALID')).toBe(false)
  })

  it('should get team names for all codes', () => {
    EXPECTED_TEAMS.forEach((code) => {
      const name = getTeamName(code)
      expect(name).not.toBe(code) // Should be full name, not abbreviation
      expect(name.length).toBeGreaterThan(3)
    })
  })

  it('should return code as fallback for invalid teams', () => {
    expect(getTeamName('XXX')).toBe('XXX')
  })
})

describe('TeamLogo Component', () => {
  it('renders a known team with logo image from manifest', () => {
    render(<TeamLogo code="BUF" />)
    // Valid team codes load from manifest and render as images
    const image = screen.getByAltText('Buffalo Bills')
    expect(image).toBeInTheDocument()
    expect(image).toHaveAttribute('src', '/logos/BUF.png')
  })

  it('falls back cleanly for an unknown team code with badge', () => {
    render(<TeamLogo code="xyz" />)
    // Unknown codes render as badges with abbreviation text
    expect(screen.getByText('XYZ')).toBeInTheDocument()
    expect(screen.getByLabelText('XYZ')).toBeInTheDocument()
  })

  it('should render image with correct attributes when logo src is provided', () => {
    render(<TeamLogo code="SF" imageSrc="/logos/SF.png" />)
    const image = screen.getByAltText('San Francisco 49ers')
    expect(image).toBeInTheDocument()
    expect(image).toHaveAttribute('src', '/logos/SF.png')
    expect(image).toHaveAttribute('loading', 'lazy')
    expect(image).toHaveAttribute('decoding', 'async')
  })

  it('should render badge fallback for unknown team codes', () => {
    render(<TeamLogo code="XXX" />)
    const badge = screen.getByLabelText('XXX')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('XXX')
  })

  it('should handle case-insensitive team codes with logo', () => {
    render(<TeamLogo code="kc" />)
    const image = screen.getByAltText('Kansas City Chiefs')
    expect(image).toBeInTheDocument()
    expect(image).toHaveAttribute('src', '/logos/KC.png')
  })

  it('should handle whitespace in team codes with logo', () => {
    render(<TeamLogo code="  DAL  " />)
    const image = screen.getByAltText('Dallas Cowboys')
    expect(image).toBeInTheDocument()
    expect(image).toHaveAttribute('src', '/logos/DAL.png')
  })

  it('should support different size variants (sm)', () => {
    render(<TeamLogo code="BUF" size="sm" />)
    const img = screen.getByAltText('Buffalo Bills')
    expect(img).toHaveClass('h-8', 'w-8')
  })

  it('should support different size variants (md)', () => {
    render(<TeamLogo code="BUF" size="md" />)
    const img = screen.getByAltText('Buffalo Bills')
    expect(img).toHaveClass('h-11', 'w-11')
  })

  it('should support different size variants (lg)', () => {
    render(<TeamLogo code="BUF" size="lg" />)
    const img = screen.getByAltText('Buffalo Bills')
    expect(img).toHaveClass('h-14', 'w-14')
  })

  it('should maintain border and shadow styling on images', () => {
    render(<TeamLogo code="PHI" />)
    const element = screen.getByAltText('Philadelphia Eagles')
    expect(element).toHaveClass('border-2', 'border-white/70', 'shadow-sm', 'rounded-full')
  })

  it('should fall back to badge when image load fails', () => {
    const { rerender } = render(<TeamLogo code="BUF" imageSrc="/logos/BUF.png" />)

    // Initially shows image
    const img = screen.getByAltText('Buffalo Bills') as HTMLImageElement
    expect(img).toBeInTheDocument()

    // Simulate image load error
    fireEvent.error(img)

    // After error, badge should be visible
    rerender(<TeamLogo code="BUF" imageSrc="/logos/BUF.png" />)
    // After state update, badge should appear
    const badge = screen.getByText('BUF')
    expect(badge).toBeInTheDocument()
  })

  it('should accept additional HTML attributes for images', () => {
    render(
      <TeamLogo
        code="KC"
        imageSrc="/logos/KC.png"
        data-testid="custom-logo"
        title="Kansas City Chiefs Logo"
      />,
    )
    const img = screen.getByTestId('custom-logo')
    expect(img).toHaveAttribute('title', 'Kansas City Chiefs Logo')
  })
})
