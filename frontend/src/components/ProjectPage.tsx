import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { useFilters } from '../hooks/useFilters'
import { useProjectEvents } from '../hooks/useProjectEvents'
import { ActivityLog } from './ActivityLog'
import { FilterSortBar } from './FilterSortBar/FilterSortBar'
import { ListingDetail } from './ListingDetail/ListingDetail'
import { ListingList } from './ListingList/ListingList'
import { ProjectHeader } from './ProjectHeader'
import { RefineForm } from './RefineForm'

export function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showLog, setShowLog] = useState(false)
  const [showRefine, setShowRefine] = useState(false)
  const filters = useFilters()
  const { events } = useProjectEvents(id)

  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => api.getProject(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && status !== 'done' && status !== 'error' ? 3000 : false
    },
  })

  const { data: requirements } = useQuery({
    queryKey: ['requirements', id],
    queryFn: () => api.getRequirements(id!),
    enabled: !!id,
  })

  const { data: stats } = useQuery({
    queryKey: ['stats', id],
    queryFn: () => api.getProjectStats(id!),
    enabled: !!id,
    refetchInterval: () => {
      const pStatus = project?.status
      return pStatus && pStatus !== 'done' && pStatus !== 'error'
        ? 5000
        : false
    },
  })

  const { data: listingsPage } = useQuery({
    queryKey: ['listings', id, filters.queryParams],
    queryFn: () => api.getListings(id!, filters.queryParams),
    enabled: !!id,
    refetchInterval: () => {
      const pStatus = project?.status
      return pStatus && pStatus !== 'done' && pStatus !== 'error'
        ? 5000
        : false
    },
  })

  if (!id) return null

  const listings = listingsPage?.items ?? []
  const selectedListing = selectedId
    ? listings.find((l) => l.id === selectedId) ?? null
    : null

  return (
    <div className="page project-page">
      <div className="project-page-top">
        <Link to="/" className="back-link">&larr; Projects</Link>
        <ProjectHeader project={project ?? null} stats={stats ?? null} />
        <div className="top-actions">
          <button
            className="btn-sm"
            onClick={() => setShowRefine(!showRefine)}
          >
            Refine
          </button>
          <button
            className="btn-sm"
            onClick={() => setShowLog(!showLog)}
          >
            {showLog ? 'Hide Log' : 'Activity Log'}
          </button>
        </div>
      </div>

      {showRefine && <RefineForm projectId={id} onClose={() => setShowRefine(false)} />}

      <FilterSortBar
        requirements={requirements ?? []}
        filters={filters}
      />

      <div className="split-layout">
        <div className="split-left">
          <ListingList
            listings={listings}
            total={listingsPage?.total ?? 0}
            requirements={requirements ?? []}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>
        <div className="split-right">
          {selectedListing ? (
            <ListingDetail
              listing={selectedListing}
              requirements={requirements ?? []}
              projectId={id}
            />
          ) : (
            <div className="detail-empty">
              <p>Select a listing to view details</p>
            </div>
          )}
        </div>
      </div>

      {showLog && <ActivityLog events={events} />}
    </div>
  )
}
