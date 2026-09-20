from datetime import date

import requests

MI_INDEX_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"


def is_trading_day(day=None):
    day = day or date.today()
    if day.weekday() >= 5:
        return False
    ymd = day.strftime("%Y%m%d")
    try:
        resp = requests.get(
            MI_INDEX_URL,
            params={"date": ymd, "response": "json"},
            timeout=10,
        )
        return resp.json().get("stat") == "OK"
    except Exception:
        return True