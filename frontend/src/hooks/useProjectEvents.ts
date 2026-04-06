import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { api } from '../api/client'

interface EventMessage {
  event: string
  data: Record<string, unknown>
}

export function useProjectEvents(projectId: string | undefined) {
  const queryClient = useQueryClient()
  const [events, setEvents] = useState<EventMessage[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)
  const loadedRef = useRef(false)

  // Load persisted events on mount / project change
  useEffect(() => {
    if (!projectId) return
    loadedRef.current = true

    void api.getActivityLog(projectId).then((log) => {
      const persisted = log.map((e) => ({ event: e.event, data: e.data }))
      if (loadedRef.current) {
        setEvents(persisted)
      }
    })

    return () => {
      loadedRef.current = false
    }
  }, [projectId])

  // SSE for live events
  useEffect(() => {
    if (!projectId) return

    const es = new EventSource(`/api/projects/${projectId}/events`)
    esRef.current = es

    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)

    const handler = (type: string) => (e: MessageEvent) => {
      const data = JSON.parse(e.data) as Record<string, unknown>
      const msg: EventMessage = { event: type, data }
      setEvents((prev) => [...prev, msg])

      if (
        type === 'listing_discovered' ||
        type === 'listing_updated' ||
        type === 'complete' ||
        type === 'dedup_complete'
      ) {
        void queryClient.invalidateQueries({
          queryKey: ['listings', projectId],
        })
      }
      if (type === 'parse_complete') {
        void queryClient.invalidateQueries({
          queryKey: ['requirements', projectId],
        })
        void queryClient.invalidateQueries({
          queryKey: ['project', projectId],
        })
      }
      if (type === 'phase_change' || type === 'complete' || type === 'error') {
        void queryClient.invalidateQueries({
          queryKey: ['project', projectId],
        })
        void queryClient.invalidateQueries({
          queryKey: ['stats', projectId],
        })
      }
    }

    const eventTypes = [
      'phase_change',
      'listing_discovered',
      'listing_updated',
      'search_started',
      'search_executed',
      'search_error',
      'parse_complete',
      'dedup_complete',
      'deep_started',
      'deep_researching',
      'maps_complete',
      'error',
      'complete',
    ]
    for (const t of eventTypes) {
      es.addEventListener(t, handler(t))
    }

    return () => {
      es.close()
      esRef.current = null
      setConnected(false)
    }
  }, [projectId, queryClient])

  return { events, connected }
}
