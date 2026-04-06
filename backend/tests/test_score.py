import json

from app.models import Requirement
from app.research.score import compute_scores


def _req(
    key: str, type_: str = "bool", is_hard: bool = False, weight: float = 1.0, direction: str = "higher_better"
) -> Requirement:
    return Requirement(
        id=0, project_id="test", key=key, label=key, type=type_, is_hard=is_hard, weight=weight, direction=direction
    )


def test_bool_scoring():
    reqs = [_req("has_coffee"), _req("has_wifi")]
    listings = [
        {"id": 1, "attributes": json.dumps({"has_coffee": True, "has_wifi": True})},
        {"id": 2, "attributes": json.dumps({"has_coffee": True, "has_wifi": False})},
        {"id": 3, "attributes": json.dumps({"has_coffee": False, "has_wifi": False})},
    ]
    scores = compute_scores(listings, reqs)
    assert scores[0]["score"] == 100.0
    assert scores[1]["score"] == 50.0
    assert scores[2]["score"] == 0.0


def test_hard_requirement_failure():
    reqs = [_req("has_printer", is_hard=True), _req("has_coffee")]
    listings = [
        {"id": 1, "attributes": json.dumps({"has_printer": True, "has_coffee": True})},
        {"id": 2, "attributes": json.dumps({"has_printer": False, "has_coffee": True})},
    ]
    scores = compute_scores(listings, reqs)
    assert not scores[0]["hard_pass"]
    assert scores[1]["hard_pass"]


def test_numeric_lower_better():
    reqs = [_req("price", type_="float", direction="lower_better")]
    listings = [
        {"id": 1, "attributes": json.dumps({"price": 100})},
        {"id": 2, "attributes": json.dumps({"price": 200})},
        {"id": 3, "attributes": json.dumps({"price": 300})},
    ]
    scores = compute_scores(listings, reqs)
    assert scores[0]["score"] > scores[1]["score"] > scores[2]["score"]


def test_numeric_higher_better():
    reqs = [_req("rating", type_="float", direction="higher_better")]
    listings = [
        {"id": 1, "attributes": json.dumps({"rating": 5.0})},
        {"id": 2, "attributes": json.dumps({"rating": 3.0})},
        {"id": 3, "attributes": json.dumps({"rating": 1.0})},
    ]
    scores = compute_scores(listings, reqs)
    assert scores[0]["score"] > scores[1]["score"] > scores[2]["score"]


def test_data_completeness():
    reqs = [_req("a"), _req("b"), _req("c"), _req("d")]
    listings = [
        {"id": 1, "attributes": json.dumps({"a": True, "b": True, "c": True, "d": True})},
        {"id": 2, "attributes": json.dumps({"a": True, "b": None})},
        {"id": 3, "attributes": json.dumps({})},
    ]
    scores = compute_scores(listings, reqs)
    assert scores[0]["data_completeness"] == 1.0
    assert scores[1]["data_completeness"] == 0.25  # only "a" is non-null
    assert scores[2]["data_completeness"] == 0.0


def test_null_hard_requirement():
    reqs = [_req("required_thing", is_hard=True)]
    listings = [
        {"id": 1, "attributes": json.dumps({"required_thing": None})},
        {"id": 2, "attributes": json.dumps({})},
    ]
    scores = compute_scores(listings, reqs)
    assert scores[0]["hard_pass"]
    assert scores[1]["hard_pass"]


def test_empty_requirements():
    listings = [{"id": 1, "attributes": json.dumps({"foo": "bar"})}]
    scores = compute_scores(listings, [])
    assert scores[0]["score"] == 0.0
    assert scores[0]["data_completeness"] == 0.0


def test_weighted_scoring():
    reqs = [_req("important", weight=3.0), _req("minor", weight=1.0)]
    listings = [
        {"id": 1, "attributes": json.dumps({"important": True, "minor": False})},
        {"id": 2, "attributes": json.dumps({"important": False, "minor": True})},
    ]
    scores = compute_scores(listings, reqs)
    assert scores[0]["score"] == 75.0  # 3/4 * 100
    assert scores[1]["score"] == 25.0  # 1/4 * 100


def test_structured_attributes():
    """Attributes with {"value": ..., "source": "..."} format."""
    reqs = [_req("has_coffee"), _req("price", type_="float", direction="lower_better")]
    listings = [
        {
            "id": 1,
            "attributes": json.dumps(
                {
                    "has_coffee": {"value": True, "source": "https://example.com"},
                    "price": {"value": 3000, "source": "https://example.com/rates"},
                }
            ),
        },
        {
            "id": 2,
            "attributes": json.dumps(
                {
                    "has_coffee": {"value": False, "source": "https://other.com"},
                    "price": {"value": 5000, "source": "https://other.com/rates"},
                }
            ),
        },
    ]
    scores = compute_scores(listings, reqs)
    assert scores[0]["score"] > scores[1]["score"]
    assert scores[0]["data_completeness"] == 1.0


def test_multi_tier_values():
    """Multi-tier numeric values — should use the lowest amount."""
    reqs = [_req("price", type_="float", direction="lower_better")]
    listings = [
        {
            "id": 1,
            "attributes": json.dumps(
                {
                    "price": {
                        "value": [
                            {"tier": "Hot Desk", "amount": 2500},
                            {"tier": "Dedicated", "amount": 4500},
                        ],
                        "source": "https://example.com/rates",
                    },
                }
            ),
        },
        {
            "id": 2,
            "attributes": json.dumps(
                {
                    "price": {"value": 3000, "source": "https://other.com"},
                }
            ),
        },
    ]
    scores = compute_scores(listings, reqs)
    # Listing 1 has lowest tier at 2500, listing 2 at 3000
    # Lower is better, so listing 1 should score higher
    assert scores[0]["score"] > scores[1]["score"]
