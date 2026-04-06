import contextlib
import json

from app.models import Requirement


def compute_scores(
    listings_data: list[dict[str, object]],
    requirements: list[Requirement],
) -> list[dict[str, object]]:
    """Compute scores for all listings. Returns list of {id, score, hard_pass, data_completeness}."""
    if not requirements:
        return [{"id": ld["id"], "score": 0.0, "hard_pass": False, "data_completeness": 0.0} for ld in listings_data]

    # Collect all values per key for normalization
    all_values: dict[str, list[float]] = {}
    for ld in listings_data:
        attrs = ld["attributes"]
        if isinstance(attrs, str):
            attrs = json.loads(attrs)
        for req in requirements:
            val = attrs.get(req.key)
            if val is not None and req.type in ("int", "float"):
                with contextlib.suppress(ValueError, TypeError):
                    all_values.setdefault(req.key, []).append(float(val))

    results = []
    for ld in listings_data:
        attrs = ld["attributes"]
        if isinstance(attrs, str):
            attrs = json.loads(attrs)

        total_weight = 0.0
        earned = 0.0
        hard_pass = False
        non_null_count = 0

        for req in requirements:
            val = attrs.get(req.key)
            if val is not None:
                non_null_count += 1

            total_weight += req.weight

            if val is None:
                if req.is_hard:
                    hard_pass = True
                continue

            if req.type == "bool":
                if val is True or val == 1:
                    earned += req.weight
                elif req.is_hard:
                    hard_pass = True

            elif req.type in ("int", "float"):
                try:
                    num_val = float(val)
                except (ValueError, TypeError):
                    continue
                values = all_values.get(req.key, [])
                normalized = _normalize(num_val, values, req.direction)
                earned += req.weight * normalized

            elif req.type == "enum":
                # Enums get full weight if they have a value
                earned += req.weight

            elif req.type == "text" and val:
                earned += req.weight

        score = (earned / total_weight * 100) if total_weight > 0 else 0.0
        completeness = non_null_count / len(requirements) if requirements else 0.0

        results.append(
            {
                "id": ld["id"],
                "score": round(score, 1),
                "hard_pass": hard_pass,
                "data_completeness": round(completeness, 2),
            }
        )

    return results


def _normalize(value: float, all_values: list[float], direction: str) -> float:
    """Normalize a numeric value to 0.0-1.0 range."""
    if not all_values or len(all_values) < 2:
        return 0.5

    min_v = min(all_values)
    max_v = max(all_values)

    if min_v == max_v:
        return 1.0

    if direction == "lower_better":
        return 1.0 - (value - min_v) / (max_v - min_v)
    elif direction == "higher_better":
        return (value - min_v) / (max_v - min_v)
    else:  # exact — not easily normalizable, default to presence
        return 0.5
