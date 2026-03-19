import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SectionTitle } from '../SectionTitle'

describe('SectionTitle', () => {
  it('en と ja を両方レンダーする', () => {
    render(<SectionTitle en="Works" ja="制作物" />)
    expect(screen.getByText('Works')).toBeInTheDocument()
    expect(screen.getByText('制作物')).toBeInTheDocument()
  })
})
