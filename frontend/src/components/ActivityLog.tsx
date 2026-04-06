interface EventMessage {
  event: string
  data: Record<string, unknown>
}

export function ActivityLog({ events }: { events: EventMessage[] }) {
  return (
    <div className="activity-log">
      <h3>Activity Log</h3>
      <div className="log-entries">
        {events.length === 0 && (
          <p className="empty">No events yet.</p>
        )}
        {events.map((e, i) => (
          <div key={i} className="log-entry">
            <span className="log-event">{e.event}</span>
            <span className="log-data">
              {formatEventData(e)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatEventData(e: EventMessage): string {
  switch (e.event) {
    case 'phase_change':
      return String(e.data.message ?? e.data.phase ?? '')
    case 'listing_discovered':
      return String(e.data.name ?? '')
    case 'listing_updated':
      return `#${e.data.id} updated`
    case 'search_executed':
      return `"${e.data.query}" (${e.data.results} results)`
    case 'parse_complete':
      return `${e.data.requirements_count} requirements, ${e.data.queries_count} queries`
    case 'error':
      return String(e.data.message ?? 'Unknown error')
    case 'complete':
      return `${e.data.total_listings} listings total`
    default:
      return JSON.stringify(e.data)
  }
}
