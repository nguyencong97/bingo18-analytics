"""Mô-đun phát cảnh báo Telegram và Heartbeat Healthchecks.io."""

import logging
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _ensure_env():
    """Tự động nạp biến môi trường từ .env nếu chưa có."""
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        env_file = Path(__file__).resolve().parent.parent / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ or not os.environ[k]:
                            os.environ[k] = v


def send_telegram_alert(message: str) -> bool:
    """Gửi tin nhắn cảnh báo tới Telegram Bot qua biến môi trường."""
    _ensure_env()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": f"🚨 [Bingo18 Analytics Alert]\n{message}",
        "parse_mode": "HTML"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status == 200
    except Exception as e:
        logger.error(f"Lỗi khi gửi cảnh báo Telegram: {e}")
        return False


def ping_heartbeat(status: str = "ok") -> bool:
    """Gửi tín hiệu sống (heartbeat) tới Healthchecks.io."""
    hc_url = os.getenv("HEALTHCHECKS_URL")
    if not hc_url:
        return False

    url = hc_url.rstrip("/")
    if status != "ok":
        url = f"{url}/fail"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Bingo18Analytics/1.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status == 200
    except Exception as e:
        logger.error(f"Lỗi khi ping Healthchecks: {e}")
        return False


def post_to_google_sheet(draw_record: dict) -> bool:
    """Gửi dòng mới tới Google Apps Script Web App để append vào Google Sheet."""
    gas_url = os.getenv("GAS_WEBAPP_URL")
    gas_token = os.getenv("GAS_WEBAPP_TOKEN", "")
    if not gas_url:
        return False

    import json
    payload = json.dumps({"token": gas_token, "record": draw_record}).encode("utf-8")
    try:
        req = urllib.request.Request(
            gas_url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status == 200
    except Exception as e:
        logger.error(f"Lỗi khi gửi bản ghi tới Google Sheet Webhook: {e}")
        return False
