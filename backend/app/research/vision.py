import httpx

from app.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
VISION_MODEL = "moondream/moondream"


async def parse_image(image_url: str, question: str) -> str | None:
    """Ask a vision model about an image via OpenRouter. Returns None if unavailable."""
    if not settings.openrouter_api_key:
        return None

    async with httpx.AsyncClient(timeout=30.0) as http:
        response = await http.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": question},
                        ],
                    }
                ],
                "max_tokens": 512,
            },
        )

        if response.status_code != 200:
            return None

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return None

        return choices[0].get("message", {}).get("content")
