import aiosqlite

from app.config import settings

_TABLES = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    prompt TEXT NOT NULL,
    parsed_intent TEXT,
    search_locale TEXT,
    origin_address TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS project_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    label TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('bool','int','float','text','enum')),
    enum_options TEXT,
    unit TEXT,
    is_hard INTEGER NOT NULL DEFAULT 0,
    weight REAL NOT NULL DEFAULT 1.0,
    direction TEXT NOT NULL DEFAULT 'higher_better'
        CHECK(direction IN ('higher_better','lower_better','exact')),
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE(project_id, key)
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    url TEXT,
    image_url TEXT,
    address TEXT,
    lat REAL,
    lng REAL,
    summary TEXT,
    attributes TEXT NOT NULL DEFAULT '{}',
    raw_notes TEXT,
    score REAL,
    hard_pass INTEGER NOT NULL DEFAULT 0,
    hard_failures TEXT NOT NULL DEFAULT '[]',
    data_completeness REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'discovered',
    user_status TEXT NOT NULL DEFAULT 'normal',
    user_notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS search_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    phase TEXT NOT NULL CHECK(phase IN ('wide','deep','fallback')),
    status TEXT NOT NULL DEFAULT 'pending',
    result_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS search_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_query_id INTEGER NOT NULL REFERENCES search_queries(id) ON DELETE CASCADE,
    listing_id INTEGER REFERENCES listings(id),
    title TEXT,
    url TEXT NOT NULL,
    snippet TEXT,
    rank INTEGER
);

CREATE TABLE IF NOT EXISTS fallbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    requirement_key TEXT NOT NULL,
    resolution_name TEXT NOT NULL,
    resolution_detail TEXT,
    resolution_url TEXT,
    distance_meters REAL,
    satisfies INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    duration_ms INTEGER,
    request_summary TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_listings_project ON listings(project_id);
CREATE INDEX IF NOT EXISTS idx_listings_score ON listings(project_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_requirements_project
    ON project_requirements(project_id);
CREATE INDEX IF NOT EXISTS idx_search_queries_project
    ON search_queries(project_id);
CREATE INDEX IF NOT EXISTS idx_fallbacks_listing ON fallbacks(listing_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_project ON llm_calls(project_id);
"""

# Shared connection for in-memory databases (tests).
# With :memory:, each connect() gets a separate DB, so we share one.
_shared_conn: aiosqlite.Connection | None = None


class _NoCloseConnection:
    """Wraps an aiosqlite connection but makes close() a no-op."""

    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn

    def __getattr__(self, name: str):
        return getattr(self._conn, name)

    async def close(self) -> None:
        pass  # keep the shared connection open


async def get_db() -> aiosqlite.Connection:
    global _shared_conn
    if settings.database_path == ":memory:":
        if _shared_conn is None:
            _shared_conn = await aiosqlite.connect(":memory:")
            _shared_conn.row_factory = aiosqlite.Row
            await _shared_conn.execute("PRAGMA foreign_keys=ON")
        return _NoCloseConnection(_shared_conn)  # type: ignore[return-value]

    db = await aiosqlite.connect(settings.database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    db = await get_db()
    try:
        await db.executescript(_TABLES)
        await db.commit()
    finally:
        await db.close()
