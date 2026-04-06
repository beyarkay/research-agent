export interface Project {
  id: string
  created_at: string
  updated_at: string
  prompt: string
  parsed_intent: string | null
  search_locale: string | null
  status: string
}

export interface Requirement {
  id: number
  project_id: string
  key: string
  label: string
  type: 'bool' | 'int' | 'float' | 'text' | 'enum'
  enum_options: string[] | null
  unit: string | null
  is_hard: boolean
  weight: number
  direction: string
  sort_order: number
}

export interface Listing {
  id: number
  project_id: string
  name: string
  url: string | null
  image_url: string | null
  address: string | null
  lat: number | null
  lng: number | null
  summary: string | null
  attributes: Record<string, unknown>
  raw_notes: string | null
  score: number | null
  hard_pass: boolean
  data_completeness: number
  status: string
}

export interface Fallback {
  id: number
  listing_id: number
  requirement_key: string
  resolution_name: string
  resolution_detail: string | null
  resolution_url: string | null
  distance_meters: number | null
  satisfies: boolean
}

export interface ListingsPage {
  items: Listing[]
  total: number
}

export interface ProjectStats {
  total_listings: number
  completed_listings: number
  avg_completeness: number
  total_input_tokens: number
  total_output_tokens: number
  total_searches: number
}

export interface SSEEvent {
  event: string
  data: Record<string, unknown>
}

export interface FilterState {
  filters: Record<string, string>
  sort: string
  hideFailed: boolean
}
