/**
 * Tiny inline SVG histogram with nicely rounded bin edges.
 * Current listing's value is highlighted with a red line.
 */

interface HistogramProps {
  values: number[]
  current: number | null
  unit?: string | null
  width?: number
  height?: number
}

const TARGET_BINS = 8
const LABEL_H = 10

/** Pick a "nice" bin size: 1, 2, 5, 10, 20, 50, 100, 200, 500, ... */
function niceStep(rawStep: number): number {
  const mag = Math.pow(10, Math.floor(Math.log10(rawStep)))
  const norm = rawStep / mag
  if (norm <= 1) return mag
  if (norm <= 2) return 2 * mag
  if (norm <= 5) return 5 * mag
  return 10 * mag
}

export function Histogram({
  values,
  current,
  unit,
  width = 140,
  height = 32,
}: HistogramProps) {
  if (values.length < 2) return null

  const rawMin = Math.min(...values)
  const rawMax = Math.max(...values)
  if (rawMin === rawMax) return null

  // Compute nice bin width and snap min/max to bin edges
  const rawStep = (rawMax - rawMin) / TARGET_BINS
  const step = niceStep(rawStep)
  const binMin = Math.floor(rawMin / step) * step
  const binMax = Math.ceil(rawMax / step) * step
  const numBins = Math.round((binMax - binMin) / step)
  const range = binMax - binMin

  const bins = new Array(numBins).fill(0) as number[]
  for (const v of values) {
    const idx = Math.min(Math.floor((v - binMin) / step), numBins - 1)
    bins[idx]++
  }

  const maxBin = Math.max(...bins)
  const barW = width / numBins
  const pad = 1
  const chartH = height - LABEL_H
  const u = unit ? ` ${unit}` : ''

  let markerX: number | null = null
  if (current !== null && current !== undefined) {
    const frac = (current - binMin) / range
    markerX = Math.max(0, Math.min(width, frac * width))
  }

  const fmt = (n: number) => {
    if (Number.isInteger(n)) return String(n)
    if (Math.abs(n) >= 100) return Math.round(n).toString()
    return n.toFixed(1)
  }

  return (
    <div className="histogram">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {bins.map((count, i) => {
          const barH = maxBin > 0 ? (count / maxBin) * (chartH - 2) : 0
          const lo = binMin + i * step
          const hi = lo + step
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
        <text x={0} y={height} fontSize={8} fill="#999" textAnchor="start">
          {fmt(binMin)}
        </text>
        <text x={width} y={height} fontSize={8} fill="#999" textAnchor="end">
          {fmt(binMax)}{u}
        </text>
      </svg>
    </div>
  )
}
