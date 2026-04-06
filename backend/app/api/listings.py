import contextlib
import json

from fastapi import APIRouter, HTTPException, Request

from app.api.filters import build_listing_query, parse_filters
from app.database import get_db
from app.models import Requirement
from app.research.score import extract_value
from app.schemas import (
    AddListingRequest,
    AttributeDistribution,
    FallbackResponse,
    ListingResponse,
    ListingsPage,
    ListingUserUpdate,
    RetryListingRequest,
)

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
        user_status=row["user_status"],
        user_notes=row["user_notes"],
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


@router.patch("/projects/{project_id}/listings/{listing_id}", response_model=ListingResponse)
async def update_listing_user_data(project_id: str, listing_id: int, body: ListingUserUpdate) -> ListingResponse:
    """Update user-set fields on a listing (favourite/minimize, notes)."""
    db = await get_db()
    try:
        updates = []
        params: list[object] = []
        if body.user_status is not None:
            if body.user_status not in ("normal", "favourite", "minimized"):
                raise HTTPException(status_code=400, detail="Invalid user_status")
            updates.append("user_status = ?")
            params.append(body.user_status)
        if body.user_notes is not None:
            updates.append("user_notes = ?")
            params.append(body.user_notes)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.extend([listing_id, project_id])
        await db.execute(
            f"UPDATE listings SET {', '.join(updates)} WHERE id = ? AND project_id = ?",
            params,
        )
        await db.commit()

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


@router.post("/projects/{project_id}/listings/{listing_id}/retry", response_model=ListingResponse)
async def retry_listing(project_id: str, listing_id: int, body: RetryListingRequest) -> ListingResponse:
    """Re-run deep research on a listing, with an optional hint."""
    import asyncio

    from anthropic import AsyncAnthropic

    from app.config import settings
    from app.research.score import compute_scores

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM listings WHERE id = ? AND project_id = ?",
            (listing_id, project_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Listing not found")

        # Reset status
        await db.execute(
            "UPDATE listings SET status = 'discovered', attributes = '{}', raw_notes = NULL WHERE id = ?",
            (listing_id,),
        )
        await db.commit()
        listing_name = row["name"]
        listing_url = row["url"]
        listing_address = row["address"]
    finally:
        await db.close()

    async def _research():
        reqs = await _get_requirements(await get_db(), project_id)
        req_list = list(reqs.values())
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        # Append hint to user content if provided
        extra = f"\n\nAdditional guidance: {body.hint}" if body.hint else ""
        import time

        from app.research.deep import _build_attributes_prompt, _extract_json, _extract_text
        from app.research.prompts import DEEP_SYSTEM
        from app.research.wide import WEB_SEARCH_TOOL

        attrs_prompt = _build_attributes_prompt(req_list)
        user_content = (
            f"Research '{listing_name}'"
            + (f" — official website: {listing_url}" if listing_url else "")
            + (f" at {listing_address}" if listing_address else "")
            + f"\n\nFill in these attributes:\n{attrs_prompt}"
            + "\n\nIMPORTANT: Visit the official website first."
            + "\n\nNOTE: Drive/commute times will be calculated automatically — set to null."
            + "\n\nIf the venue is permanently closed, set currently_open to false."
            + extra
        )

        start = time.monotonic()
        response = await client.messages.create(
            model=settings.model,
            max_tokens=8192,
            system=DEEP_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
            tools=[WEB_SEARCH_TOOL],
        )
        _ = int((time.monotonic() - start) * 1000)  # duration_ms, unused for now
        text = _extract_text(response)
        try:
            data = _extract_json(text)
        except (json.JSONDecodeError, ValueError):
            data = {}

        db2 = await get_db()
        try:
            await db2.execute(
                "UPDATE listings SET attributes = ?, summary = ?, "
                "address = COALESCE(?, address), "
                "image_url = COALESCE(?, image_url), raw_notes = ?, "
                "status = 'complete' WHERE id = ?",
                (
                    json.dumps(data.get("attributes", {})),
                    data.get("summary"),
                    data.get("full_address"),
                    data.get("image_url"),
                    data.get("raw_notes"),
                    listing_id,
                ),
            )
            await db2.commit()
        finally:
            await db2.close()

        # Rescore
        db3 = await get_db()
        try:
            cursor = await db3.execute(
                "SELECT id, attributes FROM listings WHERE project_id = ?",
                (project_id,),
            )
            all_listings = [{"id": r["id"], "attributes": r["attributes"]} for r in await cursor.fetchall()]
        finally:
            await db3.close()

        scored = compute_scores(all_listings, req_list)
        db4 = await get_db()
        try:
            for s in scored:
                await db4.execute(
                    "UPDATE listings SET score = ?, hard_pass = ?, "
                    "hard_failures = ?, data_completeness = ? WHERE id = ?",
                    (s["score"], int(s["hard_pass"]), json.dumps(s["hard_failures"]), s["data_completeness"], s["id"]),
                )
            await db4.commit()
        finally:
            await db4.close()

    asyncio.create_task(_research())

    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
        row = await cursor.fetchone()
        assert row is not None
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


@router.post(
    "/projects/{project_id}/listings/add",
    response_model=ListingResponse,
    status_code=201,
)
async def add_listing(project_id: str, body: AddListingRequest) -> ListingResponse:
    """Manually add a listing and kick off deep research on it."""
    import asyncio

    from anthropic import AsyncAnthropic

    from app.config import settings
    from app.research.deep import deep_research
    from app.research.score import compute_scores

    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Project not found")

        name = body.name or body.url.split("//")[-1].split("/")[0]
        cursor = await db.execute(
            "INSERT INTO listings (project_id, name, url, address, summary, status) "
            "VALUES (?, ?, ?, ?, ?, 'discovered')",
            (project_id, name, body.url, body.address, body.notes),
        )
        listing_id = cursor.lastrowid
        await db.commit()
    finally:
        await db.close()

    # Run deep research in background
    async def _research():
        reqs = await _get_requirements(await get_db(), project_id)
        req_list = list(reqs.values())
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        dr = await deep_research(client, name, body.url, body.address, req_list)

        db2 = await get_db()
        try:
            await db2.execute(
                "UPDATE listings SET attributes = ?, summary = ?, "
                "address = COALESCE(?, address), "
                "image_url = COALESCE(?, image_url), raw_notes = ?, "
                "status = 'complete' WHERE id = ?",
                (json.dumps(dr.attributes), dr.summary, dr.full_address, dr.image_url, dr.raw_notes, listing_id),
            )
            await db2.commit()
        finally:
            await db2.close()

        # Rescore all listings
        db3 = await get_db()
        try:
            cursor = await db3.execute(
                "SELECT id, attributes FROM listings WHERE project_id = ?",
                (project_id,),
            )
            all_listings = [{"id": r["id"], "attributes": r["attributes"]} for r in await cursor.fetchall()]
        finally:
            await db3.close()

        scored = compute_scores(all_listings, req_list)
        db4 = await get_db()
        try:
            for s in scored:
                await db4.execute(
                    "UPDATE listings SET score = ?, hard_pass = ?, "
                    "hard_failures = ?, data_completeness = ? WHERE id = ?",
                    (
                        s["score"],
                        int(s["hard_pass"]),
                        json.dumps(s["hard_failures"]),
                        s["data_completeness"],
                        s["id"],
                    ),
                )
            await db4.commit()
        finally:
            await db4.close()

    asyncio.create_task(_research())

    # Return the listing immediately (research happens in background)
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
        row = await cursor.fetchone()
        assert row is not None
        return _row_to_listing(row)
    finally:
        await db.close()
