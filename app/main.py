import requests
from fastapi import FastAPI, Header, HTTPException, Request
from app.config import get_settings
from app.market import is_trading_day
from app.pnl import analyze_portfolio
from app.quotes import QuoteError, get_prices
from app.render import render_report
from app.telegram import TelegramClient

app = FastAPI(title="StockTower")
settings = get_settings()


def build_report():
    credentials = {
        "FUBON_ID": settings.fubon_id,
        "FUBON_API_KEY": settings.fubon_api_key,
        "FUBON_CERT_PATH": settings.fubon_cert_path,
        "FUBON_CERT_PASS": settings.fubon_cert_pass,
        "FUBON_CERT_B64": settings.fubon_cert_b64,
    }
    prices = get_prices(settings.portfolio, credentials, dry_run=settings.dry_run)
    report = analyze_portfolio(settings.portfolio, prices, settings.strategy)
    return report, render_report(report)


def run_pipeline():
    report, text = build_report()
    try:
        sent = TelegramClient(
            settings.telegram_token, settings.telegram_chat_id
        ).send(text)
    except ValueError:
        sent = False
    return {"report": report, "message": text, "sent": sent}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "symbols": settings.holding_symbols}


@app.get("/status")
def status():
    return {
        "dry_run": settings.dry_run,
        "fubon_id_set": bool(settings.fubon_id),
        "fubon_api_key_set": bool(settings.fubon_api_key),
        "fubon_cert_pass_set": bool(settings.fubon_cert_pass),
        "fubon_cert_b64_set": bool(settings.fubon_cert_b64),
        "fubon_cert_path": settings.fubon_cert_path,
        "cron_secret_set": bool(settings.cron_secret),
        "telegram_chat_ids": [
            cid.strip() for cid in settings.telegram_chat_id.split(",") if cid.strip()
        ],
        "symbols": settings.holding_symbols,
    }


@app.post("/api/cron")
def cron(x_cron_secret: str = Header(default="")):
    if settings.cron_secret and x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=403, detail="forbidden")
    if not is_trading_day():
        return {"skipped": True, "reason": "非台股交易日，略過推播"}
    result = run_pipeline()
    return {"sent": result["sent"], "summary": result["report"].message}


@app.post("/api/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    allowed_chat_ids = settings.telegram_chat_id.split(",")
    payload = await request.json()
    chat_id = str(payload.get("message", {}).get("chat", {}).get("id", ""))
    if chat_id not in allowed_chat_ids:
        raise HTTPException(status_code=403, detail="forbidden")
    command = payload.get("message", {}).get("text", "").strip().lower()

    if command == "/pnl":
        try:
            report, text = build_report()
            TelegramClient(settings.telegram_token, chat_id).send(text)
        except QuoteError as exc:
            TelegramClient(settings.telegram_token, chat_id).send(f"查詢失敗：{exc}")
    elif command in ("/start", "/help"):
        TelegramClient(
            settings.telegram_token, chat_id
        ).send("可用指令：\n/pnl - 查詢即時庫存損益")
    return {"ok": True}


@app.get("/")
def root():
    return {"service": "StockTower", "usage": "POST /api/cron, POST /api/telegram"}