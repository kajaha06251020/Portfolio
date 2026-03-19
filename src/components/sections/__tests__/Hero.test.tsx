import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Hero } from '../Hero'

vi.mock('../../hooks/useVanta', () => ({
  useVanta: () => ({ isReady: false }),
}))
vi.mock('@gsap/react', () => ({
  useGSAP: vi.fn(),
}))

describe('Hero', () => {
  it('キャッチコピーを含む', () => {
    render(<Hero />)
    expect(screen.getByText(/データ × コード × 設計/)).toBeInTheDocument()
  })
  it('CTAボタンが表示される', () => {
    render(<Hero />)
    expect(screen.getByRole('button', { name: /See My Work/i })).toBeInTheDocument()
  })
})
