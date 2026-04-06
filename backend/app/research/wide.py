import json
import time
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings
from app.research.prompts import WIDE_SYSTEM


@dataclass
class WideResult:
    options: list[dict[str, str | None]]
    input_tokens: int
    output_tokens: int
    duration_ms: int


def _extract_text(response) -> str:
    """Extract text content from a response, handling tool_use agentic loops."""
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text
    return text


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

    total_input = 0
    total_output = 0
    messages: list[dict[str, object]] = [{"role": "user", "content": f"Search for: {query}"}]

    # Agentic loop: keep calling until we get a final text response
    while True:
        response = await client.messages.create(
            model=settings.model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=[{"type": "web_search_20250305"}],
        )
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        if response.stop_reason == "tool_use":
            # Append assistant response and tool results
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Search completed. Please continue.",
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    duration_ms = int((time.monotonic() - start) * 1000)

    text = _extract_text(response)
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        data = json.loads(text.strip())
        options = data.get("options", [])
    except (json.JSONDecodeError, KeyError):
        options = []

    return WideResult(
        options=options,
        input_tokens=total_input,
        output_tokens=total_output,
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
    # Simple ratio: 2 * matching_chars / total_chars (similar to difflib)
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
