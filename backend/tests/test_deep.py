import json

import pytest

from app.models import Requirement
from app.research.deep import deep_research
from tests.conftest import make_mock_response


def _req(key: str, type_: str = "bool", label: str | None = None) -> Requirement:
    return Requirement(id=0, project_id="test", key=key, label=label or key, type=type_)


@pytest.mark.asyncio
async def test_deep_research_fills_attributes(mock_anthropic_client):
    response_data = {
        "attributes": {"has_coffee": True, "monthly_price": 3500},
        "attribute_confidence": {"has_coffee": "verified", "monthly_price": "inferred"},
        "summary": "Great coworking space with good amenities",
        "image_url": "https://example.com/photo.jpg",
        "raw_notes": "Checked website and Google Maps",
    }
    mock_anthropic_client.messages.create.return_value = make_mock_response(json.dumps(response_data))

    reqs = [_req("has_coffee", "bool", "Has Coffee"), _req("monthly_price", "float", "Monthly Price")]
    result = await deep_research(mock_anthropic_client, "Test Place", "https://test.com", "123 Street", reqs)

    assert result.attributes["has_coffee"] is True
    assert result.attributes["monthly_price"] == 3500
    assert result.attribute_confidence["has_coffee"] == "verified"
    assert result.summary == "Great coworking space with good amenities"


@pytest.mark.asyncio
async def test_deep_research_handles_bad_json(mock_anthropic_client):
    mock_anthropic_client.messages.create.return_value = make_mock_response("This is not JSON at all")

    result = await deep_research(mock_anthropic_client, "Test", None, None, [])
    assert result.attributes == {}
    assert result.summary is None
