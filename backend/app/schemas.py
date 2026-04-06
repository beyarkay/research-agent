from pydantic import BaseModel


class ProjectCreate(BaseModel):
    prompt: str


class ProjectResponse(BaseModel):
    id: str
    created_at: str
    updated_at: str
    prompt: str
    parsed_intent: str | None = None
    search_locale: str | None = None
    status: str


class RequirementResponse(BaseModel):
    id: int
    project_id: str
    key: str
    label: str
    type: str
    enum_options: list[str] | None = None
    unit: str | None = None
    is_hard: bool
    weight: float
    direction: str
    sort_order: int


class RequirementUpdate(BaseModel):
    is_hard: bool | None = None
    weight: float | None = None
    direction: str | None = None


class ListingResponse(BaseModel):
    id: int
    project_id: str
    name: str
    url: str | None = None
    image_url: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    summary: str | None = None
    attributes: dict[str, object] = {}
    raw_notes: str | None = None
    score: float | None = None
    hard_pass: bool = False
    hard_failures: list[str] = []
    data_completeness: float = 0.0
    status: str


class FallbackResponse(BaseModel):
    id: int
    listing_id: int
    requirement_key: str
    resolution_name: str
    resolution_detail: str | None = None
    resolution_url: str | None = None
    distance_meters: float | None = None
    satisfies: bool


class ListingsPage(BaseModel):
    items: list[ListingResponse]
    total: int


class ProjectStatsResponse(BaseModel):
    total_listings: int
    completed_listings: int
    avg_completeness: float
    total_input_tokens: int
    total_output_tokens: int
    total_searches: int


class RefineRequest(BaseModel):
    additional_context: str


class SSEEvent(BaseModel):
    event: str
    data: dict[str, object]
