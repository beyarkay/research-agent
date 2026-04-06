"""LLM-powered deduplication of discovered listings before deep research."""

import json
import logging
import time

from anthropic import AsyncAnthropic

from app.config import settings

logger = logging.getLogger(__name__)

DEDUP_SYSTEM = """\
You are a deduplication assistant. Given a list of venues/options with their names, \
URLs, and addresses, identify which entries refer to the SAME physical location.

Group duplicates together. For each group, pick the BEST entry (most specific name, \
most official URL, most complete address) as the canonical one.

Return JSON:
{
  "groups": [
    {
      "keep_id": 5,
      "duplicate_ids": [12, 23],
      "reason": "Same venue: AfricaWorks at 7 Bree Street, different URLs"
    }
  ]
}

Only include groups where duplicates were found. Entries that are unique should NOT \
appear in the output. Be conservative — only merge entries you're confident are the \
same physical venue. Different branches/locations of the same chain are NOT duplicates."""


async def deduplicate_listings(
    client: AsyncAnthropic,
    listings: list[dict[str, object]],
) -> dict[str, object]:
    """Identify duplicate listings using Claude.

    Args:
        listings: list of {id, name, url, address}

    Returns:
        {
            "keep_ids": set of IDs to keep,
            "remove_ids": set of IDs to remove,
            "groups": list of {keep_id, duplicate_ids, reason},
            "input_tokens": int,
            "output_tokens": int,
            "duration_ms": int,
        }
    """
    if len(listings) < 2:
        return {
            "keep_ids": {item["id"] for item in listings},
            "remove_ids": set(),
            "groups": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "duration_ms": 0,
        }

    # Build the listing text for Claude
    lines = []
    for item in listings:
        lines.append(
            f"ID={item['id']}: {item['name']}"
            + (f" | URL: {item['url']}" if item.get("url") else "")
            + (f" | Address: {item['address']}" if item.get("address") else "")
        )
    listing_text = "\n".join(lines)

    start = time.monotonic()
    response = await client.messages.create(
        model=settings.model,
        max_tokens=4096,
        system=DEDUP_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Deduplicate these {len(listings)} listings:\n\n{listing_text}",
            }
        ],
    )
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
    except (json.JSONDecodeError, ValueError):
        data = {"groups": []}

    groups = data.get("groups", [])
    all_ids = {item["id"] for item in listings}
    remove_ids: set[int] = set()
    for group in groups:
        for dup_id in group.get("duplicate_ids", []):
            remove_ids.add(dup_id)

    keep_ids = all_ids - remove_ids

    logger.info(
        "Dedup: %d listings -> %d unique (%d duplicates in %d groups)",
        len(listings),
        len(keep_ids),
        len(remove_ids),
        len(groups),
    )

    return {
        "keep_ids": keep_ids,
        "remove_ids": remove_ids,
        "groups": groups,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "duration_ms": duration_ms,
    }
