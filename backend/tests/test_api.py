import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Patch the research engine before importing the app
with patch("app.research.engine.run_research", new_callable=AsyncMock):
    from app.main import app

from app.database import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_create_project(client):
    with patch("app.api.projects.asyncio.create_task"):
        response = await client.post("/api/projects", json={"prompt": "find coworking spaces"})
    assert response.status_code == 201
    data = response.json()
    assert data["prompt"] == "find coworking spaces"
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client):
    with patch("app.api.projects.asyncio.create_task"):
        await client.post("/api/projects", json={"prompt": "test 1"})
        await client.post("/api/projects", json={"prompt": "test 2"})

    response = await client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    response = await client.get("/api/projects/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_project(client):
    with patch("app.api.projects.asyncio.create_task"):
        create_resp = await client.post("/api/projects", json={"prompt": "to delete"})
    project_id = create_resp.json()["id"]

    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204

    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_listings_empty(client):
    with patch("app.api.projects.asyncio.create_task"):
        create_resp = await client.post("/api/projects", json={"prompt": "test"})
    project_id = create_resp.json()["id"]

    response = await client.get(f"/api/projects/{project_id}/listings")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_listings_with_filters(client):
    from app.database import get_db

    with patch("app.api.projects.asyncio.create_task"):
        create_resp = await client.post("/api/projects", json={"prompt": "test"})
    project_id = create_resp.json()["id"]

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO project_requirements (project_id, key, label, type) VALUES (?, ?, ?, ?)",
            (project_id, "has_coffee", "Has Coffee", "bool"),
        )
        await db.execute(
            "INSERT INTO listings (project_id, name, attributes) VALUES (?, ?, ?)",
            (project_id, "Place A", json.dumps({"has_coffee": True})),
        )
        await db.execute(
            "INSERT INTO listings (project_id, name, attributes) VALUES (?, ?, ?)",
            (project_id, "Place B", json.dumps({"has_coffee": False})),
        )
        await db.commit()
    finally:
        await db.close()

    # Filter for has_coffee=true
    response = await client.get(f"/api/projects/{project_id}/listings?filter[has_coffee]=true")
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Place A"
