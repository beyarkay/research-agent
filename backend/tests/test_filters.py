from app.api.filters import build_listing_query, cast_value, parse_filters
from app.models import Requirement


def _req(key: str, type_: str = "bool") -> Requirement:
    return Requirement(id=0, project_id="test", key=key, label=key, type=type_)


def test_parse_filters_basic():
    params = {"filter[has_coffee]": "true", "filter[price__lt]": "5000"}
    result = parse_filters(params)
    assert len(result) == 2
    assert ("has_coffee", "", "true") in result
    assert ("price", "lt", "5000") in result


def test_parse_filters_ignores_non_filters():
    params = {"sort": "-score", "page": "1", "filter[active]": "true"}
    result = parse_filters(params)
    assert len(result) == 1
    assert result[0] == ("active", "", "true")


def test_cast_value_types():
    assert cast_value("true", "bool") == 1
    assert cast_value("false", "bool") == 0
    assert cast_value("42", "int") == 42
    assert cast_value("3.14", "float") == 3.14
    assert cast_value("hello", "text") == "hello"


def test_build_query_basic():
    reqs = {"has_coffee": _req("has_coffee"), "price": _req("price", "float")}
    filters = [("has_coffee", "", "true"), ("price", "lt", "5000")]
    sql, params = build_listing_query("proj1", filters, None, False, reqs)

    assert "project_id = ?" in sql
    # Bool "true" now means "Yes + Unknown" — excludes only explicit false
    assert "json_extract(attributes, '$.has_coffee') IS NULL" in sql
    assert "!= 0" in sql
    assert "json_extract(attributes, '$.price') < ?" in sql
    assert params[0] == "proj1"
    assert 5000.0 in params


def test_build_query_bool_strict():
    reqs = {"has_coffee": _req("has_coffee")}
    filters = [("has_coffee", "", "strict_true")]
    sql, params = build_listing_query("proj1", filters, None, False, reqs)
    assert "json_extract(attributes, '$.has_coffee') = 1" in sql


def test_build_query_name_search():
    filters = [("_name", "", "workshop")]
    sql, params = build_listing_query("proj1", filters, None, False, {})
    assert "name LIKE ?" in sql
    assert "%workshop%" in params


def test_build_query_hide_failed():
    sql, params = build_listing_query("proj1", [], None, True, {})
    assert "hard_pass = 0" in sql


def test_build_query_sort_by_requirement():
    reqs = {"price": _req("price", "float")}
    sql, _ = build_listing_query("proj1", [], "-price", False, reqs)
    assert "json_extract(attributes, '$.price') DESC" in sql


def test_build_query_sort_by_score():
    sql, _ = build_listing_query("proj1", [], "-score", False, {})
    assert "score DESC" in sql


def test_build_query_ignores_unknown_filter():
    reqs = {"known": _req("known")}
    filters = [("unknown_key", "", "value")]
    sql, params = build_listing_query("proj1", filters, None, False, reqs)
    assert "unknown_key" not in sql
    assert len(params) == 1  # only project_id


def test_build_query_ignores_unknown_operator():
    reqs = {"price": _req("price", "float")}
    filters = [("price", "invalid_op", "100")]
    sql, params = build_listing_query("proj1", filters, None, False, reqs)
    assert "price" not in sql or "invalid_op" not in sql
    assert len(params) == 1
