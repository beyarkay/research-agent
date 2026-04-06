import json
import time
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings
from app.research.prompts import FALLBACK_SYSTEM, with_date
from app.research.wide import WEB_SEARCH_TOOL


@dataclass
class FallbackResult:
    alternatives: list[dict[str, object]]
    input_tokens: int
    output_tokens: int
    duration_ms: int


def _extract_text(response) -> str:
    parts = []
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts)


def _extract_json(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


async def resolve_fallback(
    client: AsyncAnthropic,
    venue_name: str,
    venue_address: str | None,
    requirement_label: str,
) -> FallbackResult:
    system = FALLBACK_SYSTEM.format(
        venue_name=venue_name,
        venue_address=venue_address or "unknown address",
        requirement_label=requirement_label,
    )
    start = time.monotonic()

    # Server-side web search: one call
    response = await client.messages.create(
        model=settings.model,
        max_tokens=4096,
        system=with_date(system),
        messages=[
            {
                "role": "user",
                "content": f"Find nearby alternatives for: {requirement_label}",
            }
        ],
        tools=[WEB_SEARCH_TOOL],
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    text = _extract_text(response)

    try:
        data = _extract_json(text)
        alternatives = data.get("alternatives", [])
    except (json.JSONDecodeError, KeyError, ValueError):
        alternatives = []

    return FallbackResult(
        alternatives=alternatives,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        duration_ms=duration_ms,
    )
