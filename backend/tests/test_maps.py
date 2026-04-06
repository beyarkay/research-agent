"""Tests for Google Maps integration. API key test is opt-in."""

import pytest

from app.config import settings
from app.research.maps import get_travel_time


@pytest.mark.asyncio
async def test_get_travel_time_returns_none_without_key():
    original = settings.google_maps_api_key
    settings.google_maps_api_key = ""
    try:
        result = await get_travel_time("A", "B")
        assert result is None
    finally:
        settings.google_maps_api_key = original


@pytest.mark.api_key
@pytest.mark.asyncio
async def test_get_travel_time_with_real_key():
    """Requires GOOGLE_MAPS_API_KEY to be set."""
    from app.config import Settings

    s = Settings()
    if not s.google_maps_api_key:
        pytest.skip("No Google Maps API key")

    original = settings.google_maps_api_key
    settings.google_maps_api_key = s.google_maps_api_key
    try:
        result = await get_travel_time(
            "2 Three Anchor Bay Road, Sea Point, Cape Town",
            "7 Bree Street, Cape Town",
            "driving",
        )
        assert result is not None
        assert result["duration_minutes"] > 0
        assert result["distance_km"] > 0
    finally:
        settings.google_maps_api_key = original
