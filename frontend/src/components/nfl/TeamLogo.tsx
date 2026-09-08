import { useState } from 'react'
import type { CSSProperties, ImgHTMLAttributes } from 'react'
import { getTeamLogoConfig, getTeamName } from '../../assets/teamLogos'
import { getTeamPalette } from './teamPalette'

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
