import { useEffect, useRef, useState } from 'react'
import type * as ThreeType from 'three'

export function useVanta(containerRef: React.RefObject<HTMLDivElement>): { isReady: boolean } {
  const effectRef = useRef<{ destroy: () => void } | null>(null)
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    // prefers-reduced-motion チェック
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setIsReady(true)
      return
    }
    if (!containerRef.current) return

    let mounted = true

    const init = async () => {
      const THREE = await import('three') as typeof ThreeType
      ;(window as Window & { THREE: typeof ThreeType }).THREE = THREE

      const VANTA = (await import('vanta/dist/vanta.net.min')).default
      if (!mounted || !containerRef.current) return

      effectRef.current = VANTA({
        el: containerRef.current,
        THREE,
        color: 0x06b6d4,
        color2: 0xa855f7,
        backgroundColor: 0x080b10,
        points: 8,
        maxDistance: 22,
        spacing: 18,
        showDots: true,
      })
      setIsReady(true)
    }

    init().catch(console.error)

    return () => {
      mounted = false
      effectRef.current?.destroy()
      effectRef.current = null
      setIsReady(false)
    }
  }, [containerRef])

  return { isReady }
}
