import json
import time
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings
from app.research.prompts import WIDE_SYSTEM

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


@dataclass
class WideResult:
    options: list[dict[str, str | None]]
    input_tokens: int
    output_tokens: int
    duration_ms: int


def _extract_text(response) -> str:
    """Extract all text content blocks from a response."""
    parts = []
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts)


def _extract_json(text: str) -> dict:
    """Extract JSON from text, handling markdown code blocks."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


async def wide_search(
    client: AsyncAnthropic,
    query: str,
    category: str,
    locale: str | None,
) -> WideResult:
    system = WIDE_SYSTEM.format(
        category=category,
        locale=locale or "the specified area",
    )
    start = time.monotonic()

    # Server-side web search: Claude handles the search internally in one call.
    # No agentic loop needed.
    response = await client.messages.create(
        model=settings.model,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": f"Search for: {query}"}],
        tools=[WEB_SEARCH_TOOL],
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    text = _extract_text(response)

    try:
        data = _extract_json(text)
        options = data.get("options", [])
    except (json.JSONDecodeError, KeyError, ValueError):
        options = []

    return WideResult(
        options=options,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        duration_ms=duration_ms,
    )


def deduplicate_options(
    all_options: list[dict[str, str | None]],
) -> list[dict[str, str | None]]:
    """Deduplicate options by URL domain and fuzzy name matching."""
    seen_domains: set[str] = set()
    seen_names: set[str] = set()
    unique = []

    for opt in all_options:
        url = (opt.get("url") or "").strip().rstrip("/").lower()
        name = (opt.get("name") or "").strip().lower()

        # Extract domain from URL for dedup
        domain = _extract_domain(url)
        if domain and domain in seen_domains:
            continue

        # Skip if name is very similar to one we've seen (sequence-based)
        if name and any(_name_similarity(name, s) > 0.92 for s in seen_names):
            continue

        if domain:
            seen_domains.add(domain)
        if name:
            seen_names.add(name)
        unique.append(opt)

    return unique


def _extract_domain(url: str) -> str:
    """Extract domain from URL, stripping www prefix."""
    if not url:
        return ""
    # Remove protocol
    url = url.split("://", 1)[-1]
    # Get domain part
    domain = url.split("/", 1)[0].split("?", 1)[0]
    # Strip www
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _name_similarity(a: str, b: str) -> float:
    """Sequence-based similarity using longest common subsequence ratio."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    len_a, len_b = len(a), len(b)
    matches = 0
    b_used = [False] * len_b
    for ch in a:
        for j in range(len_b):
            if not b_used[j] and b[j] == ch:
                matches += 1
                b_used[j] = True
                break
    return 2.0 * matches / (len_a + len_b)
