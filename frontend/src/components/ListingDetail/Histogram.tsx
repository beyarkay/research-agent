/**
 * Tiny inline SVG histogram showing the distribution of a numeric attribute.
 * The current listing's value is highlighted with a red line.
 */

interface HistogramProps {
  values: number[]
  current: number | null
  unit?: string | null
  width?: number
  height?: number
}

const BINS = 10

export function Histogram({
  values,
  current,
  unit,
  width = 120,
  height = 28,
}: HistogramProps) {
  if (values.length < 2) return null

  const min = Math.min(...values)
  const max = Math.max(...values)
  if (min === max) return null

  const range = max - min
  const binWidth = range / BINS
  const bins = new Array(BINS).fill(0) as number[]

  for (const v of values) {
    const idx = Math.min(Math.floor((v - min) / binWidth), BINS - 1)
    bins[idx]++
  }

  const maxBin = Math.max(...bins)
  const barW = width / BINS
  const pad = 1

  // Where does the current value fall?
  let markerX: number | null = null
  if (current !== null && current !== undefined) {
    const frac = (current - min) / range
    markerX = Math.max(0, Math.min(width, frac * width))
  }

  return (
    <div className="histogram" title={`${values.length} values, ${min}–${max}${unit ? ' ' + unit : ''}`}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {bins.map((count, i) => {
          const barH = maxBin > 0 ? (count / maxBin) * (height - 2) : 0
          return (
            <rect
              key={i}
              x={i * barW + pad / 2}
              y={height - barH}
              width={barW - pad}
              height={barH}
              fill="#ccc"
            />
          )
        })}
        {markerX !== null && (
          <line
            x1={markerX}
            y1={0}
            x2={markerX}
            y2={height}
            stroke="#dc2626"
            strokeWidth={2}
          />
        )}
      </svg>
    </div>
  )
}
