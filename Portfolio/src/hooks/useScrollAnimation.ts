import { type RefObject } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

interface UseScrollAnimationOptions {
  stagger?: number
  start?: string
  childSelector?: string
}

export function useScrollAnimation(
  targetRef: RefObject<Element>,
  options: UseScrollAnimationOptions = {}
): void {
  const { stagger = 0.15, start = 'top 80%', childSelector } = options

  useGSAP(() => {
    if (!targetRef.current) return

    const targets = childSelector
      ? targetRef.current.querySelectorAll(childSelector)
      : [targetRef.current]

    if (targets.length === 0) return

    // prefers-reduced-motion の場合は即時表示
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
      gsap.set(targets, { opacity: 1, y: 0 })
      return
    }

    gsap.set(targets, { opacity: 0, y: 40 })

    ScrollTrigger.create({
      trigger: targetRef.current,
      start,
      onEnter: () => {
        gsap.to(targets, {
          opacity: 1,
          y: 0,
          duration: 0.7,
          stagger,
          ease: 'power2.out',
        })
      },
      once: true,
    })
  }, { scope: targetRef })
}
