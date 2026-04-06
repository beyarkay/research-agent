import contextlib
import json

from fastapi import APIRouter, HTTPException, Request

from app.api.filters import build_listing_query, parse_filters
from app.database import get_db
from app.models import Requirement
from app.research.score import extract_value
from app.schemas import AttributeDistribution, FallbackResponse, ListingResponse, ListingsPage

router = APIRouter()


def _row_to_listing(row) -> ListingResponse:
    attrs = row["attributes"]
    parsed_attrs = json.loads(attrs) if isinstance(attrs, str) else attrs
    return ListingResponse(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        url=row["url"],
        image_url=row["image_url"],
        address=row["address"],
        lat=row["lat"],
        lng=row["lng"],
        summary=row["summary"],
        attributes=parsed_attrs,
        raw_notes=row["raw_notes"],
        score=row["score"],
        hard_pass=bool(row["hard_pass"]),
        hard_failures=json.loads(row["hard_failures"]) if row["hard_failures"] else [],
        data_completeness=row["data_completeness"],
        status=row["status"],
    )


async def _get_requirements(db, project_id: str) -> dict[str, Requirement]:
    cursor = await db.execute("SELECT * FROM project_requirements WHERE project_id = ?", (project_id,))
    rows = await cursor.fetchall()
    return {
        r["key"]: Requirement(
            id=r["id"],
            project_id=r["project_id"],
            key=r["key"],
            label=r["label"],
            type=r["type"],
            enum_options=r["enum_options"],
            unit=r["unit"],
            is_hard=bool(r["is_hard"]),
            weight=r["weight"],
            direction=r["direction"],
            sort_order=r["sort_order"],
        )
        for r in rows
    }


@router.get("/projects/{project_id}/listings", response_model=ListingsPage)
async def list_listings(project_id: str, request: Request) -> ListingsPage:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        requirements = await _get_requirements(db, project_id)
        query_params = dict(request.query_params)
        filters = parse_filters(query_params)
        sort = query_params.get("sort")
        hide_failed = query_params.get("hide_failed", "").lower() in ("true", "1")

        sql, params = build_listing_query(project_id, filters, sort, hide_failed, requirements)

        # Count total
        count_sql = sql.replace("SELECT *", "SELECT COUNT(*) as cnt", 1)
        count_sql = count_sql.split("ORDER BY")[0]
        cursor = await db.execute(count_sql, params)
        count_row = await cursor.fetchone()
        total = count_row["cnt"] if count_row else 0

        # Paginate
        page = int(query_params.get("page", "1"))
        per_page = min(int(query_params.get("per_page", "50")), 200)
        offset = (page - 1) * per_page
        sql += " LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        items = [_row_to_listing(r) for r in rows]

        return ListingsPage(items=items, total=total)
    finally:
        await db.close()


@router.get("/projects/{project_id}/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(project_id: str, listing_id: int) -> ListingResponse:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM listings WHERE id = ? AND project_id = ?",
            (listing_id, project_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Listing not found")
        return _row_to_listing(row)
    finally:
        await db.close()


@router.get(
    "/projects/{project_id}/listings/{listing_id}/fallbacks",
    response_model=list[FallbackResponse],
)
async def list_fallbacks(project_id: str, listing_id: int) -> list[FallbackResponse]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT f.* FROM fallbacks f "
            "JOIN listings l ON f.listing_id = l.id "
            "WHERE f.listing_id = ? AND l.project_id = ?",
            (listing_id, project_id),
        )
        rows = await cursor.fetchall()
        return [
            FallbackResponse(
                id=r["id"],
                listing_id=r["listing_id"],
                requirement_key=r["requirement_key"],
                resolution_name=r["resolution_name"],
                resolution_detail=r["resolution_detail"],
                resolution_url=r["resolution_url"],
                distance_meters=r["distance_meters"],
                satisfies=bool(r["satisfies"]),
            )
            for r in rows
        ]
    finally:
        await db.close()


@router.get(
    "/projects/{project_id}/distributions",
    response_model=list[AttributeDistribution],
)
async def get_distributions(project_id: str) -> list[AttributeDistribution]:
    """Get value distributions for all numeric attributes across all listings."""
    db = await get_db()
    try:
        requirements = await _get_requirements(db, project_id)
        numeric_reqs = {k: r for k, r in requirements.items() if r.type in ("int", "float")}
        if not numeric_reqs:
            return []

        cursor = await db.execute(
            "SELECT attributes FROM listings WHERE project_id = ?",
            (project_id,),
        )
        rows = await cursor.fetchall()

        distributions: list[AttributeDistribution] = []
        for key, req in numeric_reqs.items():
            values: list[float] = []
            for row in rows:
                attrs = json.loads(row["attributes"]) if isinstance(row["attributes"], str) else row["attributes"]
                raw = attrs.get(key)
                val = extract_value(raw)
                if val is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        values.append(float(val))
            if values:
                distributions.append(AttributeDistribution(key=key, values=values, unit=req.unit))

        return distributions
    finally:
        await db.close()


@router.post("/projects/{project_id}/listings/{listing_id}/validate-urls")
async def validate_listing_urls(project_id: str, listing_id: int) -> dict[str, bool]:
    """Validate all URLs associated with a listing (website, source URLs, fallback URLs)."""
    from app.research.validate_urls import validate_urls

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM listings WHERE id = ? AND project_id = ?",
            (listing_id, project_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Listing not found")

        urls_to_check: list[str] = []

        # Main URL
        if row["url"]:
            urls_to_check.append(row["url"])

        # Source URLs from structured attributes
        attrs = json.loads(row["attributes"]) if isinstance(row["attributes"], str) else row["attributes"]
        for attr_val in attrs.values():
            if isinstance(attr_val, dict):
                src = attr_val.get("source")
                if isinstance(src, str) and src.startswith("http"):
                    urls_to_check.append(src)

        # Fallback URLs
        cursor = await db.execute(
            "SELECT resolution_url FROM fallbacks WHERE listing_id = ?",
            (listing_id,),
        )
        for fb_row in await cursor.fetchall():
            if fb_row["resolution_url"]:
                urls_to_check.append(fb_row["resolution_url"])

        # Deduplicate
        urls_to_check = list(dict.fromkeys(urls_to_check))
    finally:
        await db.close()

    if not urls_to_check:
        return {}

    return await validate_urls(urls_to_check)
