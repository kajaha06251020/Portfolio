declare module 'split-type' {
  interface SplitTypeOptions {
    types?: string
    tagName?: string
    lineClass?: string
    wordClass?: string
    charClass?: string
    splitClass?: string
    absolute?: boolean
    reduceWhiteSpace?: boolean
  }
  class SplitType {
    chars: HTMLElement[] | null
    words: HTMLElement[] | null
    lines: HTMLElement[] | null
    constructor(target: string | HTMLElement | HTMLElement[], options?: SplitTypeOptions)
    revert(): void
    split(options?: SplitTypeOptions): void
  }
  export default SplitType
}
