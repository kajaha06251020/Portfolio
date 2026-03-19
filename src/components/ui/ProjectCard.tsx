import type { Project } from '../../data/projects'

interface ProjectCardProps {
  project: Project
}

const CATEGORY_COLORS: Record<Project['category'], string> = {
  data: 'from-cyan-500/20 to-purple-500/10',
  backend: 'from-purple-500/20 to-cyan-500/10',
  frontend: 'from-cyan-500/10 to-purple-500/20',
}

const cardClass = "card group rounded-lg border border-white/10 bg-white/5 overflow-hidden transition-all duration-300 hover:-translate-y-1"

function CardInner({ project }: ProjectCardProps) {
  return (
    <>
      {/* サムネイル */}
      <div className={`h-36 bg-gradient-to-br ${CATEGORY_COLORS[project.category]} flex items-center justify-center`}>
        {project.image ? (
          <img src={project.image} alt={project.title} className="w-full h-full object-cover" />
        ) : (
          <span className="text-3xl font-bold font-mono text-white/10 select-none">
            {project.title.slice(0, 2).toUpperCase()}
          </span>
        )}
      </div>

      {/* コンテンツ */}
      <div className="p-5">
        <h3 className="text-lg font-bold text-fg mb-2">{project.title}</h3>
        <p className="text-base text-fg/60 mb-1">{project.description.ja}</p>
        <p className="text-sm text-fg/40 mb-4">{project.description.en}</p>

        {/* タグ */}
        <div className="flex flex-wrap gap-1 mb-4">
          {project.tags.map(tag => (
            <span key={tag} className="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono border border-cyan-500/20">
              {tag}
            </span>
          ))}
        </div>

        {/* リンク表示 */}
        <div className="flex gap-3 items-center">
          {project.github ? (
            <span className="text-sm text-fg/40 font-mono group-hover:text-cyan-400 transition-colors">
              GitHub →
            </span>
          ) : (
            <span className="text-xs text-fg/25 font-mono border border-white/10 px-2 py-0.5 rounded">
              Private
            </span>
          )}
          {project.demo && (
            <a
              href={project.demo}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-fg/50 hover:text-purple-400 transition-colors font-mono"
              onClick={e => e.stopPropagation()}
            >
              Demo →
            </a>
          )}
        </div>
      </div>
    </>
  )
}

export function ProjectCard({ project }: ProjectCardProps) {
  if (project.github) {
    return (
      <a
        href={project.github}
        target="_blank"
        rel="noopener noreferrer"
        className={`${cardClass} hover:border-cyan-500/40 block`}
      >
        <CardInner project={project} />
      </a>
    )
  }

  return (
    <article className={`${cardClass} border-white/10 cursor-default`}>
      <CardInner project={project} />
    </article>
  )
}
