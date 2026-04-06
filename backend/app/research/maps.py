"""Google Maps Distance Matrix API integration for actual travel times."""

import httpx

from app.config import settings

DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


async def get_travel_time(
    origin: str,
    destination: str,
    mode: str = "driving",
) -> dict[str, object] | None:
    """Get travel time and distance between two addresses.

    Returns {"duration_minutes": int, "distance_km": float, "duration_text": str}
    or None if unavailable.
    """
    if not settings.google_maps_api_key:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
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
