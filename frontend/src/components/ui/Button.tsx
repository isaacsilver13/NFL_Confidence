import { forwardRef, type ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'quiet' | 'danger'
  fullWidth?: boolean
}

const variants = {
  primary:
    'bg-primary text-white shadow-sm hover:bg-primary-hover disabled:bg-primary/50 dark:bg-night-accent orange-trim dev-dark:text-white dark:hover:bg-sky/90 dev-dark:hover:bg-accent-hover',
  secondary:
    'border border-primary/20 bg-white text-primary hover:border-sky hover:bg-sky/10 dark:border-night-line-strong dark:bg-night-card dark:text-night-ink-soft dark:hover:border-night-accent',
  quiet:
    'text-ink-muted hover:bg-surface-muted hover:text-primary dark:text-night-text dark:hover:bg-night-hover dark:hover:text-night-ink',
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
