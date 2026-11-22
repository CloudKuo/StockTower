import requests

API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramClient:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_ids = (
            [cid.strip() for cid in str(chat_id).split(",") if cid.strip()]
            if not isinstance(chat_id, (list, tuple))
            else [str(cid).strip() for cid in chat_id if str(cid).strip()]
        )

    def send(self, text):
        if not self.token or not self.chat_ids:
            raise ValueError("TELEGRAM_BOT_TOKEN / chat_id 未設定")
        url = API_BASE.format(token=self.token)
        results = []
        for chat_id in self.chat_ids:
            resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)
            resp.raise_for_status()
            results.append(resp.json().get("ok"))
        return all(results)