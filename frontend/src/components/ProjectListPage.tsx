import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import type { Project } from '../types'

const STATUS_COLORS: Record<string, string> = {
  pending: '#888',
  parsing: '#e69500',
  searching: '#e69500',
  researching: '#2563eb',
  scoring: '#2563eb',
  done: '#16a34a',
  error: '#dc2626',
}

function ProjectCard({ project }: { project: Project }) {
  const age = timeSince(project.created_at)
  const color = STATUS_COLORS[project.status] ?? '#888'

  return (
    <Link to={`/projects/${project.id}`} className="project-card">
      <div className="project-card-header">
        <span className="status-dot" style={{ background: color }} />
        <span className="status-label">{project.status}</span>
        <span className="age">{age}</span>
      </div>
      <p className="project-prompt">{project.prompt}</p>
      {project.parsed_intent && (
        <p className="project-intent">{project.parsed_intent}</p>
      )}
    </Link>
  )
}

export function ProjectListPage() {
  const [prompt, setPrompt] = useState('')
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: api.listProjects,
  })

  const createMutation = useMutation({
    mutationFn: (p: string) => api.createProject(p),
    onSuccess: (project) => {
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
      navigate(`/projects/${project.id}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) return
    createMutation.mutate(prompt.trim())
  }

  return (
    <div className="page project-list-page">
      <header className="page-header">
        <h1>Research Agent</h1>
      </header>

      <form onSubmit={handleSubmit} className="new-project-form">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe what you're researching... e.g. 'Find coworking spaces in Cape Town near Sea Point with printer, gym, coffee, monitor storage, wide opening hours'"
          rows={3}
          autoFocus
        />
        <button type="submit" disabled={createMutation.isPending || !prompt.trim()}>
          {createMutation.isPending ? 'Starting...' : 'Start Research'}
        </button>
      </form>

      {isLoading && <p className="loading">Loading projects...</p>}

      <div className="project-list">
        {projects?.map((p) => <ProjectCard key={p.id} project={p} />)}
        {projects?.length === 0 && (
          <p className="empty">No projects yet. Start one above.</p>
        )}
      </div>
    </div>
  )
}

function timeSince(dateStr: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(dateStr).getTime()) / 1000
  )
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
