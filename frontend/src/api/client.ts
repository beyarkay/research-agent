import type {
  AttributeDistribution,
  Fallback,
  Listing,
  ListingsPage,
  Project,
  ProjectStats,
  Requirement,
} from '../types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  // Projects
  createProject: (prompt: string) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    }),

  listProjects: () => request<Project[]>('/projects'),

  getProject: (id: string) => request<Project>(`/projects/${id}`),

  deleteProject: (id: string) =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),

  getProjectStats: (id: string) =>
    request<ProjectStats>(`/projects/${id}/stats`),

  resumeProject: (id: string) =>
    request<Project>(`/projects/${id}/resume`, { method: 'POST' }),

  // Requirements
  getRequirements: (projectId: string) =>
    request<Requirement[]>(`/projects/${projectId}/requirements`),

  updateRequirement: (
    projectId: string,
    key: string,
    update: { is_hard?: boolean; weight?: number; direction?: string }
  ) =>
    request<Requirement>(`/projects/${projectId}/requirements/${key}`, {
      method: 'PATCH',
      body: JSON.stringify(update),
    }),

  // Listings
  getListings: (projectId: string, params?: Record<string, string>) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : ''
    return request<ListingsPage>(
      `/projects/${projectId}/listings${query}`
    )
  },

  getListing: (projectId: string, listingId: number) =>
    request<Listing>(`/projects/${projectId}/listings/${listingId}`),

  getFallbacks: (projectId: string, listingId: number) =>
    request<Fallback[]>(
      `/projects/${projectId}/listings/${listingId}/fallbacks`
    ),

  getDistributions: (projectId: string) =>
    request<AttributeDistribution[]>(`/projects/${projectId}/distributions`),

  updateListing: (
    projectId: string,
    listingId: number,
    data: { user_status?: string; user_notes?: string }
  ) =>
    request<Listing>(`/projects/${projectId}/listings/${listingId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  addListing: (
    projectId: string,
    data: { url: string; name?: string; address?: string; notes?: string }
  ) =>
    request<Listing>(`/projects/${projectId}/listings/add`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}
