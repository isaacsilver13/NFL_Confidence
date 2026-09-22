import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AccordionSection } from './AccordionSection'

describe('AccordionSection', () => {
  it('wires aria-expanded and aria-controls to the toggle button and renders children when open', () => {
    render(
      <AccordionSection
        id="picks"
        title="Picks"
        summary="This week's picks"
        isOpen
        onToggle={vi.fn()}
      >
        <p>Section body</p>
      </AccordionSection>,
    )

    const toggle = screen.getByRole('button', { name: /Picks/ })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(toggle).toHaveAttribute('aria-controls', 'picks-body')
    expect(screen.getByText('Section body')).toBeInTheDocument()
  })

  it('does not render children in the DOM when closed', () => {
    render(
      <AccordionSection
        id="picks"
        title="Picks"
        summary="This week's picks"
        isOpen={false}
        onToggle={vi.fn()}
      >
        <p>Section body</p>
      </AccordionSection>,
    )

    expect(screen.getByRole('button', { name: /Picks/ })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Section body')).not.toBeInTheDocument()
  })

  it('calls onToggle when the header button is clicked', async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()
    render(
      <AccordionSection
        id="picks"
        title="Picks"
        summary="This week's picks"
        isOpen={false}
        onToggle={onToggle}
      >
        <p>Section body</p>
      </AccordionSection>,
    )

    await user.click(screen.getByRole('button', { name: /Picks/ }))

    expect(onToggle).toHaveBeenCalledTimes(1)
  })
})
