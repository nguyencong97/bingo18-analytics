"""Bingo18 Pro Autonomous Tool Agent & Telegram Bot Daemon.

Chạy nền liên tục 24/7 trên IP nội địa (Việt Nam) để:
1. Tự động quét kết quả Vietlott Bingo18 mỗi 3-6 phút trong khung giờ quay (06:00 - 22:05 VN).
2. Tự động PUSH dữ liệu mới sang Google Sheet qua Webhook doPost (GAS_WEBAPP_URL).
3. Tự động Git commit & push dữ liệu lên GitHub để sao lưu.
4. Tự động phát cảnh báo Telegram kết quả quay thưởng & PnL.
5. Lắng nghe lệnh từ người dùng trên Telegram:
   - /sync : Quét ngay lập tức và đẩy lên Google Sheet
   - /status : Kiểm tra trạng thái kỳ mới nhất và kết nối
   - /predict: Xem nhanh dự đoán kỳ kế tiếp
   - /help : Xem danh sách lệnh hỗ trợ
"""

import csv
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import httpx

# Thiết lập thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Nạp file .env thủ công (không cần thư viện python-dotenv)
def load_env_file():
    env_file = ROOT_DIR / ".env"
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

load_env_file()

from crawler.alerts import send_telegram_alert, ping_heartbeat
from crawler.run import run_crawler

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT_DIR / "agent_daemon.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("Bingo18Agent")

VN_TZ = timezone(timedelta(hours=7))


