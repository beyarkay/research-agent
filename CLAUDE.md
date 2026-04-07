# CLAUDE.md

## What this is

A research agent: FastAPI backend + React frontend + SQLite. User types a natural-language research prompt, Claude does structured web research, results go into a scored/filterable UI.

## Dev commands

```bash
./scripts/dev.sh          # build frontend + start server on :8000
./scripts/check.sh        # parallel: ruff, pytest, tsc, eslint, vitest (must all pass)

# Backend only
cd backend && uv run pytest -x -q
cd backend && uv run ruff check . && uv run ruff format --check .

# Frontend only
cd frontend && npx tsc --noEmit && npx eslint . --max-warnings 0 && npx vitest run

# E2E (needs running server)
cd frontend && npx playwright test --config e2e/playwright.config.ts
```

## Architecture

Single SQLite DB (`backend/research.db`), single shared aiosqlite connection (WAL mode). The research engine runs as a background `asyncio.create_task` and emits SSE events that are both pushed to connected clients and persisted in `activity_log`.

Research pipeline: parse -> wide search (parallel) -> code dedup -> LLM dedup -> deep research (parallel) -> Google Maps distances -> fallback resolution -> deterministic scoring.

All Claude calls use server-side `web_search_20250305` tool. No agentic loop needed -- the server handles search internally in one API call.

## Key files

- `backend/app/research/engine.py` -- main pipeline orchestrator, handles resume logic
- `backend/app/research/prompts.py` -- all system prompts, `with_date()` helper
- `backend/app/api/filters.py` -- dynamic JSON->SQL filter builder with COALESCE for structured attrs
- `backend/app/api/listings.py` -- has retry, add-listing, distributions, URL validation endpoints
- `frontend/src/hooks/useFilters.ts` -- filter/sort/selection state synced to URL params
- `frontend/src/hooks/useProjectEvents.ts` -- loads persisted log, merges with live SSE

## Conventions

- All system prompts include today's date via `with_date()`.
- Attributes can be plain values or `{"value": ..., "source": "url", "note": "..."}`.
- `extract_value()` in `score.py` handles both formats. Filters use `COALESCE(json_extract(..., '$.key.value'), json_extract(..., '$.key'))`.
- Multi-tier numeric values: `{"value": [{"tier": "Hot Desk", "amount": 2500}, ...]}`. Scoring uses the minimum amount.
- Hard requirement failure only on explicit `false`, never on `null`/unknown.
- `user_status` is `normal | favourite | minimized`. `user_notes` is free-form text.
- The `.env` file is in the project root (not backend/). pydantic-settings reads `[".env", "../.env"]`.

## Tests

- Backend: pytest with in-memory SQLite (shared connection, `_NoCloseConnection` wrapper). Mock Anthropic client for unit tests. `@pytest.mark.api_key` for tests that hit real APIs (skipped by default).
- Frontend: vitest with happy-dom. E2E: Playwright against running server.
- `scripts/check.sh` runs everything in parallel, reports as each finishes.
