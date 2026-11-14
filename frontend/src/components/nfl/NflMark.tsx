import { Shield } from 'lucide-react'

interface NflMarkProps {
  compact?: boolean
  /** Keeps only the shield icon below `sm`, for tight headers. */
  hideWordmarkOnPhone?: boolean
}

export function NflMark({ compact = false, hideWordmarkOnPhone = false }: NflMarkProps) {
  return (
    <span className="inline-flex items-center gap-2 text-primary dark:text-night-ink">
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-sky shadow-sm dark:bg-night-accent orange-trim dev-dark:text-white">
        <Shield size={20} strokeWidth={2.5} aria-hidden="true" />
      </span>
      {!compact && (
        <span className={`leading-tight${hideWordmarkOnPhone ? ' hidden sm:block' : ''}`}>
          <span className="block text-[0.65rem] font-bold uppercase tracking-[0.2em] text-sky dark:text-accent">
            NFL
          </span>
          <span className="block text-sm font-black tracking-tight">Confidence</span>
        </span>
      )}
    </span>
  )
}