def get_latest_local_draw() -> Optional[Dict]:
    """Lấy thông tin kỳ quay mới nhất từ data/all.csv."""
    all_csv = ROOT_DIR / "data" / "all.csv"
    if not all_csv.exists() or all_csv.stat().st_size == 0:
        return None
    try:
        with open(all_csv, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            if reader:
                return reader[-1]
    except Exception as e:
        logger.warning(f"Lỗi đọc data/all.csv: {e}")
    return None


def get_today_draws_count() -> int:
    """Đếm số kỳ quay đã có trong ngày hôm nay."""
    all_csv = ROOT_DIR / "data" / "all.csv"
    if not all_csv.exists() or all_csv.stat().st_size == 0:
        return 0
    today_str = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    count = 0
    try:
        with open(all_csv, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("date") == today_str:
                    count += 1
    except Exception:
        pass
    return count


def git_backup(count_new: int, first_id: str, last_id: str):
    """Tự động commit và push dữ liệu mới lên GitHub."""
    try:
        msg = f"data: +{count_new} draws ({first_id}..{last_id}) [via Agent Daemon]"
        subprocess.run(["git", "add", "data/"], cwd=str(ROOT_DIR), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        res = subprocess.run(["git", "commit", "-m", msg], cwd=str(ROOT_DIR), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            logger.info("Đã commit dữ liệu mới vào Git.")
            # Thử push nếu có credentials
            push_res = subprocess.run(["git", "push"], cwd=str(ROOT_DIR), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if push_res.returncode == 0:
                logger.info("Đã đồng bộ Git push lên GitHub thành công.")
    except Exception as e:
        logger.debug(f"Git backup skipped: {e}")


def push_to_gas_webhook(records: List[Dict]) -> bool:
    """Chủ động đẩy danh sách kỳ quay sang Google Apps Script doPost."""
    gas_url = os.getenv("GAS_WEBAPP_URL")
    if not gas_url:
        return False
    try:
        res = httpx.post(gas_url, json={"records": records}, timeout=30, follow_redirects=True)
        if res.status_code == 200:
            logger.info(f"Đã PUSH {len(records)} kỳ sang Google Sheet thành công.")
            return True
        else:
            logger.warning(f"Google Sheet trả về mã lỗi: {res.status_code}")
    except Exception as e:
        logger.warning(f"Lỗi khi gửi webhook sang Google Sheet: {e}")
    return False


class TelegramBotListener:
    """Lớp lắng nghe lệnh điều khiển từ xa từ người dùng qua Telegram Bot."""

    def __init__(self, token: str, authorized_chat_id: str):
        self.token = token
        self.chat_id = str(authorized_chat_id).strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        self.is_running = True

    def send_message(self, text: str, reply_to_id: Optional[int] = None) -> bool:
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            if reply_to_id:
                payload["reply_to_message_id"] = reply_to_id
            res = httpx.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            logger.warning(f"Lỗi gửi tin nhắn Telegram: {e}")
            return False

    def handle_command(self, cmd: str, message_id: int):
        cmd = cmd.strip().lower()
        logger.info(f"Nhận lệnh từ Telegram: {cmd}")

        if cmd in ("/start", "/help"):
            help_text = (
                "🤖 <b>BINGO18 PRO AGENT DAEMON</b>\n\n"
                "Danh sách các lệnh hỗ trợ:\n"
                "• <b>/sync</b> hoặc <b>/dongbo</b> : Quét kết quả mới nhất từ Vietlott và PUSH ngay lên Google Sheet\n"
                "• <b>/status</b> : Kiểm tra trạng thái kỳ mới nhất, số kỳ hôm nay và kết nối\n"
                "• <b>/predict</b> : Xem nhanh dự đoán kỳ kế tiếp\n"
                "• <b>/help</b> : Xem lại danh sách này"
            )
            self.send_message(help_text, message_id)

        elif cmd in ("/sync", "/dongbo"):
            self.send_message("⏳ Đang quét kết quả từ Vietlott và đẩy sang Google Sheet...", message_id)
            try:
                count_new = run_crawler()
                latest = get_latest_local_draw()
                if count_new > 0 and latest:
                    msg = (
                        f"✅ <b>Đồng bộ thành công!</b>\n"
                        f"+{count_new} kỳ quay mới đã được lưu và cập nhật lên Google Sheet.\n"
                        f"🎯 Kỳ mới nhất: <b>#{latest['draw_id']}</b>\n"
                        f"🎲 Kết quả: <code>{latest['d1']} - {latest['d2']} - {latest['d3']}</code> (Tổng <b>{latest['total']}</b>)\n"
                        f"📅 Ngày: {latest['date']}"
                    )
                else:
                    draw_id = latest['draw_id'] if latest else 'N/A'
                    msg = (
                        f"✨ <b>Hệ thống đã ở trạng thái mới nhất!</b>\n"
                        f"Chưa có kỳ quay mới từ Vietlott.\n"
                        f"🎯 Kỳ hiện tại: <b>#{draw_id}</b>"
                    )
                self.send_message(msg, message_id)
            except Exception as e:
                self.send_message(f"❌ <b>Lỗi khi đồng bộ:</b> <code>{e}</code>", message_id)

        elif cmd in ("/status", "/trangthai"):
            latest = get_latest_local_draw()
            today_count = get_today_draws_count()
            gas_status = "Đã cấu hình ✅" if os.getenv("GAS_WEBAPP_URL") else "Chưa cấu hình (đang dùng Git fallback) ⚠️"
            now_str = datetime.now(VN_TZ).strftime("%H:%M:%S %d/%m/%Y")

            if latest:
                nid = int(latest["draw_id"])
                slot = ((nid - 195421) % 159 + 1)
                tot_min = 6 * 60 + slot * 6
                time_str = f"{tot_min // 60:02d}:{tot_min % 60:02d}"

                status_text = (
                    "📊 <b>TRẠNG THÁI BINGO18 AGENT DAEMON</b>\n\n"
                    f"⏰ Thời gian hiện tại: <code>{now_str}</code>\n"
                    f"🎯 Kỳ mới nhất: <b>#{latest['draw_id']}</b> (Slot {slot}/159 - {time_str})\n"
                    f"🎲 Kết quả: <code>{latest['d1']} - {latest['d2']} - {latest['d3']}</code> (Tổng <b>{latest['total']}</b>)\n"
                    f"📈 Số kỳ đã quay hôm nay: <b>{today_count}/159</b>\n"
                    f"🌐 Google Sheet Webhook: {gas_status}\n"
                    f"⚙️ Trạng thái Agent: <b>Hoạt động 24/7 (IP Nội địa VN)</b>"
                )
            else:
                status_text = "⚠️ Chưa tìm thấy dữ liệu kỳ quay trong data/all.csv"
            self.send_message(status_text, message_id)

        elif cmd in ("/predict", "/dudoan"):
            latest = get_latest_local_draw()
            if latest:
                nid = int(latest["draw_id"])
                next_id = nid + 1
                next_slot = ((next_id - 195421) % 159 + 1)
                tot_min = 6 * 60 + next_slot * 6
                next_time = f"{tot_min // 60:02d}:{tot_min % 60:02d}"

                p_text = (
                    f"🔮 <b>GỢI Ý KỲ TIẾP THEO #{str(next_id).zfill(7)}</b>\n"
                    f"⏰ Giờ quay: <b>{next_time}</b> (Slot {next_slot}/159)\n\n"
                    f"💡 <i>Gợi ý theo Kịch bản 3 (Đa tầng & Quản trị tài chính):</i>\n"
                    f"• Xem bảng chi tiết và tỷ lệ trúng tối ưu trực tiếp trên Google Sheet tab 'Dự đoán & Phân tích'.\n"
                    f"• Bấm <b>/sync</b> sau giờ quay để cập nhật ngay kết quả kỳ này!"
                )
            else:
                p_text = "⚠️ Chưa có dữ liệu để tính toán kỳ tiếp theo."
            self.send_message(p_text, message_id)

    def run_polling(self):
        logger.info("Telegram Bot Listener đã sẵn sàng lắng nghe lệnh từ người dùng...")
        while self.is_running:
            try:
                url = f"{self.base_url}/getUpdates"
                params = {"timeout": 20}
                if self.last_update_id > 0:
                    params["offset"] = self.last_update_id + 1

                res = httpx.get(url, params=params, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    updates = data.get("result", [])
                    for u in updates:
                        self.last_update_id = u["update_id"]
                        msg = u.get("message")
                        if not msg:
                            continue
                        from_id = str(msg.get("chat", {}).get("id", ""))
                        # Chỉ phản hồi cho tài khoản được cấu hình
                        if from_id == self.chat_id:
                            text = msg.get("text", "")
                            msg_id = msg.get("message_id")
                            if text.startswith("/"):
                                self.handle_command(text, msg_id)
            except Exception as e:
                logger.debug(f"Telegram polling tick: {e}")
                time.sleep(3)


def autonomous_loop():
    """Vòng lặp tự động quét theo lịch quay của Vietlott."""
    logger.info("🚀 Bắt đầu vòng lặp tự động hóa Bingo18 Pro Agent Daemon...")
    while True:
        try:
            now_vn = datetime.now(VN_TZ)
            hour = now_vn.hour
            minute = now_vn.minute

            # Khung giờ quay số Bingo18: từ 06:00 đến 22:05 hàng ngày
            if 6 <= hour < 22 or (hour == 22 and minute <= 5):
                logger.info(f"[{now_vn.strftime('%H:%M:%S')}] Kiểm tra kỳ quay mới từ Vietlott...")
                count_new = run_crawler()
                if count_new > 0:
                    latest = get_latest_local_draw()
                    if latest:
                        # Backup Git
                        git_backup(count_new, latest["draw_id"], latest["draw_id"])

                ping_heartbeat("ok")
                # Trong giờ quay: nghỉ 180 giây (3 phút) rồi kiểm tra tiếp
                time.sleep(180)
            else:
                logger.info(f"[{now_vn.strftime('%H:%M:%S')}] Ngoài giờ quay số Bingo18 (06:00 - 22:05 VN). Chế độ nghỉ đêm.")
                # Ngoài giờ quay: nghỉ 10 phút rồi kiểm tra lại giờ
                time.sleep(600)

        except KeyboardInterrupt:
            logger.info("Dừng Daemon theo yêu cầu người dùng.")
            break
        except Exception as e:
            logger.error(f"Lỗi bất thường trong vòng lặp: {e}")
            time.sleep(30)


def main():
    logger.info("==================================================")
    logger.info("   BINGO18 PRO AUTONOMOUS AGENT DAEMON 24/7      ")
    logger.info("==================================================")

    # 1. Khởi chạy Telegram Listener nếu có token & chat_id
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if bot_token and chat_id:
        bot = TelegramBotListener(bot_token, chat_id)
        bot_thread = threading.Thread(target=bot.run_polling, daemon=True)
        bot_thread.start()
        logger.info(f"Đã kích hoạt Telegram Bot điều khiển (@bingo182026bot)")
    else:
        logger.warning("Chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID. Bot điều khiển bị tắt.")

    # 2. Chạy vòng lặp tự động hóa chính
    autonomous_loop()


if __name__ == "__main__":
    main()
