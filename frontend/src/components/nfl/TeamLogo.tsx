import { useState } from 'react'
import type { CSSProperties, ImgHTMLAttributes } from 'react'
import { getTeamLogoConfig, getTeamName } from '../../assets/teamLogos'

/**
 * Team color palettes for fallback badge rendering.
 * Used when logo image fails to load.
 */
export interface TeamPalette {
  background: string
  foreground: string
}

const TEAM_PALETTES: Record<string, TeamPalette> = {
  // AFC East
  BAL: { background: '#241773', foreground: '#ffffff' },
  BUF: { background: '#c60c30', foreground: '#ffffff' },
  MIA: { background: '#008d97', foreground: '#ffffff' },
  NE: { background: '#002244', foreground: '#ffffff' },
  // AFC Central
  CIN: { background: '#fb4f14', foreground: '#111827' },
  CLE: { background: '#311c1c', foreground: '#ff3c00' },
  PIT: { background: '#27251f', foreground: '#fdb827' },
  HOU: { background: '#eb6e1f', foreground: '#003831' },
  // AFC West
  DEN: { background: '#002244', foreground: '#fb4f14' },
  KC: { background: '#e31837', foreground: '#ffffff' },
  LAC: { background: '#0080c6', foreground: '#ffc52f' },
  LV: { background: '#000000', foreground: '#a5a5a5' },
  // AFC South
  IND: { background: '#002c5f', foreground: '#a2aaad' },
  JAX: { background: '#006687', foreground: '#000000' },
  TB: { background: '#092c5f', foreground: '#d50a0a' },
  TEN: { background: '#0c2c56', foreground: '#a2aaad' },
  // NFC East
  DAL: { background: '#003594', foreground: '#ffffff' },
  PHI: { background: '#004c54', foreground: '#ffffff' },
  WAS: { background: '#5a1f1a', foreground: '#ffc52f' },
  NYG: { background: '#0b2265', foreground: '#a71930' },
  // NFC Central
  CHI: { background: '#c83803', foreground: '#ffffff' },
  DET: { background: '#0076b6', foreground: '#b0b7bc' },
  GB: { background: '#203731', foreground: '#ffb612' },
  MIN: { background: '#4f2683', foreground: '#ffc52f' },
  // NFC West
  ARI: { background: '#97233f', foreground: '#ffb612' },
  LAR: { background: '#003831', foreground: '#b0b7bc' },
  SF: { background: '#aa0000', foreground: '#ffffff' },
  SEA: { background: '#0c2c56', foreground: '#69be28' },
}

const FALLBACK_PALETTE: TeamPalette = { background: '#526777', foreground: '#ffffff' }

export function getTeamPalette(code: string): TeamPalette {
  return TEAM_PALETTES[code.trim().toUpperCase()] ?? FALLBACK_PALETTE
}

interface TeamLogoProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'alt'> {
  /** ESPN team abbreviation (e.g., 'KC', 'SF') */
  code: string
  /** Optional custom image source (overrides default manifest path) */
  imageSrc?: string
  /** Hide the logo from assistive technology when nearby text names the team */
  decorative?: boolean
  /** Size variant for the logo */
  size?: 'sm' | 'md' | 'lg'
}

const sizeClasses = {
  sm: 'h-8 w-8 text-[0.65rem]',
  md: 'h-11 w-11 text-xs',
  lg: 'h-14 w-14 text-sm',
}

const imageSizePixels = {
  sm: 32,
  md: 44,
  lg: 56,
}

/**
 * TeamLogo component with image-first rendering and badge fallback.
 *
 * Attempts to load the team logo image from the local manifest or custom source.
 * If the image fails to load, gracefully falls back to a colored badge with the
 * team abbreviation. This ensures the UI remains functional regardless of asset
 * availability.
 *
 * Features:
 * - Loads images with lazy loading and async decoding
 * - Provides accessible alt text with full team name
 * - Falls back to abbreviation badge on image error
 * - Uses optimized image delivery attributes
 *
 * @param code - ESPN team abbreviation (case-insensitive)
 * @param imageSrc - Optional custom image URL (overrides manifest)
 * @param size - Size variant: 'sm' (32px), 'md' (44px), 'lg' (56px)
 */
export function TeamLogo({
  code,
  imageSrc,
  decorative = false,
  size = 'md',
  ...imgProps
}: TeamLogoProps) {
  const normalizedCode = code.trim().toUpperCase()
  const teamConfig = getTeamLogoConfig(normalizedCode)
  const teamName = getTeamName(normalizedCode)
  const palette = getTeamPalette(normalizedCode)
  const pixelSize = imageSizePixels[size]

  // Determine image source: custom override, manifest, or undefined
  const logoSrc = imageSrc || teamConfig?.logoPath

  const [imageError, setImageError] = useState(false)

  // If we successfully loaded an image, render it
  if (logoSrc && !imageError) {
    return (
      <img
        src={logoSrc}
        alt={decorative ? '' : teamName}
        width={pixelSize}
        height={pixelSize}
        loading="lazy"
        decoding="async"
        onError={() => setImageError(true)}
        className={`inline-block shrink-0 rounded-full border-2 border-white/70 shadow-sm ${sizeClasses[size]}`}
        {...imgProps}
      />
    )
  }

  // Fallback to abbreviation badge if image didn't load
  const style = {
    '--team-background': palette.background,
    '--team-foreground': palette.foreground,
  } as CSSProperties

  return (
    <span
      aria-label={teamName}
      aria-hidden={decorative}
      className={`inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-white/70 bg-[var(--team-background)] font-bold tracking-wide text-[var(--team-foreground)] shadow-sm ${sizeClasses[size]}`}
      style={style}
    >
      {normalizedCode || '?'}
    </span>
  )
}
