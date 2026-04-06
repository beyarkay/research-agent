import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useFilters } from './useFilters'

function wrapper({ children }: { children: ReactNode }) {
  return MemoryRouter({ children, initialEntries: ['/projects/test123'] })
}

describe('useFilters', () => {
  it('starts with default state', () => {
    const { result } = renderHook(() => useFilters(), { wrapper })
    expect(result.current.sort).toBe('-score')
    expect(result.current.hideFailed).toBe(false)
    expect(result.current.filters).toEqual({})
    expect(result.current.selectedId).toBeNull()
  })

  it('sets and clears filters', () => {
    const { result } = renderHook(() => useFilters(), { wrapper })

    act(() => result.current.setFilter('has_coffee', 'true'))
    expect(result.current.filters).toEqual({ has_coffee: 'true' })

    act(() => result.current.setFilter('has_coffee', null))
    expect(result.current.filters).toEqual({})
  })

  it('builds query params', () => {
    const { result } = renderHook(() => useFilters(), { wrapper })

    act(() => result.current.setFilter('has_coffee', 'true'))
    act(() => result.current.setSort('-price'))
    act(() => result.current.toggleHideFailed())

    expect(result.current.queryParams['filter[has_coffee]']).toBe('true')
    expect(result.current.queryParams['sort']).toBe('-price')
    expect(result.current.queryParams['hide_failed']).toBe('true')
  })

  it('toggles hideFailed', () => {
    const { result } = renderHook(() => useFilters(), { wrapper })

    act(() => result.current.toggleHideFailed())
    expect(result.current.hideFailed).toBe(true)

    act(() => result.current.toggleHideFailed())
    expect(result.current.hideFailed).toBe(false)
  })

  it('tracks selected listing ID', () => {
    const { result } = renderHook(() => useFilters(), { wrapper })

    act(() => result.current.setSelectedId(42))
    expect(result.current.selectedId).toBe(42)

    act(() => result.current.setSelectedId(null))
    expect(result.current.selectedId).toBeNull()
  })
})
