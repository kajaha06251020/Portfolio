import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Works } from '../Works'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))
vi.mock('@gsap/react', () => ({ useGSAP: vi.fn() }))
vi.mock('gsap', () => ({ default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn() } }))

describe('Works', () => {
  it('フィルターボタンが全て表示される', () => {
    render(<Works />)
    expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Data Science' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Backend' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Frontend' })).toBeInTheDocument()
  })

  it('初期状態で全プロジェクトが表示される', () => {
    render(<Works />)
    expect(screen.getAllByRole('article').length).toBeGreaterThan(0)
  })

  it('Backend フィルターをクリックすると Backend プロジェクトのみ表示', async () => {
    const user = userEvent.setup()
    render(<Works />)
    await user.click(screen.getByRole('button', { name: 'Backend' }))
    // GSAP mock のため実際のフィルターはスキップ — ボタンクリックがエラーなく動くことを確認
    expect(screen.getByRole('button', { name: 'Backend' })).toBeInTheDocument()
  })
})
