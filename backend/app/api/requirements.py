import json

from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas import RequirementResponse, RequirementUpdate

router = APIRouter()


def _row_to_requirement(row) -> RequirementResponse:
    enum_opts = None
    if row["enum_options"]:
        enum_opts = json.loads(row["enum_options"])
    return RequirementResponse(
        id=row["id"],
        project_id=row["project_id"],
        key=row["key"],
        label=row["label"],
        type=row["type"],
        enum_options=enum_opts,
        unit=row["unit"],
        is_hard=bool(row["is_hard"]),
        weight=row["weight"],
        direction=row["direction"],
        sort_order=row["sort_order"],
    )


@router.get(
    "/projects/{project_id}/requirements",
    response_model=list[RequirementResponse],
)
async def list_requirements(project_id: str) -> list[RequirementResponse]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        cursor = await db.execute(
            "SELECT * FROM project_requirements WHERE project_id = ? ORDER BY sort_order",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_requirement(r) for r in rows]
    finally:
        await db.close()


@router.patch(
    "/projects/{project_id}/requirements/{key}",
    response_model=RequirementResponse,
)
async def update_requirement(project_id: str, key: str, body: RequirementUpdate) -> RequirementResponse:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM project_requirements WHERE project_id = ? AND key = ?",
            (project_id, key),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Requirement not found")

        updates = []
        params: list[object] = []
        if body.is_hard is not None:
            updates.append("is_hard = ?")
            params.append(int(body.is_hard))
        if body.weight is not None:
            updates.append("weight = ?")
            params.append(body.weight)
        if body.direction is not None:
            if body.direction not in ("higher_better", "lower_better", "exact"):
                raise HTTPException(status_code=400, detail="Invalid direction")
            updates.append("direction = ?")
            params.append(body.direction)

        if updates:
            params.extend([project_id, key])
            await db.execute(
                f"UPDATE project_requirements SET {', '.join(updates)} WHERE project_id = ? AND key = ?",
                params,
            )
            await db.commit()

        cursor = await db.execute(
            "SELECT * FROM project_requirements WHERE project_id = ? AND key = ?",
            (project_id, key),
        )
        updated = await cursor.fetchone()
        assert updated is not None
        return _row_to_requirement(updated)
    finally:
        await db.close()
