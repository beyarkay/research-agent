"""Test that the actual app serves index.html for SPA client-side routes.

Requires frontend to be built (frontend/dist/ must exist).
Skipped if dist doesn't exist.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

_dist_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
_skip = not _dist_path.is_dir()


@pytest.fixture
def real_app():
    """Import the actual app with frontend_dir pointing to the real dist."""
    from app.config import settings

    old = settings.frontend_dir
    settings.frontend_dir = str(_dist_path)

    # Re-import to pick up the dist dir (main.py checks at import time).
    # Instead, we rebuild the app routes dynamically.
    import importlib

    import app.main

    with patch("app.research.engine.run_research", new_callable=AsyncMock):
        importlib.reload(app.main)
        yield app.main.app

    settings.frontend_dir = old
    importlib.reload(app.main)


@pytest.mark.skipif(_skip, reason="frontend not built (run: cd frontend && npx vite build)")
@pytest.mark.asyncio
async def test_spa_project_route_returns_index_html(real_app):
    """GET /projects/<id> should return index.html (200), not 404."""
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/projects/6bc94e422dfcb69d4586faf3d821900b")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert "<html" in resp.text.lower() or "<!doctype" in resp.text.lower()


@pytest.mark.skipif(_skip, reason="frontend not built")
@pytest.mark.asyncio
async def test_api_routes_still_work(real_app):
    """API routes should not be shadowed by the SPA fallback."""
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/projects")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.skipif(_skip, reason="frontend not built")
@pytest.mark.asyncio
async def test_assets_served_directly(real_app):
    """Static assets in /assets/ should be served directly."""
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Find an actual asset file
        assets_dir = _dist_path / "assets"
        asset_files = list(assets_dir.glob("*.js")) + list(assets_dir.glob("*.css"))
        assert asset_files, "No asset files found in dist/assets/"

        asset_name = asset_files[0].name
        resp = await client.get(f"/assets/{asset_name}")
        assert resp.status_code == 200
