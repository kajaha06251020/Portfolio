import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Contact } from '../Contact'
import emailjs from '@emailjs/browser'

vi.mock('../../hooks/useScrollAnimation', () => ({ useScrollAnimation: vi.fn() }))
vi.mock('@gsap/react', () => ({ useGSAP: vi.fn() }))
vi.mock('gsap', () => ({ default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn() } }))
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn() } }))
vi.mock('@emailjs/browser', () => ({ default: { sendForm: vi.fn(() => Promise.resolve()) } }))

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

  it('有効フォーム送信で成功メッセージが表示される', async () => {
    vi.mocked(emailjs.sendForm).mockResolvedValueOnce({ status: 200, text: 'OK' })
    const user = userEvent.setup()
    render(<Contact />)
    await user.type(screen.getByLabelText(/name/i), 'Test User')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/message/i), 'Hello World')
    await user.click(screen.getByRole('button', { name: /send/i }))
    expect(await screen.findByText(/Sent!/)).toBeInTheDocument()
  })

  it('送信失敗でエラーメッセージが表示される', async () => {
    vi.mocked(emailjs.sendForm).mockRejectedValueOnce(new Error('Network error'))
    const user = userEvent.setup()
    render(<Contact />)
    await user.type(screen.getByLabelText(/name/i), 'Test User')
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/message/i), 'Hello World')
    await user.click(screen.getByRole('button', { name: /send/i }))
    expect(await screen.findByText(/送信に失敗/)).toBeInTheDocument()
  })
})
