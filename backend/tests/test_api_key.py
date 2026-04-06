"""Smoke test that verifies the Anthropic API key works. Not run by default.

Run with: uv run pytest tests/test_api_key.py -m api_key
"""

import pytest
from anthropic import AsyncAnthropic

from app.config import Settings


@pytest.mark.api_key
async def test_anthropic_api_key_works():
    settings = Settings()
    assert settings.anthropic_api_key, "ANTHROPIC_API_KEY not set in .env or environment"

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16,
        messages=[{"role": "user", "content": "Say 'ok'"}],
    )
    text = response.content[0].text
    assert len(text) > 0, "Got empty response from API"
