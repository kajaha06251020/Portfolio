import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Contact } from '../Contact'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))
vi.mock('@gsap/react', () => ({ useGSAP: vi.fn() }))
vi.mock('gsap', () => ({ default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn() } }))
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn() } }))

describe('Contact', () => {
  it('SNSリンクが表示される', () => {
    render(<Contact />)
    expect(screen.getByRole('link', { name: /GitHub/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Email/ })).toBeInTheDocument()
  })

  it('GitHub リンクが正しい href を持つ', () => {
    render(<Contact />)
    expect(screen.getByRole('link', { name: /GitHub/ })).toHaveAttribute('href', 'https://github.com/kajaha06251020')
  })

  it('Email リンクが mailto を持つ', () => {
    render(<Contact />)
    expect(screen.getByRole('link', { name: /Email/ })).toHaveAttribute('href', 'mailto:shotacoding@gmail.com')
  })
})
