import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import type { TableSort } from './useTableSort'

export function SortableTh({
  label,
  columnKey,
  sort,
  align = 'left',
  className = 'px-5 py-4',
  hideIconOnPhone = false,
}: {
  label: string
  columnKey: string
  sort: TableSort
  align?: 'left' | 'right' | 'center'
  className?: string
  /** Drops the sort arrow below `sm` so a narrow column's header fits its content. */
  hideIconOnPhone?: boolean
}) {
  const isActive = sort.sortKey === columnKey
  const Icon = isActive ? (sort.direction === 'ascending' ? ArrowUp : ArrowDown) : ArrowUpDown
  const alignClass = align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : ''
  return (
    <th className={`${className} ${alignClass}`} aria-sort={isActive ? sort.direction : 'none'}>
      <button
        type="button"
        onClick={() => sort.requestSort(columnKey)}
        aria-label={`Sort by ${label}`}
        className="inline-flex items-center gap-1 font-bold uppercase hover:text-primary dark:hover:text-night-ink"
      >
        <span>{label}</span>
        <Icon
          size={14}
          aria-hidden="true"
          className={hideIconOnPhone ? 'hidden sm:block' : undefined}
        />
      </button>
    </th>
  )
}
