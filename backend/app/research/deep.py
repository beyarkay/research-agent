import json
import time
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings
from app.models import Requirement
from app.research.prompts import DEEP_SYSTEM


@dataclass
class DeepResult:
    attributes: dict[str, object]
    attribute_confidence: dict[str, str]
    summary: str | None
    image_url: str | None
    raw_notes: str | None
    input_tokens: int
    output_tokens: int
    duration_ms: int


def _build_attributes_prompt(requirements: list[Requirement]) -> str:
    lines = []
    for req in requirements:
        type_hint = req.type
        if req.enum_options:
            type_hint = f"enum ({req.enum_options})"
        unit = f" ({req.unit})" if req.unit else ""
        hard = " [REQUIRED]" if req.is_hard else ""
        lines.append(f"- {req.key}: {req.label} — type: {type_hint}{unit}{hard}")
    return "\n".join(lines)


async def deep_research(
    client: AsyncAnthropic,
    name: str,
    url: str | None,
    address: str | None,
    requirements: list[Requirement],
) -> DeepResult:
    attrs_prompt = _build_attributes_prompt(requirements)
    start = time.monotonic()

    user_content = (
        f"Research '{name}'"
        + (f" ({url})" if url else "")
        + (f" at {address}" if address else "")
        + f"\n\nFill in these attributes:\n{attrs_prompt}"
    )

    total_input = 0
    total_output = 0
    messages: list[dict[str, object]] = [{"role": "user", "content": user_content}]

    while True:
        response = await client.messages.create(
            model=settings.model,
            max_tokens=4096,
            system=DEEP_SYSTEM,
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
    except json.JSONDecodeError:
        data = {}

    return DeepResult(
        attributes=data.get("attributes", {}),
        attribute_confidence=data.get("attribute_confidence", {}),
        summary=data.get("summary"),
        image_url=data.get("image_url"),
        raw_notes=data.get("raw_notes"),
        input_tokens=total_input,
        output_tokens=total_output,
        duration_ms=duration_ms,
    )
