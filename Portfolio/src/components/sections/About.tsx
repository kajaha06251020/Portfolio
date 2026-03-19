import { useRef } from 'react'
import { SectionTitle } from '../ui/SectionTitle'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { profile } from '../../data/profile'

export function About() {
  const sectionRef = useRef<HTMLElement>(null)
  useScrollAnimation(sectionRef, { childSelector: '.about-block', stagger: 0.12 })

  return (
    <section id="about" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="About" ja="プロフィール" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* 自己紹介 */}
        <div className="about-block space-y-4">
          <p className="text-fg/80 leading-relaxed">{profile.bio.ja}</p>
          <p className="text-fg/50 text-sm leading-relaxed">{profile.bio.en}</p>
        </div>

        {/* ハイライト */}
        <div className="space-y-4">
          <div className="about-block p-4 rounded border border-white/10 bg-white/5">
            <p className="text-xs font-mono text-cyan-500 mb-1 tracking-widest">FREELANCE FROM</p>
            <p className="text-2xl font-bold text-fg">{profile.freelanceFrom}</p>
          </div>

          <div className="about-block p-4 rounded border border-white/10 bg-white/5">
            <p className="text-xs font-mono text-cyan-500 mb-2 tracking-widest">STRENGTHS</p>
            <ul className="space-y-1">
              {[
                'データ解析からサービス実装まで一貫対応',
                '領域横断による課題解決',
                'スケーラブルなシステム設計',
              ].map(item => (
                <li key={item} className="text-sm text-fg/70 flex items-start gap-2">
                  <span className="text-cyan-500 mt-0.5">▸</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="about-block p-4 rounded border border-white/10 bg-white/5">
            <p className="text-xs font-mono text-purple-400 mb-2 tracking-widest">NEXT GOALS</p>
            <ul className="space-y-1">
              {[
                'モデルの実運用・MLOps',
                'チームでの設計改善・アーキテクチャ改善',
              ].map(item => (
                <li key={item} className="text-sm text-fg/70 flex items-start gap-2">
                  <span className="text-purple-400 mt-0.5">▸</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
