from fastapi import FastAPI, Header, HTTPException, Request

from app.config import get_settings, load_holdings, save_holdings
from app.market import is_trading_day
from app.pnl import analyze_portfolio
from app.quotes import QuoteError, get_prices
from app.render import render_report
from app.telegram import TelegramClient

app = FastAPI(title="StockTower")
settings = get_settings()


def build_report():
    portfolio = settings.portfolio
    if not portfolio:
        return None, "目前尚無庫存。請用 /add 代號 名稱 股數 成本 新增，例如：\n/add 2330 台積電 1000 580"
    prices = get_prices(portfolio, dry_run=settings.dry_run)
    report = analyze_portfolio(portfolio, prices, settings.strategy)
    return report, render_report(report)


def run_pipeline():
    report, text = build_report()
    if report is None:
        return {"report": None, "message": text, "sent": False}
    try:
        sent = TelegramClient(settings.telegram_token, settings.telegram_chat_id).send(text)
    except ValueError:
        sent = False
    return {"report": report, "message": text, "sent": sent}


def _allowed_chat_ids():
    return [cid.strip() for cid in settings.telegram_chat_id.split(",") if cid.strip()]


def _normalize_command(text):
    text = (text or "").strip()
    if not text:
        return "", []
    parts = text.split()
    cmd = parts[0].split("@")[0].lower()
    return cmd, parts[1:]


def _parse_add(args):
    # /add 2330 台積電 1000 580  or /add 2330 1000 580
    if len(args) < 3:
        raise ValueError("格式：/add 代號 名稱 股數 成本 或 /add 代號 股數 成本")
    symbol = args[0].strip()
    if len(args) == 3:
        name = symbol
        shares = int(float(args[1]))
        avg_cost = float(args[2])
    else:
        name = " ".join(args[1:-2]).strip() or symbol
        shares = int(float(args[-2]))
        avg_cost = float(args[-1])
    if shares <= 0 or avg_cost <= 0:
        raise ValueError("股數與成本需大於 0")
    return {"symbol": symbol, "name": name, "shares": shares, "avg_cost": avg_cost}


def _handle_command(command, args, chat_id):
    holdings = load_holdings(settings.holdings_path)

    if command == "/add":
        item = _parse_add(args)
        replaced = False
        for i, h in enumerate(holdings):
            if h["symbol"] == item["symbol"]:
                holdings[i] = item
                replaced = True
                break
        if not replaced:
            holdings.append(item)
        save_holdings(settings.holdings_path, holdings)
        action = "更新" if replaced else "新增"
        return f"已{action} {item['name']}({item['symbol']}) {item['shares']} 股，成本 {item['avg_cost']}"

    if command == "/remove":
        if not args:
            return "格式：/remove 代號"
        symbol = args[0].strip()
        new_holdings = [h for h in holdings if h["symbol"] != symbol]
        if len(new_holdings) == len(holdings):
            return f"找不到 {symbol}"
        save_holdings(settings.holdings_path, new_holdings)
        return f"已移除 {symbol}"

    if command == "/list":
        if not holdings:
            return "目前尚無庫存。請用 /add 新增。"
        lines = ["目前庫存："]
        for h in holdings:
            lines.append(f"- {h['name']}({h['symbol']}) {h['shares']} 股 @ {h['avg_cost']}")
        return "\n".join(lines)

    if command == "/pnl":
        try:
            _, text = build_report()
            return text
        except QuoteError as exc:
            return f"查詢失敗：{exc}"

    if command in ("/start", "/help"):
        return (
            "可用指令：\n"
            "/add 代號 名稱 股數 成本 - 新增/更新庫存\n"
            "/remove 代號 - 移除庫存\n"
            "/list - 查看庫存\n"
            "/pnl - 查詢即時損益與建議"
        )
    return "未知指令，請用 /help 查看可用指令。"


@app.get("/healthz")
def healthz():
    return {"status": "ok", "symbols": settings.holding_symbols}


@app.get("/status")
def status():
    return {
        "dry_run": settings.dry_run,
        "cron_secret_set": bool(settings.cron_secret),
        "telegram_chat_ids": _allowed_chat_ids(),
        "holdings_file": str(settings.holdings_path),
        "symbols": settings.holding_symbols,
    }


@app.post("/api/cron")
def cron(x_cron_secret: str = Header(default="")):
    if settings.cron_secret and x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=403, detail="forbidden")
    if not is_trading_day():
        return {"skipped": True, "reason": "非台股交易日，略過推播"}
    result = run_pipeline()
    summary = result["report"].total_pnl if result["report"] else result["message"]
    return {"sent": result["sent"], "summary": summary}


@app.post("/api/telegram")
async def telegram_webhook(request: Request):
    payload = await request.json()
    message = payload.get("message") or {}
    chat_id = str(message.get("chat", {}).get("id", ""))
    allowed = _allowed_chat_ids()
    if allowed and chat_id not in allowed:
        raise HTTPException(status_code=403, detail="forbidden")
    text = (message.get("text") or "").strip()
    if not text:
        return {"ok": True}
    command, args = _normalize_command(text)
    try:
        reply = _handle_command(command, args, chat_id)
    except Exception as exc:
        reply = f"指令錯誤：{exc}"
    TelegramClient(settings.telegram_token, chat_id).send(reply)
    return {"ok": True}


@app.get("/")
def root():
    return {"service": "StockTower", "usage": "POST /api/cron, POST /api/telegram"}