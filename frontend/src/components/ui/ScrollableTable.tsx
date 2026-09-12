import type { ReactNode } from 'react'

/**
 * Wraps a wide table in a horizontally-scrolling container with a persistent
 * fade on the trailing edge, hinting that there's more content to swipe to
 * on narrow screens (the plain `overflow-x-auto` alone gives no visual cue).
 */
export function ScrollableTable({ children }: { children: ReactNode }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-surface shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="overflow-x-auto">{children}</div>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-surface to-transparent dark:from-slate-900"
      />
    </div>
  )
}
