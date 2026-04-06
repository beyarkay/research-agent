import json

import pytest

from app.research.parse import parse_prompt
from tests.conftest import make_mock_response


@pytest.mark.asyncio
async def test_parse_prompt_extracts_requirements(mock_anthropic_client):
    response_data = {
        "parsed_intent": "Find coworking spaces near Sea Point, Cape Town",
        "search_locale": "Cape Town, South Africa",
        "requirements": [
            {
                "key": "has_printer",
                "label": "Printer Access",
                "type": "bool",
                "is_hard": True,
                "weight": 1.0,
                "direction": "higher_better",
            },
            {
                "key": "monthly_price",
                "label": "Monthly Price",
                "type": "float",
                "unit": "ZAR",
                "is_hard": False,
                "weight": 0.6,
                "direction": "lower_better",
            },
        ],
        "search_queries": ["coworking spaces Sea Point Cape Town", "shared office Cape Town"],
    }
    mock_anthropic_client.messages.create.return_value = make_mock_response(json.dumps(response_data))

    result = await parse_prompt(mock_anthropic_client, "find coworking spaces near sea point")

    assert result.parsed_intent == "Find coworking spaces near Sea Point, Cape Town"
    assert result.search_locale == "Cape Town, South Africa"
    assert len(result.requirements) == 2
    assert result.requirements[0]["key"] == "has_printer"
    assert len(result.search_queries) == 2


@pytest.mark.asyncio
async def test_parse_prompt_handles_code_blocks(mock_anthropic_client):
    response_data = {"parsed_intent": "test", "search_locale": None, "requirements": [], "search_queries": ["test"]}
    text = f"Here's the result:\n```json\n{json.dumps(response_data)}\n```"
    mock_anthropic_client.messages.create.return_value = make_mock_response(text)

    result = await parse_prompt(mock_anthropic_client, "test")
    assert result.parsed_intent == "test"


@pytest.mark.asyncio
async def test_parse_prompt_tracks_tokens(mock_anthropic_client):
    response_data = {"parsed_intent": "test", "search_locale": None, "requirements": [], "search_queries": []}
    mock_anthropic_client.messages.create.return_value = make_mock_response(
        json.dumps(response_data), input_tokens=150, output_tokens=300
    )

    result = await parse_prompt(mock_anthropic_client, "test")
    assert result.input_tokens == 150
    assert result.output_tokens == 300
