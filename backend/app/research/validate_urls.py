"""Validate URLs by checking they actually exist (HEAD request)."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

SEMAPHORE = asyncio.Semaphore(10)
TIMEOUT = 8.0


async def check_url(url: str) -> bool:
    """Check if a URL returns a non-error status. Returns True if reachable."""
    async with SEMAPHORE:
        try:
            async with httpx.AsyncClient(
                timeout=TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"},
            ) as client:
                resp = await client.head(url)
                if resp.status_code < 400:
                    return True
                # Some servers reject HEAD, try GET
                resp = await client.get(url)
                return resp.status_code < 400
        except (httpx.HTTPError, httpx.InvalidURL):
            return False


async def validate_urls(urls: list[str]) -> dict[str, bool]:
    """Check multiple URLs in parallel. Returns {url: is_valid}."""
    tasks = [check_url(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return dict(zip(urls, results, strict=True))
