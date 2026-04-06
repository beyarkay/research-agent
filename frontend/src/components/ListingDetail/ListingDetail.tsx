import { useQuery } from '@tanstack/react-query'

import { api } from '../../api/client'
import type { Fallback, Listing, Requirement } from '../../types'

function mapsUrl(address: string): string {
  return `https://www.google.com/maps/search/${encodeURIComponent(address)}`
}

/** Extract value from plain or structured attribute */
function extractValue(attr: unknown): unknown {
  if (attr === null || attr === undefined) return null
  if (typeof attr === 'object' && !Array.isArray(attr) && attr !== null) {
    const obj = attr as Record<string, unknown>
    if ('value' in obj) return obj.value
  }
  return attr
}

/** Extract source URL from structured attribute */
function extractSource(attr: unknown): string | null {
  if (typeof attr === 'object' && attr !== null && !Array.isArray(attr)) {
    const obj = attr as Record<string, unknown>
    if (typeof obj.source === 'string') return obj.source
  }
  return null
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

  const filledCount = requirements.filter((r) => {
    const val = extractValue(listing.attributes[r.key])
    return val !== null && val !== undefined
  }).length

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
            rawAttr={listing.attributes[req.key]}
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
  rawAttr,
  fallbacks,
}: {
  requirement: Requirement
  rawAttr: unknown
  fallbacks: Fallback[]
}) {
  const value = extractValue(rawAttr)
  const source = extractSource(rawAttr)
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
      {source && (
        <a className="attr-source" href={source} target="_blank" rel="noopener noreferrer" title={source}>
          src
        </a>
      )}
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
  if (label.length <= 25) return label
  return label.slice(0, 22) + '...'
}

function formatAttrValue(val: unknown, req: Requirement): string {
  if (val === null || val === undefined) return '\u2014'

  // Multi-tier values (array of {tier, amount})
  if (Array.isArray(val)) {
    const tiers = val as Array<Record<string, unknown>>
    return tiers
      .map((t) => {
        const amount = t.amount ?? t.price ?? t.value
        const tier = t.tier ?? t.label ?? t.name ?? ''
        const unit = req.unit ? ` ${req.unit}` : ''
        return `${tier}: ${amount}${unit}`
      })
      .join(' · ')
  }

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
