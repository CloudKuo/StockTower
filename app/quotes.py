from fubon_neo.sdk import FubonSDK

PRICE_FIELDS = ("lastPrice", "closePrice", "referencePrice", "previousClose")


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


def get_prices(symbols, api_key, secret_key):
    if not api_key or not secret_key:
        raise QuoteError("FUBON_API_KEY / FUBON_SECRET_KEY 未設定")

    sdk = FubonSDK()
    accounts = sdk.login(api_key, secret_key)
    if not accounts:
        raise QuoteError("富邦登入失敗，請檢查 API Key")

    sdk.init_realtime()
    stock = sdk.marketdata.rest_client.stock

    prices = {}
    for symbol in symbols:
        try:
            result = stock.intraday.quote(symbol=symbol)
            prices[symbol] = _extract_price(result)
        except Exception as exc:
            prices[symbol] = None
            print(f"取得 {symbol} 報價失敗: {exc}")
    return prices