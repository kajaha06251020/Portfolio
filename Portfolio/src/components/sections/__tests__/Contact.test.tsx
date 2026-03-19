import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Contact } from '../Contact'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))
vi.mock('@gsap/react', () => ({ useGSAP: vi.fn() }))
vi.mock('gsap', () => ({ default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn() } }))
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn() } }))
vi.mock('@emailjs/browser', () => ({ sendForm: vi.fn(() => Promise.resolve()) }))

describe('Contact', () => {
  it('フォームフィールドが全て表示される', () => {
    render(<Contact />)
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument()
  })

  it('空フォーム送信でバリデーションエラー', async () => {
    const user = userEvent.setup()
    render(<Contact />)
    await user.click(screen.getByRole('button', { name: /send/i }))
    expect(screen.getByText(/必須/)).toBeInTheDocument()
  })

  it('不正なメールアドレスでエラー', async () => {
    const user = userEvent.setup()
    render(<Contact />)
    await user.type(screen.getByLabelText(/name/i), 'Test')
    await user.type(screen.getByLabelText(/email/i), 'invalid-email')
    await user.type(screen.getByLabelText(/message/i), 'Hello')
    await user.click(screen.getByRole('button', { name: /send/i }))
    expect(screen.getByText(/メールアドレス/)).toBeInTheDocument()
  })
})
