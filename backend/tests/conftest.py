import os
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Use in-memory DB for tests
os.environ["DATABASE_PATH"] = ":memory:"

from app.config import settings  # noqa: E402

settings.database_path = ":memory:"
settings.anthropic_api_key = "test-key"

import app.database as _db_module  # noqa: E402
from app.database import get_db, init_db  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield
    # Clean up tables between tests to avoid cross-test pollution
    db = await get_db()
    for table in [
        "activity_log",
        "llm_calls",
        "fallbacks",
        "search_results",
        "search_queries",
        "listings",
        "project_requirements",
        "projects",
    ]:
        await db.execute(f"DELETE FROM {table}")  # noqa: S608
    await db.commit()


@pytest.fixture(scope="session", autouse=True)
def close_shared_db():
    """Close the shared in-memory connection after all tests to prevent hang."""
    yield
    if _db_module._shared_conn is not None:
        import asyncio

        asyncio.get_event_loop().run_until_complete(_db_module._shared_conn.close())
        _db_module._shared_conn = None


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client with configurable responses."""
    return AsyncMock()


def make_mock_response(text: str, input_tokens: int = 100, output_tokens: int = 200):
    """Create a mock Claude API response."""
    response = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    response.content = [block]
    response.stop_reason = "end_turn"
    response.usage = MagicMock()
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response
