from app.quotes import _extract_price, get_prices

PORTFOLIO = [
    {"symbol": "2330", "name": "台積電", "shares": 1000, "avg_cost": 580.0},
    {"symbol": "2409", "name": "友達", "shares": 2000, "avg_cost": 18.5},
]


def test_extract_from_z():
    assert _extract_price({"c": "2330", "z": "650.0"}) == 650.0


def test_extract_from_prev_close_when_no_trade():
    assert _extract_price({"c": "2330", "z": "-", "y": "567"}) == 567.0


def test_extract_from_bid():
    assert _extract_price({"c": "2330", "z": "-", "y": "-", "b": "100.5_101.0_"}) == 100.5


def test_missing_price_returns_none():
    assert _extract_price({"c": "2330", "z": "-", "y": "-"}) is None
    assert _extract_price(None) is None


def test_dry_run_prices():
    prices = get_prices(PORTFOLIO, dry_run=True)
    assert set(prices) == {"2330", "2409"}
    assert all(prices[s] and prices[s] > 0 for s in prices)
    assert 0.7 < prices["2330"] / 580.0 < 1.3


def test_public_fetch_parses_msg_array(monkeypatch):
    import app.quotes as quotes

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "msgArray": [
                    {"c": "2330", "z": "600"},
                    {"c": "2409", "z": "-", "y": "20.1"},
                ]
            }

    monkeypatch.setattr(quotes.requests, "get", lambda *a, **k: FakeResp())
    prices = get_prices(PORTFOLIO)
    assert prices == {"2330": 600.0, "2409": 20.1}


def test_public_fetch_failure_raises(monkeypatch):
    import app.quotes as quotes

    def boom(*a, **k):
        raise RuntimeError("network")

    monkeypatch.setattr(quotes.requests, "get", boom)
    try:
        get_prices(PORTFOLIO)
    except Exception as exc:
        assert "公開報價查詢失敗" in str(exc)
    else:
        raise AssertionError("expected QuoteError")