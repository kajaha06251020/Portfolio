import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useScrollAnimation } from '../useScrollAnimation'

vi.mock('gsap', () => ({
  default: { to: vi.fn(), fromTo: vi.fn(), set: vi.fn(), context: vi.fn(() => ({ revert: vi.fn() })) },
}))
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn() } }))
vi.mock('@gsap/react', () => ({
  useGSAP: (fn: () => void) => { try { fn() } catch { /* ignore */ } },
}))

describe('useScrollAnimation', () => {
  it('ref が null でもクラッシュしない', () => {
    const ref = { current: null } as React.RefObject<Element>
    expect(() => renderHook(() => useScrollAnimation(ref))).not.toThrow()
  })

  it('戻り値は undefined (void)', () => {
    const ref = { current: null } as React.RefObject<Element>
    const { result } = renderHook(() => useScrollAnimation(ref))
    expect(result.current).toBeUndefined()
  })
})
