import asyncio
import json
import secrets

import aiosqlite
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.schemas import ProjectCreate, ProjectResponse, ProjectStatsResponse, RefineRequest

router = APIRouter()

# In-memory event queues keyed by project_id
_event_queues: dict[str, list[asyncio.Queue[dict[str, object] | None]]] = {}


def get_event_queues() -> dict[str, list[asyncio.Queue[dict[str, object] | None]]]:
    return _event_queues


async def emit_event(project_id: str, event: str, data: dict[str, object]) -> None:
    for queue in _event_queues.get(project_id, []):
        await queue.put({"event": event, "data": data})


def _row_to_project(row: aiosqlite.Row) -> ProjectResponse:
    return ProjectResponse(
        id=row["id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        prompt=row["prompt"],
        parsed_intent=row["parsed_intent"],
        search_locale=row["search_locale"],
        status=row["status"],
    )


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate) -> ProjectResponse:
    project_id = secrets.token_hex(16)
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO projects (id, prompt) VALUES (?, ?)",
            (project_id, body.prompt),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        assert row is not None
        project = _row_to_project(row)
    finally:
        await db.close()

    # Start research engine in background
    from app.research.engine import run_research

    asyncio.create_task(run_research(project_id))

    return project


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects() -> list[ProjectResponse]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_project(r) for r in rows]
    finally:
        await db.close()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str) -> ProjectResponse:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return _row_to_project(row)
    finally:
        await db.close()


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        await db.commit()
    finally:
        await db.close()


@router.get("/projects/{project_id}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(project_id: str) -> ProjectStatsResponse:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        cursor = await db.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as completed, "
            "AVG(data_completeness) as avg_comp "
            "FROM listings WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
        assert row is not None

        cursor = await db.execute(
            "SELECT COALESCE(SUM(input_tokens), 0) as inp, COALESCE(SUM(output_tokens), 0) as outp "
            "FROM llm_calls WHERE project_id = ?",
            (project_id,),
        )
        tokens = await cursor.fetchone()
        assert tokens is not None

        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM search_queries WHERE project_id = ?",
            (project_id,),
        )
        searches = await cursor.fetchone()
        assert searches is not None

        return ProjectStatsResponse(
            total_listings=row["total"] or 0,
            completed_listings=row["completed"] or 0,
            avg_completeness=row["avg_comp"] or 0.0,
            total_input_tokens=tokens["inp"],
            total_output_tokens=tokens["outp"],
            total_searches=searches["cnt"],
        )
    finally:
        await db.close()


@router.get("/projects/{project_id}/events")
async def project_events(project_id: str) -> EventSourceResponse:
    queue: asyncio.Queue[dict[str, object] | None] = asyncio.Queue()
    if project_id not in _event_queues:
        _event_queues[project_id] = []
    _event_queues[project_id].append(queue)

    async def event_generator():
        try:
            while True:
                msg = await queue.get()
                if msg is None:
                    break
                yield {"event": msg["event"], "data": json.dumps(msg["data"])}
        finally:
            _event_queues[project_id].remove(queue)
            if not _event_queues[project_id]:
                del _event_queues[project_id]

    return EventSourceResponse(event_generator())


@router.post("/projects/{project_id}/refine", response_model=ProjectResponse)
async def refine_project(project_id: str, body: RefineRequest) -> ProjectResponse:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        new_prompt = row["prompt"] + "\n\nAdditional context: " + body.additional_context
        await db.execute(
            "UPDATE projects SET prompt = ?, status = 'pending', "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (new_prompt, project_id),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        updated = await cursor.fetchone()
        assert updated is not None
        project = _row_to_project(updated)
    finally:
        await db.close()

    from app.research.engine import run_research

    asyncio.create_task(run_research(project_id))

    return project


@router.post("/projects/{project_id}/resume", response_model=ProjectResponse)
async def resume_project(project_id: str) -> ProjectResponse:
    """Resume a project's research from where it left off."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        await db.execute(
            "UPDATE projects SET status = 'pending', updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (project_id,),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        updated = await cursor.fetchone()
        assert updated is not None
        project = _row_to_project(updated)
    finally:
        await db.close()

    from app.research.engine import run_research

    asyncio.create_task(run_research(project_id))

    return project
