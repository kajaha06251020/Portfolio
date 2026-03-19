import { useRef } from 'react'
import { SectionTitle } from '../ui/SectionTitle'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { profile } from '../../data/profile'

export function Contact() {
  const sectionRef = useRef<HTMLElement>(null)

  useScrollAnimation(sectionRef, { childSelector: '.contact-block', stagger: 0.12 })

  const SNS_LINKS = [
    { label: 'GitHub', href: profile.contact.github, color: 'border-white/20 hover:border-white/50' },
    ...(profile.contact.x ? [{ label: 'X (Twitter)', href: profile.contact.x, color: 'border-white/20 hover:border-white/50' }] : []),
    { label: 'Email', href: `mailto:${profile.contact.email}`, color: 'border-cyan-500/30 hover:border-cyan-500' },
  ]

  return (
    <section id="contact" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="Contact" ja="お問い合わせ" />

      <div className="contact-block max-w-md space-y-4">
        <p className="text-fg/60 text-base leading-relaxed mb-6">
          お仕事のご相談・ご依頼はお気軽にどうぞ。<br />
          Feel free to reach out for project inquiries.
        </p>
        {SNS_LINKS.map(link => (
          <a
            key={link.label}
            href={link.href}
            target={link.href.startsWith('mailto') ? undefined : '_blank'}
            rel="noopener noreferrer"
            className={`flex items-center justify-between p-4 rounded border bg-white/5 transition-all duration-200 hover:bg-white/8 font-mono text-base ${link.color}`}
          >
            <span className="text-fg/80">{link.label}</span>
            <span className="text-fg/30">→</span>
          </a>
        ))}
      </div>
    </section>
  )
}
