import { useRef, useState } from 'react'
import emailjs from '@emailjs/browser'
import { SectionTitle } from '../ui/SectionTitle'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { profile } from '../../data/profile'

type FormState = {
  name: string
  email: string
  message: string
}

type SendStatus = 'idle' | 'sending' | 'success' | 'error'

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate(form: FormState): Partial<FormState> {
  if (!form.name.trim()) return { name: '必須項目です' }
  if (!form.email.trim()) return { email: '必須項目です' }
  if (!EMAIL_REGEX.test(form.email)) return { email: 'メールアドレスの形式が正しくありません' }
  if (!form.message.trim()) return { message: '必須項目です' }
  if (form.message.length > 1000) return { message: '1000文字以内で入力してください' }
  return {}
}

export function Contact() {
  const sectionRef = useRef<HTMLElement>(null)
  const formRef = useRef<HTMLFormElement>(null)
  const [form, setForm] = useState<FormState>({ name: '', email: '', message: '' })
  const [errors, setErrors] = useState<Partial<FormState>>({})
  const [status, setStatus] = useState<SendStatus>('idle')

  useScrollAnimation(sectionRef, { childSelector: '.contact-block', stagger: 0.12 })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    setErrors(prev => ({ ...prev, [e.target.name]: undefined }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setStatus('sending')
    try {
      await emailjs.sendForm(
        import.meta.env.VITE_EMAILJS_SERVICE_ID,
        import.meta.env.VITE_EMAILJS_TEMPLATE_ID,
        formRef.current!,
        import.meta.env.VITE_EMAILJS_PUBLIC_KEY,
      )
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }

  const SNS_LINKS = [
    { label: 'GitHub', href: profile.contact.github, color: 'border-white/20 hover:border-white/50' },
    ...(profile.contact.x ? [{ label: 'X (Twitter)', href: profile.contact.x, color: 'border-white/20 hover:border-white/50' }] : []),
    { label: 'Email', href: `mailto:${profile.contact.email}`, color: 'border-cyan-500/30 hover:border-cyan-500' },
  ]

  return (
    <section id="contact" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="Contact" ja="お問い合わせ" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* SNSリンク */}
        <div className="contact-block space-y-4">
          <p className="text-fg/60 text-sm leading-relaxed mb-6">
            お仕事のご相談・ご依頼はお気軽にどうぞ。<br />
            Feel free to reach out for project inquiries.
          </p>
          {SNS_LINKS.map(link => (
            <a
              key={link.label}
              href={link.href}
              target={link.href.startsWith('mailto') ? undefined : '_blank'}
              rel="noopener noreferrer"
              className={`flex items-center justify-between p-4 rounded border bg-white/5 transition-all duration-200 hover:bg-white/8 font-mono text-sm ${link.color}`}
            >
              <span className="text-fg/80">{link.label}</span>
              <span className="text-fg/30">→</span>
            </a>
          ))}
        </div>

        {/* フォーム */}
        <div className="contact-block">
          {status === 'success' ? (
            <div className="p-8 rounded border border-cyan-500/30 bg-cyan-500/5 text-center">
              <p className="text-cyan-400 font-mono text-lg mb-2">✓ Sent!</p>
              <p className="text-fg/60 text-sm">メッセージを送信しました。ありがとうございます。</p>
            </div>
          ) : (
            <form ref={formRef} onSubmit={handleSubmit} className="space-y-4" noValidate>
              {/* Name */}
              <div>
                <label htmlFor="name" className="block text-xs font-mono text-fg/50 mb-1 tracking-widest">NAME</label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={form.name}
                  onChange={handleChange}
                  className="w-full bg-white/5 border border-white/15 rounded px-4 py-2.5 text-sm text-fg focus:outline-none focus:border-cyan-500/50 transition-colors"
                />
                {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name}</p>}
              </div>

              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-xs font-mono text-fg/50 mb-1 tracking-widest">EMAIL</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={handleChange}
                  className="w-full bg-white/5 border border-white/15 rounded px-4 py-2.5 text-sm text-fg focus:outline-none focus:border-cyan-500/50 transition-colors"
                />
                {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email}</p>}
              </div>

              {/* Message */}
              <div>
                <label htmlFor="message" className="block text-xs font-mono text-fg/50 mb-1 tracking-widest">MESSAGE</label>
                <textarea
                  id="message"
                  name="message"
                  rows={5}
                  value={form.message}
                  onChange={handleChange}
                  className="w-full bg-white/5 border border-white/15 rounded px-4 py-2.5 text-sm text-fg focus:outline-none focus:border-cyan-500/50 transition-colors resize-none"
                />
                <div className="flex justify-between mt-1">
                  {errors.message && <p className="text-red-400 text-xs">{errors.message}</p>}
                  <span className="text-xs text-fg/30 ml-auto">{form.message.length}/1000</span>
                </div>
              </div>

              {status === 'error' && (
                <p className="text-red-400 text-xs">送信に失敗しました。時間をおいて再度お試しください。</p>
              )}

              <button
                type="submit"
                disabled={status === 'sending'}
                className="w-full py-3 rounded border border-cyan-500/50 text-cyan-400 font-mono text-sm hover:bg-cyan-500/10 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {status === 'sending' ? 'Sending...' : 'Send Message →'}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  )
}
