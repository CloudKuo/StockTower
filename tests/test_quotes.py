from app.quotes import _extract_price, get_prices

PORTFOLIO = [
    {"symbol": "2330", "name": "台積電", "shares": 1000, "avg_cost": 580.0},
    {"symbol": "2409", "name": "友達", "shares": 2000, "avg_cost": 18.5},
]


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


def test_dry_run_no_credentials_needed():
    prices = get_prices(PORTFOLIO, "", "", dry_run=True)
    assert set(prices) == {"2330", "2409"}
    assert all(None is not prices[s] and prices[s] > 0 for s in prices)


def test_dry_run_prices_near_cost():
    prices = get_prices(PORTFOLIO, "", "", dry_run=True)
    assert 0.7 < prices["2330"] / 580.0 < 1.3
    assert 0.7 < prices["2409"] / 18.5 < 1.3


def test_missing_credentials_raise():
    try:
        get_prices(PORTFOLIO, "", "")
    except Exception as exc:
        assert "FUBON" in str(exc)
    else:
        raise AssertionError("expected QuoteError")