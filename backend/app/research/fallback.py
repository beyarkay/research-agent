import json
import time
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings
from app.research.prompts import FALLBACK_SYSTEM


@dataclass
class FallbackResult:
    alternatives: list[dict[str, object]]
    input_tokens: int
    output_tokens: int
    duration_ms: int


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

    total_input = 0
    total_output = 0
    messages: list[dict[str, object]] = [
        {
            "role": "user",
            "content": f"Find nearby alternatives for: {requirement_label}",
        }
    ]

    while True:
        response = await client.messages.create(
            model=settings.model,
            max_tokens=2048,
            system=system,
            messages=messages,
            tools=[{"type": "web_search_20250305"}],
        )
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        if response.stop_reason == "tool_use":
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

    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        data = json.loads(text.strip())
        alternatives = data.get("alternatives", [])
    except (json.JSONDecodeError, KeyError):
        alternatives = []

    return FallbackResult(
        alternatives=alternatives,
        input_tokens=total_input,
        output_tokens=total_output,
        duration_ms=duration_ms,
    )
