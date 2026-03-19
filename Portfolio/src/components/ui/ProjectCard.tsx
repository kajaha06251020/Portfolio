import type { Project } from '../../data/projects'

interface ProjectCardProps {
  project: Project
}

const CATEGORY_COLORS: Record<Project['category'], string> = {
  data: 'from-cyan-500/20 to-purple-500/10',
  backend: 'from-purple-500/20 to-cyan-500/10',
  frontend: 'from-cyan-500/10 to-purple-500/20',
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <article className="card group rounded-lg border border-white/10 bg-white/5 overflow-hidden hover:border-cyan-500/40 transition-all duration-300 hover:-translate-y-1">
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
        <h3 className="text-base font-bold text-fg mb-2">{project.title}</h3>
        <p className="text-sm text-fg/60 mb-1">{project.description.ja}</p>
        <p className="text-xs text-fg/40 mb-4">{project.description.en}</p>

        {/* タグ */}
        <div className="flex flex-wrap gap-1 mb-4">
          {project.tags.map(tag => (
            <span key={tag} className="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono border border-cyan-500/20">
              {tag}
            </span>
          ))}
        </div>

        {/* リンク */}
        <div className="flex gap-3">
          <a
            href={project.github}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-fg/50 hover:text-cyan-400 transition-colors font-mono"
            aria-label="GitHub"
          >
            GitHub →
          </a>
          {project.demo && (
            <a
              href={project.demo}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-fg/50 hover:text-purple-400 transition-colors font-mono"
            >
              Demo →
            </a>
          )}
        </div>
      </div>
    </article>
  )
}
