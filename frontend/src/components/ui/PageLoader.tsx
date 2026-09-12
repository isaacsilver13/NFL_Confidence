export function PageLoader() {
  return (
    <div className="flex min-h-40 items-center justify-center py-12" role="status">
      <span className="sr-only">Loading…</span>
      <span
        aria-hidden="true"
        className="h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary dark:border-slate-700 dark:border-t-sky"
      />
    </div>
  )
}
