from dataclasses import dataclass, field


@dataclass
class Project:
    id: str
    created_at: str
    updated_at: str
    prompt: str
    parsed_intent: str | None = None
    search_locale: str | None = None
    status: str = "pending"


@dataclass
class Requirement:
    id: int
    project_id: str
    key: str
    label: str
    type: str
    enum_options: str | None = None
    unit: str | None = None
    is_hard: bool = False
    weight: float = 1.0
    direction: str = "higher_better"
    sort_order: int = 0


@dataclass
class Listing:
    id: int
    project_id: str
    name: str
    url: str | None = None
    image_url: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    summary: str | None = None
    attributes: str = "{}"
    raw_notes: str | None = None
    score: float | None = None
    hard_pass: bool = False
    data_completeness: float = 0.0
    status: str = "discovered"


@dataclass
class SearchQuery:
    id: int
    project_id: str
    query_text: str
    phase: str
    status: str = "pending"
    result_count: int | None = None
    created_at: str = ""


@dataclass
class SearchResult:
    id: int
    search_query_id: int
    listing_id: int | None
    title: str | None
    url: str
    snippet: str | None
    rank: int | None = None


@dataclass
class Fallback:
    id: int
    listing_id: int
    requirement_key: str
    resolution_name: str
    resolution_detail: str | None = None
    resolution_url: str | None = None
    distance_meters: float | None = None
    satisfies: bool = True


@dataclass
class LLMCall:
    id: int
    project_id: str
    phase: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: int | None = None
    request_summary: str | None = None
    created_at: str = ""


@dataclass
class ProjectStats:
    total_listings: int = 0
    completed_listings: int = 0
    avg_completeness: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_searches: int = 0
    requirements: list[dict[str, object]] = field(default_factory=list)
