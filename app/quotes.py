import base64
from hashlib import sha256
from pathlib import Path

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


def _ensure_cert(cert_b64, cert_path):
    path = Path(cert_path)
    if path.exists() and path.stat().st_size > 0:
        return
    if not cert_b64:
        raise QuoteError("FUBON_CERT_B64 未設定（憑證需以 base64 存放在環境變數）")
    path.write_bytes(base64.b64decode(cert_b64))


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


def get_prices(portfolio, credentials, dry_run=False):
    if dry_run:
        return _mock_prices(portfolio)

    required = {
        "FUBON_ID": credentials["FUBON_ID"],
        "FUBON_API_KEY": credentials["FUBON_API_KEY"],
        "FUBON_CERT_PASS": credentials["FUBON_CERT_PASS"],
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise QuoteError(f"{', '.join(missing)} 未設定")

    cert_path = credentials["FUBON_CERT_PATH"] or "/tmp/fubon_cert.pfx"
    _ensure_cert(credentials["FUBON_CERT_B64"], cert_path)

    sdk = FubonSDK()
    result = sdk.apikey_login(
        credentials["FUBON_ID"],
        credentials["FUBON_API_KEY"],
        cert_path,
        credentials["FUBON_CERT_PASS"],
    )
    if not result or not getattr(result, "is_success", False):
        message = getattr(result, "message", None) or "無回傳帳戶"
        raise QuoteError(f"富邦登入失敗：{message}")

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