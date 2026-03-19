import { useRef } from 'react'
import { SectionTitle } from '../ui/SectionTitle'
import { SkillBadge } from '../ui/SkillBadge'
import { useScrollAnimation } from '../../hooks/useScrollAnimation'
import { skills, type Skill } from '../../data/skills'

const DOMAIN_CONFIG: {
  key: Skill['domain']
  label: string
  color: string
}[] = [
  { key: 'data',     label: 'Data Science', color: 'border-cyan-500/30 hover:border-cyan-500/60' },
  { key: 'backend',  label: 'Backend',      color: 'border-purple-500/30 hover:border-purple-500/60' },
  { key: 'frontend', label: 'Frontend',     color: 'border-cyan-500/20 hover:border-cyan-500/50' },
]

export function Skills() {
  const sectionRef = useRef<HTMLElement>(null)

  useScrollAnimation(sectionRef, { childSelector: '.skill-panel', stagger: 0.15 })

  return (
    <section id="skills" ref={sectionRef} className="py-24 px-6 max-w-6xl mx-auto">
      <SectionTitle en="Skills" ja="技術スタック" />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {DOMAIN_CONFIG.map(({ key, label, color }) => {
          const domainSkills = skills.filter(s => s.domain === key)
          return (
            <div
              key={key}
              className={`skill-panel rounded-lg border p-6 bg-white/3 transition-all duration-300 ${color}`}
            >
              <h3 className="text-sm font-mono tracking-widest text-fg/40 uppercase mb-5">{label}</h3>
              <div className="flex flex-col gap-2">
                {domainSkills.map(skill => (
                  <SkillBadge key={skill.name} skill={skill} />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
