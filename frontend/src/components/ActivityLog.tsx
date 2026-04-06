import { useEffect, useRef } from 'react'

interface EventMessage {
  event: string
  data: Record<string, unknown>
}

export function ActivityLog({ events }: { events: EventMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  return (
    <div className="activity-log">
      <h3>Activity Log ({events.length} events)</h3>
      <div className="log-entries">
        {events.length === 0 && (
          <p className="empty">Waiting for events...</p>
        )}
        {events.map((e, i) => (
          <div key={i} className={`log-entry log-${eventSeverity(e.event)}`}>
            <span className="log-event">{e.event}</span>
            <span className="log-data">
              {formatEventData(e)}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function eventSeverity(event: string): string {
  if (event === 'error' || event === 'search_error') return 'error'
  if (event === 'complete') return 'success'
  return 'info'
}

function formatEventData(e: EventMessage): string {
  switch (e.event) {
    case 'phase_change':
      return String(e.data.message ?? e.data.phase ?? '')

    case 'parse_complete':
      return `Extracted ${e.data.requirements_count} requirements, generated ${e.data.queries_count} search queries`

    case 'search_started':
      return `Searching: "${e.data.query}"`

    case 'search_executed': {
      const names = (e.data.names as string[]) ?? []
      const namesStr = names.length > 0 ? ` → ${names.join(', ')}` : ''
      return `"${e.data.query}" found ${e.data.results} results (${e.data.duration_s}s, ${e.data.tokens} tokens)${namesStr}`
    }

    case 'search_error':
      return `Search failed: "${e.data.query}" — ${e.data.error}`

    case 'listing_discovered':
      return `Found: ${e.data.name}${e.data.url ? ` (${e.data.url})` : ''}`

    case 'dedup_complete': {
      const removed = (e.data.removed_names as string[]) ?? []
      if (removed.length === 0) return `No duplicates found`
      return `Removed ${e.data.removed} duplicates (${e.data.groups} groups): ${removed.join(', ')}`
    }

    case 'deep_started': {
      const names = (e.data.names as string[]) ?? []
      return `Starting deep research on ${e.data.total} listings: ${names.join(', ')}`
    }

    case 'deep_researching':
      return `Researching: ${e.data.name}...`

    case 'listing_updated':
      return `${e.data.name}: ${e.data.filled} attributes filled (${e.data.duration_s}s, ${e.data.tokens} tokens) — ${e.data.summary}`

    case 'error':
      return `ERROR: ${e.data.message}`

    case 'complete':
      return `Done! ${e.data.total_listings} listings researched.`

    default:
      return JSON.stringify(e.data)
  }
}
