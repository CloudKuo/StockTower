from hashlib import sha256

import requests

PRICE_FIELDS = ("z", "y", "o", "h", "l")
MOCK_FACTORS = (0.92, 0.98, 1.05, 1.12, 0.88, 1.18)
TWSE_MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


class QuoteError(Exception):
    pass


def _to_float(value):
    try:
        if value in (None, "", "-", "--", "---"):
            return None
        price = float(str(value).replace(",", ""))
        return price if price > 0 else None
    except (TypeError, ValueError):
        return None


def _extract_price(msg):
    if not isinstance(msg, dict):
        return None
    for field in ("z", "pz", "b", "a", "y"):
        raw = msg.get(field)
        if field in ("b", "a") and isinstance(raw, str):
            raw = raw.split("_")[0]
        price = _to_float(raw)
        if price is not None:
            return price
    return None


def _mock_prices(portfolio):
    prices = {}
    for idx, item in enumerate(portfolio):
        symbol = item["symbol"]
        avg_cost = float(item["avg_cost"])
        digest = sha256(symbol.encode()).hexdigest()
        jitter = (int(digest[:8], 16) % 100) / 1000 - 0.05
        factor = MOCK_FACTORS[idx % len(MOCK_FACTORS)] + jitter
        prices[symbol] = round(avg_cost * factor, 2)
    return prices


def _query_twse(symbols):
    ex_ch = "|".join(f"tse_{s}.tw|otc_{s}.tw" for s in symbols)
    resp = requests.get(
        TWSE_MIS_URL,
        params={"ex_ch": ex_ch, "json": "1", "delay": "0"},
        timeout=10,
        headers={"User-Agent": "StockTower/1.0"},
    )
    resp.raise_for_status()
    data = resp.json()
    msgs = data.get("msgArray") or []
    by_symbol = {}
    for msg in msgs:
        code = str(msg.get("c") or msg.get("ch", "").split(".")[0]).strip()
        price = _extract_price(msg)
        if code and price is not None:
            by_symbol[code] = price
    return by_symbol


def get_prices(portfolio, dry_run=False):
    if dry_run:
        return _mock_prices(portfolio)

    symbols = [str(item["symbol"]).strip() for item in portfolio if item.get("symbol")]
    if not symbols:
        return {}

    try:
        by_symbol = _query_twse(symbols)
    except Exception as exc:
        raise QuoteError(f"公開報價查詢失敗：{exc}") from exc

    prices = {}
    for symbol in symbols:
        price = by_symbol.get(symbol)
        if price is None:
            print(f"取得 {symbol} 報價失敗: 無有效價格")
        prices[symbol] = price
    return prices