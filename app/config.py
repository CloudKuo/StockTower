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


class Settings:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.portfolio = self.config["portfolio"]
        self.strategy = self.config["strategy"]
        self.push_schedule = self.config.get("telegram", {}).get(
            "push_schedule", ["09:05", "11:30", "13:35"]
        )
        self.fubon_api_key = os.getenv("FUBON_API_KEY", "")
        self.fubon_secret_key = os.getenv("FUBON_SECRET_KEY", "")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.cron_secret = os.getenv("CRON_SECRET", "")

    @property
    def holding_symbols(self):
        return [item["symbol"] for item in self.portfolio]


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings