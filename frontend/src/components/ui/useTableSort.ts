import { useMemo, useState } from 'react'

export type SortDirection = 'ascending' | 'descending'
export type SortValue = string | number | null

export interface SortColumn<T> {
  value: (row: T) => SortValue
  /** Numeric columns sort highest-first on the first click; text columns A-Z. */
  numeric?: boolean
}

export interface TableSort {
  sortKey: string | null
  direction: SortDirection
  requestSort: (key: string) => void
}

function compareValues(left: SortValue, right: SortValue): number {
  if (typeof left === 'number' && typeof right === 'number') return left - right
  return String(left).localeCompare(String(right), undefined, { numeric: true })
}

/**
 * Sorts `rows` by one of the named columns. With no active column the original order is kept,
 * ties keep their original order, and empty (null) values always sort last.
 */
export function useTableSort<T>(
  rows: T[],
  columns: Record<string, SortColumn<T>>,
  initial?: { key: string; direction?: SortDirection },
): { sortedRows: T[] } & TableSort {
  const [sortKey, setSortKey] = useState<string | null>(initial?.key ?? null)
  const [direction, setDirection] = useState<SortDirection>(initial?.direction ?? 'ascending')

  const sortedRows = useMemo(() => {
    const column = sortKey ? columns[sortKey] : undefined
    if (!column) return rows
    const sign = direction === 'ascending' ? 1 : -1
    return [...rows].sort((left, right) => {
      const leftValue = column.value(left)
      const rightValue = column.value(right)
      if (leftValue === null && rightValue === null) return 0
      if (leftValue === null) return 1
      if (rightValue === null) return -1
      return compareValues(leftValue, rightValue) * sign
    })
    // `columns` is rebuilt every render by callers; the row identity and sort state are what matter.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, sortKey, direction])

  function requestSort(key: string) {
    if (key === sortKey) {
      setDirection((current) => (current === 'ascending' ? 'descending' : 'ascending'))
      return
    }
    setSortKey(key)
    setDirection(columns[key]?.numeric ? 'descending' : 'ascending')
  }

  return { sortedRows, sortKey, direction, requestSort }
}
