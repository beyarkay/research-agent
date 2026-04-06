"""Google Maps Distance Matrix API integration for actual travel times."""

import asyncio
import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
SEMAPHORE = asyncio.Semaphore(5)


async def get_travel_time(
    origin: str,
    destination: str,
    mode: str = "driving",
) -> dict[str, object] | None:
    """Get travel time and distance between two addresses.

    Returns {"duration_minutes": int, "distance_km": float,
             "duration_text": str, "distance_text": str}
    or None if unavailable.
    """
    if not settings.google_maps_api_key:
        return None

    async with SEMAPHORE, httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            DISTANCE_MATRIX_URL,
            params={
                "origins": origin,
                "destinations": destination,
                "mode": mode,
                "key": settings.google_maps_api_key,
            },
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("status") != "OK":
            return None

        rows = data.get("rows", [])
        if not rows:
            return None

        elements = rows[0].get("elements", [])
        if not elements or elements[0].get("status") != "OK":
            return None

        element = elements[0]
        duration_secs = element["duration"]["value"]
        distance_m = element["distance"]["value"]

        return {
            "duration_minutes": round(duration_secs / 60),
            "distance_km": round(distance_m / 1000, 1),
            "duration_text": element["duration"]["text"],
            "distance_text": element["distance"]["text"],
        }


async def enrich_listings_with_distances(
    project_id: str,
    origin_address: str,
) -> int:
    """Update distance-related attributes for all listings using Google Maps.

    Looks for requirements with unit containing 'min' and keys containing
    'drive' or 'walk', then queries actual distances.

    Returns number of listings updated.
    """
    if not settings.google_maps_api_key:
        return 0

    from app.database import get_db

    db = await get_db()
    try:
        # Find distance requirements
        cursor = await db.execute(
            "SELECT key, unit FROM project_requirements "
            "WHERE project_id = ? AND type IN ('int', 'float') "
            "AND (key LIKE '%drive%' OR key LIKE '%walk%' OR key LIKE '%distance%' "
            "OR key LIKE '%time%')",
            (project_id,),
        )
        dist_reqs = await cursor.fetchall()
        if not dist_reqs:
            return 0

        # Load listings with addresses
        cursor = await db.execute(
            "SELECT id, name, address, attributes FROM listings "
            "WHERE project_id = ? AND address IS NOT NULL AND status = 'complete'",
            (project_id,),
        )
        listings = await cursor.fetchall()
    finally:
        await db.close()

    updated = 0

    for listing in listings:
        attrs = json.loads(listing["attributes"]) if isinstance(listing["attributes"], str) else listing["attributes"]
        changed = False

        for req in dist_reqs:
            key = req["key"]
            is_walk = "walk" in key.lower()
            is_drive = "drive" in key.lower() or "time" in key.lower()

            if is_drive:
                # Drive time from user's origin to this listing
                result = await get_travel_time(origin_address, listing["address"], "driving")
                if result:
                    attrs[key] = {
                        "value": result["duration_minutes"],
                        "source": "Google Maps Distance Matrix API",
                        "note": (
                            f"{result['duration_text']} ({result['distance_text']}) driving from {origin_address}"
                        ),
                    }
                    changed = True
                    logger.info(
                        "Maps: %s -> %s = %s driving",
                        origin_address,
                        listing["name"],
                        result["duration_text"],
                    )

            elif is_walk:
                # Walk time — this is trickier since we need to know WHAT
                # they're walking to (e.g. gym). We can't resolve that from
                # just the requirement key. Skip if no existing value to
                # use as a reference, or if the value is already structured.
                existing = attrs.get(key)
                if isinstance(existing, dict) and existing.get("source") == "Google Maps Distance Matrix API":
                    continue  # already enriched

        if changed:
            db2 = await get_db()
            try:
                await db2.execute(
                    "UPDATE listings SET attributes = ? WHERE id = ?",
                    (json.dumps(attrs), listing["id"]),
                )
                await db2.commit()
            finally:
                await db2.close()
            updated += 1

    return updated
