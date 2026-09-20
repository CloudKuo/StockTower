from hashlib import sha256

from fubon_neo.sdk import FubonSDK

PRICE_FIELDS = ("lastPrice", "closePrice", "referencePrice", "previousClose")

MOCK_FACTORS = (0.92, 0.98, 1.05, 1.12, 0.88, 1.18)


class QuoteError(Exception):
    pass


def _as_dict(value):
    return value if isinstance(value, dict) else {}


def _extract_price(result):
    if not isinstance(result, dict):
        result = _as_dict(getattr(result, "data", None))
    candidates = [result]
    for key in ("quote", "data", "intraday"):
        child = result.get(key)
        if isinstance(child, dict):
            candidates.append(child)
    for field in PRICE_FIELDS:
        for candidate in candidates:
            value = candidate.get(field)
            if value is not None:
                try:
                    price = float(value)
                    if price > 0:
                        return price
                except (TypeError, ValueError):
                    continue
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


def get_prices(portfolio, api_key, secret_key, dry_run=False):
    if dry_run:
        return _mock_prices(portfolio)

    if not api_key or not secret_key:
        raise QuoteError("FUBON_API_KEY / FUBON_SECRET_KEY 未設定")

    sdk = FubonSDK()
    accounts = sdk.login(api_key, secret_key)
    if not accounts:
        raise QuoteError("富邦登入失敗，請檢查 API Key")

    sdk.init_realtime()
    stock = sdk.marketdata.rest_client.stock

    symbols = [item["symbol"] for item in portfolio]
    prices = {}
    for symbol in symbols:
        try:
            result = stock.intraday.quote(symbol=symbol)
            prices[symbol] = _extract_price(result)
        except Exception as exc:
            prices[symbol] = None
            print(f"取得 {symbol} 報價失敗: {exc}")
    return prices