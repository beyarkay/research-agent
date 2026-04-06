import { useQuery } from '@tanstack/react-query'

import { api } from '../../api/client'
import type { Fallback, Listing, Requirement } from '../../types'

function mapsUrl(address: string): string {
  return `https://www.google.com/maps/search/${encodeURIComponent(address)}`
}

export function ListingDetail({
  listing,
  requirements,
  projectId,
}: {
  listing: Listing
  requirements: Requirement[]
  projectId: string
}) {
  const { data: fallbacks } = useQuery({
    queryKey: ['fallbacks', projectId, listing.id],
    queryFn: () => api.getFallbacks(projectId, listing.id),
  })

  const filledCount = requirements.filter(
    (r) => listing.attributes[r.key] !== null && listing.attributes[r.key] !== undefined
  ).length

  return (
    <div className="listing-detail">
      <div className="detail-header">
        <div className="detail-title-row">
          <h2>{listing.name}</h2>
          {listing.score != null && (
            <div className="detail-score" data-score={scoreLevel(listing.score)}>
              {Math.round(listing.score)}/100
            </div>
          )}
        </div>
        {listing.address && (
          <p className="detail-address">
            <a href={mapsUrl(listing.address)} target="_blank" rel="noopener noreferrer">
              {listing.address} &rarr;
            </a>
          </p>
        )}
        <div className="detail-meta">
          <span>
            Data: {filledCount}/{requirements.length} verified
          </span>
          {listing.url && (
            <a href={listing.url} target="_blank" rel="noopener noreferrer">
              Website &rarr;
            </a>
          )}
          {listing.hard_pass && <span className="hard-fail-badge">Fails hard requirement</span>}
        </div>
      </div>

      {listing.image_url && (
        <img src={listing.image_url} alt="" className="detail-image" loading="lazy" />
      )}

      {listing.summary && (
        <div className="detail-summary">
          <p>{listing.summary}</p>
        </div>
      )}

      <div className="attribute-grid">
        <h3>Requirements</h3>
        {requirements.map((req) => (
          <AttributeRow
            key={req.key}
            requirement={req}
            value={listing.attributes[req.key]}
            fallbacks={fallbacks?.filter((f) => f.requirement_key === req.key) ?? []}
          />
        ))}
      </div>

      {listing.raw_notes && (
        <details className="raw-notes">
          <summary>Research Notes</summary>
          <pre>{listing.raw_notes.split('---CONFIDENCE---')[0].trim()}</pre>
        </details>
      )}
    </div>
  )
}

function AttributeRow({
  requirement,
  value,
  fallbacks,
}: {
  requirement: Requirement
  value: unknown
  fallbacks: Fallback[]
}) {
  const isNull = value === null || value === undefined
  const isBoolFail = requirement.type === 'bool' && value === false

  return (
    <div className={`attr-row ${requirement.is_hard ? 'hard' : 'soft'}`}>
      <span className={`attr-value ${isNull ? 'unknown' : ''} ${isBoolFail ? 'fail' : ''}`}>
        {formatAttrValue(value, requirement)}
      </span>
      <span className="attr-icon">
        {isNull ? '?' : isBoolFail ? '\u2717' : '\u2713'}
      </span>
      <span className="attr-label" title={requirement.label}>
        {requirement.is_hard && <span className="hard-marker">*</span>}
        {shortLabel(requirement.label)}
      </span>
      {fallbacks.length > 0 && (
        <div className="fallback-list">
          {fallbacks.map((fb) => (
            <div key={fb.id} className="fallback-item">
              <span className="fallback-name">{fb.resolution_name}</span>
              {fb.resolution_detail && (
                <span className="fallback-detail">{fb.resolution_detail}</span>
              )}
              {fb.resolution_url && (
                <a href={fb.resolution_url} target="_blank" rel="noopener noreferrer">
                  &rarr;
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function shortLabel(label: string): string {
  // Truncate long labels, full text available on hover via title attr
  if (label.length <= 25) return label
  return label.slice(0, 22) + '...'
}

function formatAttrValue(val: unknown, req: Requirement): string {
  if (val === null || val === undefined) return '—'
  if (req.type === 'bool') return val ? 'Yes' : 'No'
  if (req.type === 'int' || req.type === 'float') {
    const num = Number(val)
    const formatted = req.type === 'float' ? num.toLocaleString() : String(num)
    return req.unit ? `${formatted} ${req.unit}` : formatted
  }
  return String(val)
}

function scoreLevel(score: number): string {
  if (score >= 75) return 'high'
  if (score >= 50) return 'mid'
  return 'low'
}
