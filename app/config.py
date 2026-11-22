import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"

BUY_FEE_RATE = 0.001425
SELL_FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003
MIN_FEE = 20

DEFAULT_STRATEGY = {
    "take_profit_pct": 10,
    "stop_loss_pct": -8,
    "sell_batch_pct": 0.5,
    "buy_more_pct": -3,
    "buy_more_max_pct": -15,
}


class Settings:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.strategy = {**DEFAULT_STRATEGY, **self.config.get("strategy", {})}
        self.push_schedule = self.config.get("telegram", {}).get("push_schedule", ["09:05"])
        holdings_dir = os.getenv(
            "HOLDINGS_DIR", self.config.get("holdings_dir", "data/holdings")
        )
        self.holdings_dir = Path(holdings_dir)
        if not self.holdings_dir.is_absolute():
            self.holdings_dir = BASE_DIR / self.holdings_dir
        legacy = os.getenv("HOLDINGS_FILE", self.config.get("holdings_file", "data/holdings.json"))
        self.legacy_holdings_path = Path(legacy)
        if not self.legacy_holdings_path.is_absolute():
            self.legacy_holdings_path = BASE_DIR / self.legacy_holdings_path
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.cron_secret = os.getenv("CRON_SECRET", "")
        self.dry_run = os.getenv("DRY_RUN", "").strip().lower() in ("1", "true", "yes")

    def holdings_path(self, chat_id):
        safe = "".join(c for c in str(chat_id) if c.isdigit() or c in "-_")
        return self.holdings_dir / f"{safe or 'default'}.json"

    def load_holdings(self, chat_id):
        path = self.holdings_path(chat_id)
        if path.exists():
            return load_holdings_file(path)
        if self.legacy_holdings_path.is_file():
            data = load_holdings_file(self.legacy_holdings_path)
            if data:
                save_holdings_file(path, data)
            return data
        return []

    def save_holdings(self, chat_id, holdings):
        save_holdings_file(self.holdings_path(chat_id), holdings)

    def known_chat_ids(self):
        ids = set(self.allowed_chat_ids())
        if self.holdings_dir.exists():
            for p in self.holdings_dir.glob("*.json"):
                ids.add(p.stem)
        return sorted(ids)

    def allowed_chat_ids(self):
        return [cid.strip() for cid in self.telegram_chat_id.split(",") if cid.strip()]


def load_holdings_file(path: Path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict):
        data = data.get("portfolio", [])
    if not isinstance(data, list):
        return []
    holdings = []
    for item in data:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip()
        if not symbol:
            continue
        holdings.append(
            {
                "symbol": symbol,
                "name": str(item.get("name") or symbol).strip(),
                "shares": int(float(item.get("shares", 0))),
                "avg_cost": float(item.get("avg_cost", 0)),
            }
        )
    return holdings


def save_holdings_file(path: Path, holdings):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"portfolio": holdings}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings