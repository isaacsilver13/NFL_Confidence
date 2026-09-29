import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'
import type { TableSort } from './useTableSort'

export function SortableTh({
  label,
  columnKey,
  sort,
  align = 'left',
  className = 'px-5 py-4',
}: {
  label: string
  columnKey: string
  sort: TableSort
  align?: 'left' | 'right' | 'center'
  className?: string
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
        className="inline-flex items-center gap-1 font-bold uppercase hover:text-primary dark:hover:text-white dev-dark:hover:text-ink"
      >
        <span>{label}</span>
        <Icon size={14} aria-hidden="true" />
      </button>
    </th>
  )
}
