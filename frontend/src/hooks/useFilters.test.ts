import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import { useFilters } from './useFilters'

describe('useFilters', () => {
  it('starts with default state', () => {
    const { result } = renderHook(() => useFilters())
    expect(result.current.sort).toBe('-score')
    expect(result.current.hideFailed).toBe(false)
    expect(result.current.filters).toEqual({})
  })

  it('sets and clears filters', () => {
    const { result } = renderHook(() => useFilters())

    act(() => result.current.setFilter('has_coffee', 'true'))
    expect(result.current.filters).toEqual({ has_coffee: 'true' })

    act(() => result.current.setFilter('has_coffee', null))
    expect(result.current.filters).toEqual({})
  })

  it('builds query params', () => {
    const { result } = renderHook(() => useFilters())

    act(() => {
      result.current.setFilter('has_coffee', 'true')
      result.current.setSort('-price')
      result.current.toggleHideFailed()
    })

    expect(result.current.queryParams).toEqual({
      'filter[has_coffee]': 'true',
      sort: '-price',
      hide_failed: 'true',
    })
  })

  it('toggles hideFailed', () => {
    const { result } = renderHook(() => useFilters())

    act(() => result.current.toggleHideFailed())
    expect(result.current.hideFailed).toBe(true)

    act(() => result.current.toggleHideFailed())
    expect(result.current.hideFailed).toBe(false)
  })
})
