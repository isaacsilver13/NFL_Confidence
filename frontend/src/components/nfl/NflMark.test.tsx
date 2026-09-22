import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NflMark } from './NflMark'

describe('NflMark', () => {
  it('renders the full wordmark by default', () => {
    render(<NflMark />)

    expect(screen.getByText('NFL')).toBeInTheDocument()
    expect(screen.getByText('Confidence')).toBeInTheDocument()
  })

  it('hides the wordmark text in compact mode', () => {
    render(<NflMark compact />)

    expect(screen.queryByText('NFL')).not.toBeInTheDocument()
    expect(screen.queryByText('Confidence')).not.toBeInTheDocument()
  })
})
