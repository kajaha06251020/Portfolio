import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Skills } from '../Skills'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))
vi.mock('@gsap/react', () => ({ useGSAP: vi.fn() }))
vi.mock('gsap', () => ({ default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn() } }))
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn() } }))

describe('Skills', () => {
  it('3つのドメインパネルが表示される', () => {
    render(<Skills />)
    expect(screen.getByText('Data Science')).toBeInTheDocument()
    expect(screen.getByText('Backend')).toBeInTheDocument()
    expect(screen.getByText('Frontend')).toBeInTheDocument()
  })

  it('Python スキルが表示される', () => {
    render(<Skills />)
    expect(screen.getByText('Python')).toBeInTheDocument()
  })
})
