import type { Requirement } from '../../types'
import type { useFilters } from '../../hooks/useFilters'

type Filters = ReturnType<typeof useFilters>

export function FilterSortBar({
  requirements,
  filters,
}: {
  requirements: Requirement[]
  filters: Filters
}) {
  return (
    <div className="filter-bar">
      <div className="filter-item">
        <label>Name</label>
        <input
          type="text"
          value={filters.filters['_name'] ?? ''}
          placeholder="Search..."
          onChange={(e) => filters.setFilter('_name', e.target.value || null)}
        />
      </div>

      {requirements.map((req) => (
        <DynamicFilter key={req.key} requirement={req} filters={filters} />
      ))}

      <div className="filter-item">
        <label>Sort</label>
        <select
          value={filters.sort}
          onChange={(e) => filters.setSort(e.target.value)}
        >
          <option value="-score">Score (high first)</option>
          <option value="score">Score (low first)</option>
          <option value="-data_completeness">Data completeness</option>
          <option value="name">Name A-Z</option>
          {requirements
            .filter((r) => r.type === 'int' || r.type === 'float')
            .map((r) => (
              <option key={r.key} value={r.direction === 'lower_better' ? r.key : `-${r.key}`}>
                {r.label} {r.unit ? `(${r.unit})` : ''}
              </option>
            ))}
        </select>
      </div>

      <div className="filter-item">
        <label>
          <input
            type="checkbox"
            checked={filters.hideFailed}
            onChange={filters.toggleHideFailed}
          />
          {' '}Hide failed
        </label>
      </div>
    </div>
  )
}

function DynamicFilter({
  requirement,
  filters,
}: {
  requirement: Requirement
  filters: Filters
}) {
  const { key, label, type } = requirement
  const value = filters.filters[key] ?? ''

  const shortLbl = label.length > 18 ? label.slice(0, 15) + '...' : label

  switch (type) {
    case 'bool':
      return (
        <div className="filter-item" title={label}>
          <label>{shortLbl}</label>
          <select
            value={value}
            onChange={(e) => filters.setFilter(key, e.target.value || null)}
          >
            <option value="">Any</option>
            <option value="true">Yes + Unknown</option>
            <option value="strict_true">Yes only</option>
            <option value="false">No</option>
          </select>
        </div>
      )

    case 'int':
    case 'float':
      return (
        <div className="filter-item" title={label}>
          <label>
            {shortLbl}
            {requirement.unit ? ` (${requirement.unit})` : ''}
          </label>
          <div className="numeric-filter">
            <input
              type="number"
              placeholder="max"
              value={filters.filters[`${key}__lte`] ?? ''}
              onChange={(e) =>
                filters.setFilter(`${key}__lte`, e.target.value || null)
              }
            />
          </div>
        </div>
      )

    case 'enum':
      return (
        <div className="filter-item" title={label}>
          <label>{shortLbl}</label>
          <select
            value={value}
            onChange={(e) => filters.setFilter(key, e.target.value || null)}
          >
            <option value="">Any</option>
            {requirement.enum_options?.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      )

    case 'text':
      return (
        <div className="filter-item" title={label}>
          <label>{shortLbl}</label>
          <input
            type="text"
            value={value}
            placeholder="Search..."
            onChange={(e) => filters.setFilter(key, e.target.value || null)}
          />
        </div>
      )

    default:
      return null
  }
}
