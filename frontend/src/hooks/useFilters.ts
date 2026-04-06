import { useCallback, useMemo, useState } from 'react'

import type { FilterState } from '../types'

export function useFilters() {
  const [state, setState] = useState<FilterState>({
    filters: {},
    sort: '-score',
    hideFailed: false,
  })

  const setFilter = useCallback((key: string, value: string | null) => {
    setState((prev) => {
      const next = { ...prev.filters }
      if (value === null || value === '') {
        delete next[key]
      } else {
        next[key] = value
      }
      return { ...prev, filters: next }
    })
  }, [])

  const setSort = useCallback((sort: string) => {
    setState((prev) => ({ ...prev, sort }))
  }, [])

  const toggleHideFailed = useCallback(() => {
    setState((prev) => ({ ...prev, hideFailed: !prev.hideFailed }))
  }, [])

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
    queryParams,
  }
}
