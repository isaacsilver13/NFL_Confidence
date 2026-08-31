import type { ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'quiet' | 'danger'
  fullWidth?: boolean
}

const variants = {
  primary:
    'bg-primary text-white shadow-sm hover:bg-primary-hover disabled:bg-primary/50 dark:bg-sky dark:text-primary dark:hover:bg-sky/90',
  secondary:
    'border border-primary/20 bg-white text-primary hover:border-sky hover:bg-sky/10 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:border-sky',
  quiet:
    'text-ink-muted hover:bg-surface-muted hover:text-primary dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white',
  danger: 'bg-danger text-white hover:bg-danger/90 disabled:bg-danger/50',
}

export function Button({
  className = '',
  variant = 'primary',
  fullWidth = false,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-bold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    />
  )
}
