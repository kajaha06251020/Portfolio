declare module 'vanta/dist/vanta.net.min' {
  interface VantaNetOptions {
    el: HTMLElement
    THREE: unknown
    color?: number
    color2?: number
    backgroundColor?: number
    points?: number
    maxDistance?: number
    spacing?: number
    showDots?: boolean
  }
  interface VantaEffect {
    destroy: () => void
    resize: () => void
  }
  function NET(options: VantaNetOptions): VantaEffect
  export = NET
}
