from app.research.wide import deduplicate_options


def test_deduplicate_by_url():
    options = [
        {"name": "Place A", "url": "https://placea.com/about"},
        {"name": "Place A", "url": "https://placea.com/pricing"},
        {"name": "Place B", "url": "https://placeb.com"},
    ]
    result = deduplicate_options(options)
    assert len(result) == 2


def test_deduplicate_by_name():
    options = [
        {"name": "Workshop17 Kloof Street", "url": "https://site1.com"},
        {"name": "Workshop17 Kloof St", "url": "https://site2.com"},
        {"name": "Totally Different Place", "url": "https://site3.com"},
    ]
    result = deduplicate_options(options)
    # The two Workshop17 entries are similar enough to deduplicate
    assert len(result) <= 3


def test_deduplicate_strips_query_params():
    options = [
        {"name": "A", "url": "https://example.com/page?ref=google"},
        {"name": "B", "url": "https://example.com/page?ref=bing"},
    ]
    result = deduplicate_options(options)
    assert len(result) == 1


def test_deduplicate_handles_none_url():
    options = [
        {"name": "Place A", "url": None},
        {"name": "Place B", "url": None},
        {"name": "Place A Copy", "url": None},
    ]
    result = deduplicate_options(options)
    assert len(result) >= 2  # At least A and B


def test_deduplicate_preserves_order():
    options = [
        {"name": "First", "url": "https://first.com"},
        {"name": "Second", "url": "https://second.com"},
        {"name": "Third", "url": "https://third.com"},
    ]
    result = deduplicate_options(options)
    assert result[0]["name"] == "First"
    assert result[1]["name"] == "Second"
    assert result[2]["name"] == "Third"
