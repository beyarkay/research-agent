import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef } from 'react'

import { api } from '../../api/client'
import type { AttributeDistribution, Fallback, Listing, Requirement } from '../../types'
import { Histogram } from './Histogram'

function mapsDirectionsUrl(destination: string, origin?: string | null): string {
  if (origin) {
    return `https://www.google.com/maps/dir/${encodeURIComponent(origin)}/${encodeURIComponent(destination)}`
  }
  return `https://www.google.com/maps/search/${encodeURIComponent(destination)}`
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

/** Extract per-attribute research note */
function extractNote(attr: unknown): string | null {
  if (typeof attr === 'object' && attr !== null && !Array.isArray(attr)) {
    const obj = attr as Record<string, unknown>
    if (typeof obj.note === 'string') return obj.note
  }
  return null
}

export function ListingDetail({
  listing,
  requirements,
  projectId,
  originAddress,
}: {
  listing: Listing
  requirements: Requirement[]
  projectId: string
  originAddress?: string | null
}) {
  const queryClient = useQueryClient()
  const notesRef = useRef<HTMLTextAreaElement>(null)

  const { data: fallbacks } = useQuery({
    queryKey: ['fallbacks', projectId, listing.id],
    queryFn: () => api.getFallbacks(projectId, listing.id),
  })

  const { data: distributions } = useQuery({
    queryKey: ['distributions', projectId],
    queryFn: () => api.getDistributions(projectId),
  })

  const distMap = new Map<string, AttributeDistribution>()
  for (const d of distributions ?? []) {
    distMap.set(d.key, d)
  }

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
            <a href={mapsDirectionsUrl(listing.address, originAddress)} target="_blank" rel="noopener noreferrer">
              {listing.address} {originAddress ? '(directions)' : ''} &rarr;
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
          {listing.hard_pass && listing.hard_failures.length > 0 && (
            <span className="hard-fail-badge">
              Fails: {listing.hard_failures.map((key) => {
                const req = requirements.find((r) => r.key === key)
                return req?.label ?? key
              }).join(', ')}
            </span>
          )}
        </div>
      </div>

      <div className="user-controls">
        <div className="user-buttons">
          <button
            className={`btn-sm ${listing.user_status === 'favourite' ? 'active-fav' : ''}`}
            onClick={() => {
              const next = listing.user_status === 'favourite' ? 'normal' : 'favourite'
              void api.updateListing(projectId, listing.id, { user_status: next }).then(() => {
                void queryClient.invalidateQueries({ queryKey: ['listings', projectId] })
              })
            }}
          >
            {listing.user_status === 'favourite' ? '\u2605 Fav' : '\u2606 Fav'}
          </button>
          <button
            className={`btn-sm ${listing.user_status === 'minimized' ? 'active-min' : ''}`}
            onClick={() => {
              const next = listing.user_status === 'minimized' ? 'normal' : 'minimized'
              void api.updateListing(projectId, listing.id, { user_status: next }).then(() => {
                void queryClient.invalidateQueries({ queryKey: ['listings', projectId] })
              })
            }}
          >
            {listing.user_status === 'minimized' ? 'Show' : 'Minimize'}
          </button>
        </div>
        <textarea
          ref={notesRef}
          className="user-notes"
          defaultValue={listing.user_notes}
          placeholder="Your notes..."
          rows={2}
          key={listing.id}
          onBlur={() => {
            const val = notesRef.current?.value ?? ''
            if (val !== listing.user_notes) {
              void api.updateListing(projectId, listing.id, { user_notes: val }).then(() => {
                void queryClient.invalidateQueries({ queryKey: ['listings', projectId] })
              })
            }
          }}
        />
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
            distribution={distMap.get(req.key) ?? null}
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
  distribution,
}: {
  requirement: Requirement
  rawAttr: unknown
  fallbacks: Fallback[]
  distribution: AttributeDistribution | null
}) {
  const value = extractValue(rawAttr)
  const source = extractSource(rawAttr)
  const note = extractNote(rawAttr)
  const isNull = value === null || value === undefined
  const isBoolFail = requirement.type === 'bool' && value === false

  // Extract numeric values for histogram markers (supports multi-tier)
  const numericValues: number[] = []
  if ((requirement.type === 'int' || requirement.type === 'float') && !isNull) {
    if (Array.isArray(value)) {
      for (const item of value as Array<Record<string, unknown>>) {
        const amt = item.amount ?? item.price ?? item.value
        if (amt !== null && amt !== undefined) numericValues.push(Number(amt))
      }
    } else {
      numericValues.push(Number(value))
    }
  }

  // Build tooltip: note + source
  const tooltipParts: string[] = [requirement.label]
  if (note) tooltipParts.push(note)
  if (source) tooltipParts.push(`Source: ${source}`)
  const tooltip = tooltipParts.join('\n')

  return (
    <div className={`attr-row ${requirement.is_hard ? 'hard' : 'soft'}`}>
      <span className={`attr-value ${isNull ? 'unknown' : ''} ${isBoolFail ? 'fail' : ''}`}>
        <FormatAttrValue val={value} req={requirement} />
      </span>
      <span className="attr-icon">
        {isNull ? '?' : isBoolFail ? '\u2717' : '\u2713'}
      </span>
      <span className="attr-label" data-tip={tooltip}>
        {requirement.is_hard && <span className="hard-marker">*</span>}
        {shortLabel(requirement.label)}
      </span>
      {distribution && (
        <Histogram
          values={distribution.values}
          current={numericValues}
          unit={distribution.unit}
        />
      )}
      {source && (
        <a className="attr-source" href={source} target="_blank" rel="noopener noreferrer" data-tip={source}>
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

/** Format attribute value as a React node (supports multi-line for tiers) */
function FormatAttrValue({ val, req }: { val: unknown; req: Requirement }) {
  if (val === null || val === undefined) return <>{'\u2014'}</>

  if (Array.isArray(val)) {
    const items = val as unknown[]
    // String array (e.g. ["hot_desk", "private_office"])
    if (items.length > 0 && typeof items[0] === 'string') {
      return <>{(items as string[]).join(', ')}</>
    }
    // Object array (e.g. [{tier, amount}])
    const tiers = items as Array<Record<string, unknown>>
    const u = req.unit ? ` ${req.unit}` : ''
    return (
      <span className="multi-tier">
        {tiers.map((t, i) => {
          const amount = t.amount ?? t.price ?? t.value
          const tier = t.tier ?? t.label ?? t.name ?? ''
          if (amount === undefined || amount === null) return null
          return (
            <span key={i} className="tier-line">
              {tier}: {amount}{u}
            </span>
          )
        })}
      </span>
    )
  }

  if (req.type === 'bool') return <>{val ? 'Yes' : 'No'}</>
  if (req.type === 'int' || req.type === 'float') {
    const num = Number(val)
    const formatted = req.type === 'float' ? num.toLocaleString() : String(num)
    return <>{req.unit ? `${formatted} ${req.unit}` : formatted}</>
  }
  return <>{String(val)}</>
}

function scoreLevel(score: number): string {
  if (score >= 75) return 'high'
  if (score >= 50) return 'mid'
  return 'low'
}
