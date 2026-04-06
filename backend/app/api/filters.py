import re

from app.models import Requirement

OPERATORS = {
    "": "=",
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "ne": "!=",
}

_FILTER_RE = re.compile(r"^filter\[(\w+?)(?:__(\w+))?\]$")


def parse_filters(query_params: dict[str, str]) -> list[tuple[str, str, str]]:
    """Parse query params like filter[key__op]=value into (key, op, value) tuples."""
    result = []
    for param, value in query_params.items():
        m = _FILTER_RE.match(param)
        if m:
            key = m.group(1)
            op = m.group(2) or ""
            result.append((key, op, value))
    return result


def cast_value(value: str, req_type: str) -> object:
    if req_type == "bool":
        return 1 if value.lower() in ("true", "1", "yes", "strict_true") else 0
    if req_type == "int":
        return int(value)
    if req_type == "float":
        return float(value)
    return value


def build_listing_query(
    project_id: str,
    filters: list[tuple[str, str, str]],
    sort: str | None,
    hide_failed: bool,
    requirements: dict[str, Requirement],
) -> tuple[str, list[object]]:
    """Build parameterized SQL for listing queries with dynamic JSON filters."""
    conditions = ["project_id = ?"]
    params: list[object] = [project_id]

    for key, op, value in filters:
        # Special: name search (not a JSON attribute)
        if key == "_name":
            conditions.append("name LIKE ?")
            params.append(f"%{value}%")
            continue

        req = requirements.get(key)
        if req is None:
            continue

        # Special: bool "true" means "Yes OR Unknown" (don't exclude unknowns)
        if req.type == "bool" and value.lower() == "true":
            # Exclude only explicit false
            conditions.append(
                f"(json_extract(attributes, '$.{key}') IS NULL OR json_extract(attributes, '$.{key}') != 0)"
            )
            continue

        # Special: bool "strict_true" means only verified true
        if req.type == "bool" and value.lower() == "strict_true":
            conditions.append(f"json_extract(attributes, '$.{key}') = 1")
            continue

        sql_op = OPERATORS.get(op)
        if sql_op is None:
            continue
        casted = cast_value(value, req.type)
        conditions.append(f"json_extract(attributes, '$.{key}') {sql_op} ?")
        params.append(casted)

    if hide_failed:
        conditions.append("hard_pass = 0")

    where = " AND ".join(conditions)

    # Sort
    order = "score DESC NULLS LAST"
    if sort:
        desc = sort.startswith("-")
        sort_key = sort.lstrip("-")
        direction = "DESC" if desc else "ASC"
        if sort_key == "score":
            order = f"score {direction} NULLS LAST"
        elif sort_key == "name":
            order = f"name {direction}"
        elif sort_key == "data_completeness":
            order = f"data_completeness {direction}"
        elif sort_key in requirements:
            order = f"json_extract(attributes, '$.{sort_key}') {direction} NULLS LAST"

    return f"SELECT * FROM listings WHERE {where} ORDER BY {order}", params
