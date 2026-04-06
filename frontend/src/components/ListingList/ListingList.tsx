import type { Listing, Requirement } from '../../types'

function extractVal(attr: unknown): unknown {
  if (attr === null || attr === undefined) return null
  if (typeof attr === 'object' && !Array.isArray(attr)) {
    const obj = attr as Record<string, unknown>
    if ('value' in obj) return obj.value
  }
  return attr
}

function mapsUrl(address: string): string {
  return `https://www.google.com/maps/search/${encodeURIComponent(address)}`
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
            allReqCount={requirements.length}
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
  allReqCount,
  selected,
  onClick,
}: {
  listing: Listing
  keyReqs: Requirement[]
  allReqCount: number
  selected: boolean
  onClick: () => void
}) {
  // Count filled attributes across ALL requirements
  const filledCount = Object.values(listing.attributes).filter((v) => {
    const extracted = extractVal(v)
    return extracted !== null && extracted !== undefined
  }).length

  return (
    <div
      className={`listing-card ${selected ? 'selected' : ''} ${listing.hard_pass ? 'failed' : ''}`}
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
            <a
              className="card-address"
              href={mapsUrl(listing.address)}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              {listing.address}
            </a>
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
