import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { useFilters } from '../hooks/useFilters'
import { useProjectEvents } from '../hooks/useProjectEvents'
import { ActivityLog } from './ActivityLog'
import { FilterSortBar } from './FilterSortBar/FilterSortBar'
import { ListingDetail } from './ListingDetail/ListingDetail'
import { ListingList } from './ListingList/ListingList'
import { ProjectHeader } from './ProjectHeader'

export function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const [showLog, setShowLog] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const addUrlRef = useRef<HTMLInputElement>(null)
  const filters = useFilters()
  const { selectedId, setSelectedId } = filters
  const { events } = useProjectEvents(id)
  const queryClient = useQueryClient()

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

  const isDone = project?.status === 'done' || project?.status === 'error'

  const { data: stats } = useQuery({
    queryKey: ['stats', id],
    queryFn: () => api.getProjectStats(id!),
    enabled: !!id,
    refetchInterval: isDone ? false : 5000,
  })

  const { data: listingsPage } = useQuery({
    queryKey: ['listings', id, filters.queryParams],
    queryFn: () => api.getListings(id!, filters.queryParams),
    enabled: !!id,
    refetchInterval: isDone ? false : 5000,
  })

  const resumeMutation = useMutation({
    mutationFn: () => api.resumeProject(id!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project', id] })
    },
  })

  const addListingMutation = useMutation({
    mutationFn: (url: string) => api.addListing(id!, { url }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['listings', id] })
      setShowAddForm(false)
    },
  })

  if (!id) return null

  const listings = listingsPage?.items ?? []
  const selectedListing = selectedId
    ? listings.find((l) => l.id === selectedId) ?? null
    : null

  const canResume = project?.status === 'done' || project?.status === 'error'

  return (
    <div className="page project-page">
      <div className="project-page-top">
        <Link to="/" className="back-link">&larr; Projects</Link>
        <ProjectHeader project={project ?? null} stats={stats ?? null} />
        <div className="top-actions">
          {canResume && (
            <button
              className="btn-sm"
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
            >
              {resumeMutation.isPending ? 'Resuming...' : 'Resume'}
            </button>
          )}
          <button
            className="btn-sm"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            + Add
          </button>
          <button
            className="btn-sm"
            onClick={() => setShowLog(!showLog)}
          >
            {showLog ? 'Hide Log' : 'Log'}
          </button>
        </div>
      </div>

      {showAddForm && (
        <form
          className="add-listing-form"
          onSubmit={(e) => {
            e.preventDefault()
            const url = addUrlRef.current?.value?.trim()
            if (url) addListingMutation.mutate(url)
          }}
        >
          <input
            ref={addUrlRef}
            type="url"
            placeholder="Paste website URL to research..."
            autoFocus
          />
          <button type="submit" disabled={addListingMutation.isPending}>
            {addListingMutation.isPending ? 'Adding...' : 'Research'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => setShowAddForm(false)}>
            Cancel
          </button>
        </form>
      )}

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
              originAddress={project?.origin_address}
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
