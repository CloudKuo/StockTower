from app.quotes import _extract_price


def test_flat_response():
    result = {"symbol": "2330", "lastPrice": 568, "closePrice": 567}
    assert _extract_price(result) == 568.0


def test_nested_quote_response():
    result = {"quote": {"lastPrice": 650.0}}
    assert _extract_price(result) == 650.0


def test_uses_close_price_when_no_last():
    result = {"closePrice": 567, "referencePrice": 566}
    assert _extract_price(result) == 567.0


def test_zero_price_rejected():
    result = {"lastPrice": 0, "closePrice": 567}
    assert _extract_price(result) == 567.0


def test_missing_price_returns_none():
    assert _extract_price({"symbol": "2330"}) is None
    assert _extract_price(None) is None