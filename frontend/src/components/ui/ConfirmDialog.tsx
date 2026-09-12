import { useEffect } from 'react'
import { Button } from './Button'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  isDangerous?: boolean
  isBusy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/**
 * Accessible replacement for `window.confirm()` for destructive actions.
 * Native confirm() blocks the JS thread and renders inconsistently across
 * mobile browsers; this matches the app's own UI and touch-target sizing.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDangerous = true,
  isBusy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-4 sm:items-center"
      onClick={onCancel}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        className="w-full max-w-sm space-y-4 rounded-2xl bg-surface p-5 shadow-xl dark:bg-slate-900"
        onClick={(event) => event.stopPropagation()}
      >
        <div>
          <h2 id="confirm-dialog-title" className="text-lg font-bold">
            {title}
          </h2>
          <p
            id="confirm-dialog-description"
            className="mt-1 text-sm text-ink-muted dark:text-slate-300"
          >
            {description}
          </p>
        </div>
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="secondary" onClick={onCancel} disabled={isBusy}>
            {cancelLabel}
          </Button>
          <Button
            type="button"
            autoFocus
            variant={isDangerous ? 'danger' : 'primary'}
            onClick={onConfirm}
            disabled={isBusy}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
