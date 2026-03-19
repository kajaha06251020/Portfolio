import { useRef, useState, useCallback } from 'react'
import gsap from 'gsap'
import { SectionTitle } from '../ui/SectionTitle'
import { ProjectCard } from '../ui/ProjectCard'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { projects, CATEGORY_LABELS, type Project } from '../../data/projects'

type FilterCategory = Project['category'] | 'all'

const FILTER_CATEGORIES: FilterCategory[] = ['all', 'data', 'backend', 'frontend']

export function Works() {
  const sectionRef = useRef<HTMLElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)
  const [activeFilter, setActiveFilter] = useState<FilterCategory>('all')

  useScrollAnimation(sectionRef, { childSelector: '.card', stagger: 0.1 })

  const handleFilter = useCallback((category: FilterCategory) => {
    if (category === activeFilter || !gridRef.current) return

    const cards = Array.from(gridRef.current.querySelectorAll<HTMLElement>('.card'))

    gsap.to(cards, {
      opacity: 0,
      duration: 0.2,
      onComplete: () => {
        setActiveFilter(category)
        requestAnimationFrame(() => {
          const visibleCards = Array.from(
            gridRef.current?.querySelectorAll<HTMLElement>('.card') ?? []
          )
          gsap.fromTo(
            visibleCards,
            { opacity: 0, y: 20 },
            { opacity: 1, y: 0, stagger: 0.05, duration: 0.3, ease: 'power2.out' }
          )
        })
      },
    })
  }, [activeFilter])

  const filtered = activeFilter === 'all'
    ? projects
    : projects.filter(p => p.category === activeFilter)

  return (
    <section id="works" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="Works" ja="制作物" />

      {/* フィルターボタン */}
      <div className="flex gap-3 mb-12 flex-wrap">
        {FILTER_CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => handleFilter(cat)}
            className={`px-4 py-1.5 rounded-full text-xs font-mono border transition-all duration-200 ${
              activeFilter === cat
                ? 'border-cyan-500 text-cyan-400 bg-cyan-500/10'
                : 'border-white/20 text-fg/50 hover:border-white/40 hover:text-fg/80'
            }`}
          >
            {CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* カードグリッド */}
      <div
        ref={gridRef}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
      >
        {filtered.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>

      {/* 注記 */}
      <p className="mt-10 text-sm text-fg/35 font-mono text-center border-t border-white/5 pt-8">
        ▸ GitHub に公開していない制作物も多数あります。詳細はお気軽にお問い合わせください。
      </p>
    </section>
  )
}
