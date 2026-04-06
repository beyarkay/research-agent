import json
import time
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings
from app.models import Requirement
from app.research.prompts import DEEP_SYSTEM
from app.research.wide import WEB_SEARCH_TOOL


@dataclass
class DeepResult:
    attributes: dict[str, object]
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
        + (f" — official website: {url}" if url else "")
        + (f" at {address}" if address else "")
        + f"\n\nFill in these attributes:\n{attrs_prompt}"
        + "\n\nIMPORTANT: If a URL is provided, search for and visit that "
        "website first. Look for their rates/pricing page, amenities page, "
        "and about page. Then supplement with review sites."
    )

    response = await client.messages.create(
        model=settings.model,
        max_tokens=8192,
        system=DEEP_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
        tools=[WEB_SEARCH_TOOL],
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    text = _extract_text(response)

    try:
        data = _extract_json(text)
    except (json.JSONDecodeError, ValueError):
        data = {}

    return DeepResult(
        attributes=data.get("attributes", {}),
        summary=data.get("summary"),
        image_url=data.get("image_url"),
        raw_notes=data.get("raw_notes"),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        duration_ms=duration_ms,
    )
