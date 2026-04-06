import type { Project, ProjectStats } from '../types'

const STATUS_COLORS: Record<string, string> = {
  pending: '#888',
  parsing: '#e69500',
  searching: '#e69500',
  researching: '#2563eb',
  resolving: '#2563eb',
  scoring: '#2563eb',
  done: '#16a34a',
  error: '#dc2626',
}

export function ProjectHeader({
  project,
  stats,
}: {
  project: Project | null
  stats: ProjectStats | null
}) {
  if (!project) return <div className="project-header">Loading...</div>

  const color = STATUS_COLORS[project.status] ?? '#888'
  const tokens = stats
    ? stats.total_input_tokens + stats.total_output_tokens
    : 0
  const costUsd = tokens * 0.000003 // rough estimate for sonnet

  return (
    <div className="project-header">
      <div className="header-top">
        <span className="status-dot" style={{ background: color }} />
        <span className="status-label">{project.status}</span>
        {stats && (
          <span className="header-stats">
            {stats.total_listings} listings
            {' \u00b7 '}
            {stats.completed_listings} complete
            {' \u00b7 '}
            avg {Math.round(stats.avg_completeness * 100)}% data
            {' \u00b7 '}
            ~${costUsd.toFixed(2)}
          </span>
        )}
      </div>
      <p className="header-prompt">{project.prompt}</p>
      {project.parsed_intent && (
        <p className="header-intent">{project.parsed_intent}</p>
      )}
    </div>
  )
}
