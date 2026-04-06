import pytest

from app.research.validate_urls import check_url, validate_urls


@pytest.mark.api_key
@pytest.mark.asyncio
async def test_check_url_valid():
    assert await check_url("https://www.google.com") is True


@pytest.mark.api_key
@pytest.mark.asyncio
async def test_check_url_invalid():
    assert await check_url("https://thisdomaindoesnotexist12345.com") is False


@pytest.mark.api_key
@pytest.mark.asyncio
async def test_validate_urls_batch():
    results = await validate_urls(
        [
            "https://www.google.com",
            "https://thisdomaindoesnotexist12345.com",
        ]
    )
    assert results["https://www.google.com"] is True
    assert results["https://thisdomaindoesnotexist12345.com"] is False
