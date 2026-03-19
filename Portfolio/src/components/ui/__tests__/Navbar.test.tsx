import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Navbar } from '../Navbar'

describe('Navbar', () => {
  it('ナビリンクが全て表示される', () => {
    render(<Navbar />)
    expect(screen.getByText('Works')).toBeInTheDocument()
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText('About')).toBeInTheDocument()
    expect(screen.getByText('Contact')).toBeInTheDocument()
  })

  it('ロゴが表示される', () => {
    render(<Navbar />)
    expect(screen.getByText('kajaha')).toBeInTheDocument()
  })
})
