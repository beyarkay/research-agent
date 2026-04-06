import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import type { FilterState } from '../types'

/**
 * Filter/sort state synced to URL search params.
 * e.g. /projects/abc?f.has_coffee=true&sort=-score&hide_failed=1&selected=42
 */
export function useFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Parse state from URL
  const state: FilterState = useMemo(() => {
    const filters: Record<string, string> = {}
    for (const [key, value] of searchParams.entries()) {
      if (key.startsWith('f.')) {
        filters[key.slice(2)] = value
      }
    }
    return {
      filters,
      sort: searchParams.get('sort') ?? '-score',
      hideFailed: searchParams.get('hide_failed') === '1',
    }
  }, [searchParams])

  const _updateParams = useCallback(
    (updater: (params: URLSearchParams) => void) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        updater(next)
        return next
      }, { replace: true })
    },
    [setSearchParams]
  )

  const setFilter = useCallback(
    (key: string, value: string | null) => {
      _updateParams((p) => {
        if (value === null || value === '') {
          p.delete(`f.${key}`)
        } else {
          p.set(`f.${key}`, value)
        }
      })
    },
    [_updateParams]
  )

  const setSort = useCallback(
    (sort: string) => {
      _updateParams((p) => {
        if (sort === '-score') {
          p.delete('sort')
        } else {
          p.set('sort', sort)
        }
      })
    },
    [_updateParams]
  )

  const toggleHideFailed = useCallback(() => {
    _updateParams((p) => {
      if (p.get('hide_failed') === '1') {
        p.delete('hide_failed')
      } else {
        p.set('hide_failed', '1')
      }
    })
  }, [_updateParams])

  // Selected listing ID (also in URL)
  const selectedId = searchParams.get('selected')
    ? Number(searchParams.get('selected'))
    : null

  const setSelectedId = useCallback(
    (id: number | null) => {
      _updateParams((p) => {
        if (id === null) {
          p.delete('selected')
        } else {
          p.set('selected', String(id))
        }
      })
    },
    [_updateParams]
  )

  const queryParams = useMemo(() => {
    const params: Record<string, string> = {}
    for (const [key, value] of Object.entries(state.filters)) {
      params[`filter[${key}]`] = value
    }
    if (state.sort) params['sort'] = state.sort
    if (state.hideFailed) params['hide_failed'] = 'true'
    return params
  }, [state])

  return {
    ...state,
    setFilter,
    setSort,
    toggleHideFailed,
    selectedId,
    setSelectedId,
    queryParams,
  }
}
