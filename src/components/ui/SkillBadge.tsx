import type { Skill } from '../../data/skills'

interface SkillBadgeProps {
  skill: Skill
}

export function SkillBadge({ skill }: SkillBadgeProps) {
  return (
    <div className="flex items-center justify-between px-3 py-2 rounded border border-white/10 bg-white/5 hover:border-cyan-500/40 transition-colors">
      <span className="text-sm font-mono text-fg">{skill.name}</span>
      <span className="text-xs text-cyan-500/70 ml-3 whitespace-nowrap">{skill.years}</span>
    </div>
  )
}
