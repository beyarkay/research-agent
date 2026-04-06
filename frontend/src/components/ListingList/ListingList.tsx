import type { Listing, Requirement } from '../../types'

function extractVal(attr: unknown): unknown {
  if (attr === null || attr === undefined) return null
  if (typeof attr === 'object' && !Array.isArray(attr)) {
    const obj = attr as Record<string, unknown>
    if ('value' in obj) return obj.value
  }
  return attr
}


export function ListingList({
  listings,
  total,
  requirements,
  selectedId,
  onSelect,
}: {
  listings: Listing[]
  total: number
  requirements: Requirement[]
  selectedId: number | null
  onSelect: (id: number) => void
}) {
  const keyReqs = requirements.slice(0, 4)

  return (
    <div className="listing-list">
      <div className="listing-list-header">
        <span>{total} results</span>
      </div>
      <div className="listing-list-scroll">
        {listings.map((listing) => (
          <ListingCard
            key={listing.id}
            listing={listing}
            keyReqs={keyReqs}
            allReqs={requirements}
            selected={listing.id === selectedId}
            onClick={() => onSelect(listing.id)}
          />
        ))}
        {listings.length === 0 && (
          <p className="empty">No listings match your filters.</p>
        )}
      </div>
    </div>
  )
}

function ListingCard({
  listing,
  keyReqs,
  allReqs,
  selected,
  onClick,
}: {
  listing: Listing
  keyReqs: Requirement[]
  allReqs: Requirement[]
  selected: boolean
  onClick: () => void
}) {
  const allReqCount = allReqs.length
  // Count filled attributes across ALL requirements
  const filledCount = Object.values(listing.attributes).filter((v) => {
    const extracted = extractVal(v)
    return extracted !== null && extracted !== undefined
  }).length

  // Get human-readable names for hard failures
  const failureLabels = listing.hard_failures
    .map((key) => allReqs.find((r) => r.key === key)?.label ?? key)
    .join(', ')

  const userClass = listing.user_status === 'favourite' ? 'fav' :
    listing.user_status === 'minimized' ? 'minimized' : ''
  const firstNote = listing.user_notes?.split('\n')[0] || ''

  return (
    <div
      className={`listing-card ${selected ? 'selected' : ''} ${listing.hard_pass ? 'failed' : ''} ${userClass}`}
      onClick={onClick}
    >
      <div className="card-top">
        {listing.image_url && (
          <img
            src={listing.image_url}
            alt=""
            className="card-thumb"
            loading="lazy"
          />
        )}
        <div className="card-info">
          <div className="card-name">{listing.name}</div>
          {listing.address && (
            <div className="card-address">{listing.address}</div>
          )}
        </div>
        <div className="card-score-area">
          {listing.score != null && (
            <div className="card-score" data-score={scoreLevel(listing.score)}>
              {Math.round(listing.score)}
            </div>
          )}
          <div className="card-completeness" title={`${filledCount} of ${allReqCount} requirements have data`}>
            {filledCount}/{allReqCount}
          </div>
          {listing.status !== 'complete' && listing.status !== 'error' && (
            <div className="card-spinner" title={listing.status} />
          )}
        </div>
      </div>
      {failureLabels && (
        <div className="card-failures">Fails: {failureLabels}</div>
      )}
      <div className="card-stats">
        {keyReqs.map((req) => {
          const val = extractVal(listing.attributes[req.key])
          return (
            <span key={req.key} className="stat-pill" data-type={req.type} title={req.label}>
              <span className="stat-label">{shortLabel(req.label)}</span>
              <span className="stat-value">{formatValue(val, req)}</span>
            </span>
          )
        })}
      {firstNote && <div className="card-note">{firstNote}</div>}
      </div>
    </div>
  )
}

function shortLabel(label: string): string {
  if (label.length <= 12) return label
  return label.slice(0, 10) + '..'
}

function formatValue(val: unknown, req: Requirement): string {
  if (val === null || val === undefined) return '?'
  if (req.type === 'bool') return val ? '\u2713' : '\u2717'
  if (req.type === 'int' || req.type === 'float') {
    const num = Number(val)
    const formatted = req.type === 'float' ? num.toFixed(0) : String(num)
    return req.unit ? `${formatted} ${req.unit}` : formatted
  }
  return String(val)
}

function scoreLevel(score: number): string {
  if (score >= 75) return 'high'
  if (score >= 50) return 'mid'
  return 'low'
}
