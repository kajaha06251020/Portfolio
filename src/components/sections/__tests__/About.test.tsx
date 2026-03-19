import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { About } from '../About'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))
vi.mock('@gsap/react', () => ({ useGSAP: vi.fn() }))
vi.mock('gsap', () => ({ default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn() } }))
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn() } }))

describe('About', () => {
  it('自己紹介文（日英）が表示される', () => {
    render(<About />)
    expect(screen.getByText(/フリーランスエンジニア/)).toBeInTheDocument()
    expect(screen.getByText(/Freelance engineer/)).toBeInTheDocument()
  })

  it('フリーランス開始年が表示される', () => {
    render(<About />)
    expect(screen.getByText(/2026/)).toBeInTheDocument()
  })
})
