interface SectionTitleProps {
  en: string
  ja: string
}

export function SectionTitle({ en, ja }: SectionTitleProps) {
  return (
    <div className="mb-12">
      <p className="text-xs font-mono tracking-[0.3em] text-cyan-500 uppercase mb-2">{ja}</p>
      <h2 className="text-4xl font-bold text-fg">{en}</h2>
      <div className="mt-3 h-px w-16 bg-gradient-to-r from-cyan-500 to-purple-500" />
    </div>
  )
}
