"""Optional Telegram ping when something needs your approval."""
import logging

import httpx

from app.settings import get_settings

log = logging.getLogger(__name__)


def notify(text: str) -> None:
    s = get_settings()
    log.info("notify: %s", text)
    if not (s.telegram_bot_token and s.telegram_chat_id):
        return
    try:
        httpx.post(f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
                   json={"chat_id": s.telegram_chat_id, "text": text}, timeout=10)
    except Exception as e:  # noqa: BLE001
        log.warning("telegram notify failed: %s", e)
