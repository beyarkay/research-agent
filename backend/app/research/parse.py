import json
import time
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings
from app.research.prompts import PARSE_SYSTEM, PARSE_USER_TEMPLATE, with_date


@dataclass
class ParseResult:
    parsed_intent: str
    search_locale: str | None
    origin_address: str | None
    requirements: list[dict[str, object]]
    search_queries: list[str]
    input_tokens: int
    output_tokens: int
    duration_ms: int


async def parse_prompt(client: AsyncAnthropic, prompt: str) -> ParseResult:
    user_msg = PARSE_USER_TEMPLATE.format(prompt=prompt)
    start = time.monotonic()

    response = await client.messages.create(
        model=settings.model,
        max_tokens=4096,
        system=with_date(PARSE_SYSTEM),
        messages=[{"role": "user", "content": user_msg}],
    )

    duration_ms = int((time.monotonic() - start) * 1000)

    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    # Extract JSON from potential markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    data = json.loads(text.strip())

    return ParseResult(
        parsed_intent=data["parsed_intent"],
        search_locale=data.get("search_locale"),
        origin_address=data.get("origin_address"),
        requirements=data["requirements"],
        search_queries=data["search_queries"],
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        duration_ms=duration_ms,
    )
