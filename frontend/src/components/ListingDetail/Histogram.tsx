/**
 * Tiny inline SVG histogram showing the distribution of a numeric attribute.
 * The current listing's value is highlighted with a red line.
 * Shows min/max labels and bar tooltips on hover.
 */

interface HistogramProps {
  values: number[]
  current: number | null
  unit?: string | null
  width?: number
  height?: number
}

const BINS = 10
const LABEL_H = 10

export function Histogram({
  values,
  current,
  unit,
  width = 140,
  height = 32,
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
  const chartH = height - LABEL_H
  const u = unit ? ` ${unit}` : ''

  // Where does the current value fall?
  let markerX: number | null = null
  if (current !== null && current !== undefined) {
    const frac = (current - min) / range
    markerX = Math.max(0, Math.min(width, frac * width))
  }

  const fmt = (n: number) => Number.isInteger(n) ? String(n) : n.toFixed(1)

  return (
    <div className="histogram">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {bins.map((count, i) => {
          const barH = maxBin > 0 ? (count / maxBin) * (chartH - 2) : 0
          const lo = min + i * binWidth
          const hi = lo + binWidth
          const title = `${count} listing${count !== 1 ? 's' : ''}: ${fmt(lo)}–${fmt(hi)}${u}`
          return (
            <rect
              key={i}
              x={i * barW + pad / 2}
              y={chartH - barH}
              width={barW - pad}
              height={barH}
              fill="#ccc"
            >
              <title>{title}</title>
            </rect>
          )
        })}
        {markerX !== null && (
          <line
            x1={markerX}
            y1={0}
            x2={markerX}
            y2={chartH}
            stroke="#dc2626"
            strokeWidth={2}
          />
        )}
        {/* Min/max labels */}
        <text x={0} y={height} fontSize={8} fill="#999" textAnchor="start">
          {fmt(min)}
        </text>
        <text x={width} y={height} fontSize={8} fill="#999" textAnchor="end">
          {fmt(max)}{u}
        </text>
      </svg>
    </div>
  )
}
