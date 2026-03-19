import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useVanta } from '../useVanta'

// Vanta と THREE はブラウザ依存のため jsdom では mock する
vi.mock('vanta/dist/vanta.net.min', () => ({
  default: vi.fn(() => ({ destroy: vi.fn(), resize: vi.fn() })),
}))
vi.mock('three', () => ({}))

describe('useVanta', () => {
  it('ref が null のときクラッシュしない', () => {
    const ref = { current: null } as React.RefObject<HTMLDivElement>
    expect(() => renderHook(() => useVanta(ref))).not.toThrow()
  })

  it('isReady を返す', () => {
    const ref = { current: null } as React.RefObject<HTMLDivElement>
    const { result } = renderHook(() => useVanta(ref))
    expect(typeof result.current.isReady).toBe('boolean')
  })
})
