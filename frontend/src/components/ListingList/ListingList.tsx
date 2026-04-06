import type { Listing, Requirement } from '../../types'

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
  // Pick top 3 requirements for key stats display
  const keyReqs = requirements.slice(0, 4)

  return (
    <div className="listing-list">
      <div className="listing-list-header">
        <span>{total} results</span>
      </div>
      {listings.map((listing) => (
        <ListingCard
          key={listing.id}
          listing={listing}
          keyReqs={keyReqs}
          selected={listing.id === selectedId}
          onClick={() => onSelect(listing.id)}
        />
      ))}
      {listings.length === 0 && (
        <p className="empty">No listings match your filters.</p>
      )}
    </div>
  )
}

function ListingCard({
  listing,
  keyReqs,
  selected,
  onClick,
}: {
  listing: Listing
  keyReqs: Requirement[]
  selected: boolean
  onClick: () => void
}) {
  const completeParts = Math.round(listing.data_completeness * keyReqs.length)
  const totalReqs = keyReqs.length

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
            <div className="card-address">{listing.address}</div>
          )}
        </div>
        <div className="card-score-area">
          {listing.score != null && (
            <div className="card-score" data-score={scoreLevel(listing.score)}>
              {Math.round(listing.score)}
            </div>
          )}
          <div className="card-completeness">
            {completeParts}/{totalReqs}
          </div>
          {listing.status !== 'complete' && listing.status !== 'error' && (
            <div className="card-spinner" title={listing.status} />
          )}
        </div>
      </div>
      <div className="card-stats">
        {keyReqs.map((req) => {
          const val = listing.attributes[req.key]
          return (
            <span key={req.key} className="stat-pill" data-type={req.type}>
              <span className="stat-label">{req.label}</span>
              <span className="stat-value">{formatValue(val, req)}</span>
            </span>
          )
        })}
      </div>
    </div>
  )
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
