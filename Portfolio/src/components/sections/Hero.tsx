import { useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import SplitType from 'split-type'
import { useVanta } from '../../hooks/useVanta'
import { profile } from '../../data/profile'

export function Hero() {
  const containerRef = useRef<HTMLDivElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const subtitleRef = useRef<HTMLParagraphElement>(null)
  const ctaRef = useRef<HTMLButtonElement>(null)

  const { isReady } = useVanta(containerRef)

  useGSAP(() => {
    if (!titleRef.current || !subtitleRef.current || !ctaRef.current) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const titleSplit = new SplitType(titleRef.current, { types: 'chars' })
    const subtitleSplit = new SplitType(subtitleRef.current, { types: 'lines' })

    if (prefersReduced) {
      gsap.set([...(titleSplit.chars ?? []), ...(subtitleSplit.lines ?? []), ctaRef.current], { opacity: 1, y: 0, scale: 1 })
      return () => {
        titleSplit.revert()
        subtitleSplit.revert()
      }
    }

    const tl = gsap.timeline({ delay: 0.3 })

    tl.from(titleSplit.chars ?? [], {
      y: 20,
      opacity: 0,
      stagger: 0.05,
      duration: 0.6,
      ease: 'power2.out',
    })
    .from(subtitleSplit.lines ?? [], {
      y: 15,
      opacity: 0,
      stagger: 0.1,
      duration: 0.5,
      ease: 'power2.out',
    }, '-=0.2')
    .from(ctaRef.current, {
      scale: 0.9,
      opacity: 0,
      duration: 0.4,
      ease: 'back.out(1.7)',
    }, '-=0.1')

    return () => {
      titleSplit.revert()
      subtitleSplit.revert()
    }
  }, { scope: containerRef, dependencies: [isReady] })

  const scrollToWorks = () => {
    document.querySelector('#works')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <section
      id="hero"
      ref={containerRef}
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden"
    >
      {/* コンテンツ */}
      <div className="relative z-10 text-center px-6 max-w-4xl">
        <p className="text-xs font-mono tracking-[0.4em] text-cyan-500 uppercase mb-6">
          Freelance Engineer — Since {profile.freelanceFrom}
        </p>

        <h1
          ref={titleRef}
          className="text-5xl md:text-7xl font-black text-fg leading-tight mb-4 tracking-tight"
        >
          {profile.catchcopy.ja}
        </h1>

        <p
          ref={subtitleRef}
          className="text-base md:text-lg text-fg/60 font-mono mb-10 leading-relaxed"
        >
          {profile.catchcopy.en}
          <br />
          Data Science × Backend × Frontend
        </p>

        <button
          ref={ctaRef}
          onClick={scrollToWorks}
          className="px-8 py-3 rounded border border-cyan-500/50 text-cyan-400 font-mono text-sm hover:bg-cyan-500/10 transition-all duration-200 hover:border-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.2)]"
        >
          See My Work →
        </button>
      </div>

      {/* スクロールインジケーター */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-40">
        <span className="text-xs font-mono tracking-widest text-fg/50">SCROLL</span>
        <div className="w-px h-12 bg-gradient-to-b from-cyan-500/50 to-transparent" />
      </div>
    </section>
  )
}
