import { forwardRef, type ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'quiet' | 'danger'
  fullWidth?: boolean
}

const variants = {
  primary:
    'bg-primary text-white shadow-sm hover:bg-primary-hover disabled:bg-primary/50 dark:bg-sky dev-dark:bg-accent dark:text-primary dev-dark:text-white dark:hover:bg-sky/90 dev-dark:hover:bg-accent-hover',
  secondary:
    'border border-primary/20 bg-white text-primary hover:border-sky hover:bg-sky/10 dark:border-slate-700 dev-dark:border-border-hover dark:bg-slate-900 dev-dark:bg-surface-elevated dark:text-slate-100 dev-dark:text-ink dark:hover:border-sky dev-dark:hover:border-accent',
  quiet:
    'text-ink-muted hover:bg-surface-muted hover:text-primary dark:text-slate-300 dev-dark:text-text-secondary dark:hover:bg-slate-800 dev-dark:hover:bg-surface-hover dark:hover:text-white dev-dark:hover:text-ink',
  danger: 'bg-danger text-white hover:bg-danger/90 disabled:bg-danger/50',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className = '', variant = 'primary', fullWidth = false, type = 'button', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-bold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    />
  )
})
