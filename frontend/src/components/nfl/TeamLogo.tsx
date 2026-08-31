import type { CSSProperties } from 'react'

export interface TeamPalette {
  background: string
  foreground: string
}

const TEAM_PALETTES: Record<string, TeamPalette> = {
  BAL: { background: '#241773', foreground: '#ffffff' },
  BUF: { background: '#c60c30', foreground: '#ffffff' },
  CHI: { background: '#c83803', foreground: '#ffffff' },
  CIN: { background: '#fb4f14', foreground: '#111827' },
  DAL: { background: '#003594', foreground: '#ffffff' },
  GB: { background: '#203731', foreground: '#ffb612' },
  KC: { background: '#e31837', foreground: '#ffffff' },
  PHI: { background: '#004c54', foreground: '#ffffff' },
  SF: { background: '#aa0000', foreground: '#ffffff' },
  SEA: { background: '#69be28', foreground: '#102a43' },
}

const FALLBACK_PALETTE: TeamPalette = { background: '#526777', foreground: '#ffffff' }

export function getTeamPalette(code: string): TeamPalette {
  return TEAM_PALETTES[code.trim().toUpperCase()] ?? FALLBACK_PALETTE
}

interface TeamLogoProps {
  code: string
  imageSrc?: string
  size?: 'sm' | 'md' | 'lg'
}

const sizes = {
  sm: 'h-8 w-8 text-[0.65rem]',
  md: 'h-11 w-11 text-xs',
  lg: 'h-14 w-14 text-sm',
}

export function TeamLogo({ code, imageSrc, size = 'md' }: TeamLogoProps) {
  const normalizedCode = code.trim().toUpperCase()
  const palette = getTeamPalette(normalizedCode)
  const style = {
    '--team-background': palette.background,
    '--team-foreground': palette.foreground,
  } as CSSProperties

  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-white/70 bg-[var(--team-background)] font-bold tracking-wide text-[var(--team-foreground)] shadow-sm ${sizes[size]}`}
      style={style}
    >
      {imageSrc ? (
        <img src={imageSrc} alt="" className="h-full w-full object-contain" />
      ) : (
        normalizedCode || '?'
      )}
    </span>
  )
}
