import { createRef } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Button } from './Button'

describe('Button', () => {
  it('applies the primary variant classes by default', () => {
    render(<Button>Save</Button>)

    expect(screen.getByRole('button', { name: 'Save' })).toHaveClass('bg-primary', 'text-white')
  })

  it('applies the secondary variant classes', () => {
    render(<Button variant="secondary">Cancel</Button>)

    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveClass(
      'border',
      'border-primary/20',
    )
  })

  it('applies the quiet variant classes', () => {
    render(<Button variant="quiet">Dismiss</Button>)

    expect(screen.getByRole('button', { name: 'Dismiss' })).toHaveClass('text-ink-muted')
  })

  it('applies the danger variant classes', () => {
    render(<Button variant="danger">Delete</Button>)

    expect(screen.getByRole('button', { name: 'Delete' })).toHaveClass('bg-danger', 'text-white')
  })

  it('applies the disabled attribute and styling', () => {
    render(<Button disabled>Save</Button>)

    const button = screen.getByRole('button', { name: 'Save' })
    expect(button).toBeDisabled()
    expect(button).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-60')
  })

  it('applies full width styling when fullWidth is set', () => {
    render(<Button fullWidth>Save</Button>)

    expect(screen.getByRole('button', { name: 'Save' })).toHaveClass('w-full')
  })

  it('does not apply full width styling by default', () => {
    render(<Button>Save</Button>)

    expect(screen.getByRole('button', { name: 'Save' })).not.toHaveClass('w-full')
  })

  it('forwards a ref to the underlying button DOM node', () => {
    const ref = createRef<HTMLButtonElement>()
    render(<Button ref={ref}>Save</Button>)

    expect(ref.current).toBeInstanceOf(HTMLButtonElement)
    expect(ref.current).toBe(screen.getByRole('button', { name: 'Save' }))
  })
})
