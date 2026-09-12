import { ChevronDown } from 'lucide-react'
import type { ReactNode } from 'react'

interface AccordionSectionProps {
  id: string
  title: string
  summary: string
  isOpen: boolean
  onToggle: () => void
  children: ReactNode
}

export function AccordionSection({
  id,
  title,
  summary,
  isOpen,
  onToggle,
  children,
}: AccordionSectionProps) {
  const headingId = `${id}-heading`
  const bodyId = `${id}-body`

  return (
    <section
      id={`section-${id}`}
      className="overflow-hidden rounded-2xl border border-slate-200 bg-surface shadow-sm dark:border-slate-800 dark:bg-slate-900"
      aria-labelledby={headingId}
    >
      <h2 id={headingId}>
        <button
          type="button"
          aria-controls={bodyId}
          aria-expanded={isOpen}
          onClick={onToggle}
          className="flex min-h-20 w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-surface-muted/60 dark:hover:bg-slate-950/60"
        >
          <span className="min-w-0">
            <span className="block text-lg font-black text-primary dark:text-white">{title}</span>
            <span className="mt-1 block truncate text-sm text-ink-muted dark:text-slate-400">
              {summary}
            </span>
          </span>
          <ChevronDown
            size={22}
            aria-hidden="true"
            className={`shrink-0 text-ink-muted transition-transform dark:text-slate-400 ${isOpen ? 'rotate-180' : ''}`}
          />
        </button>
      </h2>
      {isOpen && (
        <div
          id={bodyId}
          role="region"
          aria-labelledby={headingId}
          className="border-t border-slate-200 p-4 dark:border-slate-800 sm:p-5"
        >
          {children}
        </div>
      )}
    </section>
  )
}
