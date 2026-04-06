import { describe, it, expect, vi, beforeEach } from 'vitest'

import { api } from './client'

const mockFetch = vi.fn()
globalThis.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
})

describe('api client', () => {
  it('creates a project', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({
        id: 'abc123',
        prompt: 'test',
        status: 'pending',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        parsed_intent: null,
        search_locale: null,
      }),
    })

    const result = await api.createProject('test')
    expect(result.id).toBe('abc123')
    expect(mockFetch).toHaveBeenCalledWith('/api/projects', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ prompt: 'test' }),
    }))
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: async () => 'Not found',
    })

    await expect(api.getProject('bad-id')).rejects.toThrow('404')
  })

  it('handles delete (204)', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    })

    const result = await api.deleteProject('abc')
    expect(result).toBeUndefined()
  })

  it('builds listing query params', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0 }),
    })

    await api.getListings('proj1', {
      'filter[has_coffee]': 'true',
      sort: '-score',
    })

    const callUrl = mockFetch.mock.calls[0][0] as string
    expect(callUrl).toContain('filter%5Bhas_coffee%5D=true')
    expect(callUrl).toContain('sort=-score')
  })
})
