import os
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Use in-memory DB for tests
os.environ["DATABASE_PATH"] = ":memory:"

from app.config import settings  # noqa: E402

settings.database_path = ":memory:"
settings.anthropic_api_key = "test-key"

from app.database import init_db  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()
    yield


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
