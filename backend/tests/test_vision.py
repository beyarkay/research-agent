import pytest

from app.research.vision import parse_image


@pytest.mark.asyncio
async def test_parse_image_returns_none_without_api_key():
    """Without an OpenRouter API key, parse_image should return None."""
    from app.config import settings

    original = settings.openrouter_api_key
    settings.openrouter_api_key = ""
    try:
        result = await parse_image("https://example.com/image.jpg", "What is in this image?")
        assert result is None
    finally:
        settings.openrouter_api_key = original
