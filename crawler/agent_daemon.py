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
import http.server
import json
import logging
import os
import socketserver
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
from crawler.realtime_scraper import compute_draw_metadata
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


# =========================================================================
# DANH MỤC LỆNH & MENU TƯƠNG TÁC TỰ ĐỘNG (DYNAMIC COMMAND REGISTRY)
# =========================================================================
BOT_COMMANDS = [
    {
        "command": "streak",
        "description": "📊 Nhịp gan cửa Lớn / Nhỏ / Hòa",
        "button": "📊 /streak",
        "aliases": ["/streak", "streak", "/cauthong", "/nhipgan", "📊 /streak", "nhịp gan", "cầu thông"]
    },
    {
        "command": "sync",
        "description": "🔄 Quét kết quả & đẩy Google Sheet",
        "button": "🔄 /sync",
        "aliases": ["/sync", "sync", "/dongbo", "🔄 /sync", "đồng bộ", "cập nhật"]
    },
    {
        "command": "status",
        "description": "📈 Trạng thái kỳ mới & tiến độ ngày",
        "button": "📈 /status",
        "aliases": ["/status", "status", "/trangthai", "📈 /status", "trạng thái"]
    },
    {
        "command": "predict",
        "description": "🔮 Phân tích & gợi ý kỳ kế tiếp",
        "button": "🔮 /predict",
        "aliases": ["/predict", "predict", "/dudoan", "🔮 /predict", "dự đoán"]
    },
    {
        "command": "help",
        "description": "ℹ️ Hướng dẫn & danh sách nút bấm",
        "button": "ℹ️ /help",
        "aliases": ["/help", "help", "/start", "start", "ℹ️ /help", "trợ giúp", "hướng dẫn"]
    }
]


def register_telegram_commands(token: str) -> bool:
    """Đăng ký danh sách lệnh vào Menu hệ thống của Telegram Bot."""
    if not token:
        return False
    try:
        base_url = f"https://api.telegram.org/bot{token}"
        commands_payload = [
            {"command": c["command"], "description": c["description"]}
            for c in BOT_COMMANDS
        ]
        res1 = httpx.post(f"{base_url}/setMyCommands", json={"commands": commands_payload}, timeout=10)
        menu_payload = {"menu_button": {"type": "commands"}}
        res2 = httpx.post(f"{base_url}/setChatMenuButton", json=menu_payload, timeout=10)
        ok = (res1.status_code == 200 and res2.status_code == 200)
        if ok:
            logger.info("Đã đăng ký thành công Menu lệnh với máy chủ Telegram!")
        return ok
    except Exception as e:
        logger.warning(f"Không thể kết nối Telegram để đăng ký commands: {e}")
        return False


def build_reply_keyboard() -> Dict:
    """Tạo bàn phím nút bấm cố định dưới màn hình chat."""
    buttons = [c["button"] for c in BOT_COMMANDS]
    keyboard = []
    row = []
    for b in buttons:
        row.append({"text": b})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "is_persistent": True
    }


class TelegramBotListener:
    """Lớp lắng nghe lệnh điều khiển từ xa từ người dùng qua Telegram Bot."""

    def __init__(self, token: str, authorized_chat_id: str):
        self.token = token
        self.chat_id = str(authorized_chat_id).strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        self.is_running = True
        register_telegram_commands(self.token)

    def send_message(self, text: str, reply_to_id: Optional[int] = None, with_keyboard: bool = True) -> bool:
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            if with_keyboard:
                payload["reply_markup"] = build_reply_keyboard()
            if reply_to_id:
                payload["reply_to_message_id"] = reply_to_id
            res = httpx.post(f"{self.base_url}/sendMessage", json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            logger.warning(f"Lỗi gửi tin nhắn Telegram: {e}")
            return False

    def handle_command(self, raw_input: str, message_id: int):
        clean_text = raw_input.strip()
        lower_text = clean_text.lower()
        logger.info(f"Nhận lệnh từ Telegram: {clean_text}")

        # Tìm command khớp trong BOT_COMMANDS
        matched_cmd = None
        for c in BOT_COMMANDS:
            if lower_text in [a.lower() for a in c["aliases"]]:
                matched_cmd = c["command"]
                break
            for a in c["aliases"]:
                if lower_text.startswith(a.lower()):
                    matched_cmd = c["command"]
                    break
            if matched_cmd:
                break

        if not matched_cmd:
            if clean_text.startswith("/"):
                self.send_message(
                    "⚠️ <b>Lệnh không xác định!</b>\n\nVui lòng bấm một trong các nút chức năng bên dưới bàn phím 👇",
                    message_id
                )
            return

        if matched_cmd == "help":
            help_lines = [
                "🤖 <b>BINGO18 PRO AGENT DAEMON</b>\n",
                "Bấm các nút bên dưới bàn phím hoặc mở menu <b>[/]</b> góc trái:"
            ]
            for c in BOT_COMMANDS:
                help_lines.append(f"• <b>/{c['command']}</b> : {c['description']}")
            help_lines.append("\n💡 <i>Hệ thống tự động theo dõi nhịp gan và cảnh báo kết quả 24/7.</i>")
            self.send_message("\n".join(help_lines), message_id)

        elif matched_cmd == "sync":
            self.send_message("⏳ Đang quét kết quả từ Vietlott và đồng bộ sang Google Sheet...", message_id)
            try:
                count_new = run_crawler(force_sync=True)
                latest = get_latest_local_draw()
                today_count = get_today_draws_count()
                if latest:
                    nid = int(latest["draw_id"])
                    date_str, time_str, slot, _ = compute_draw_metadata(nid)

                    from crawler.run import LAST_GAS_STATUS
                    gas_msg = ""
                    if LAST_GAS_STATUS["status"] == "ok":
                        gas_msg = f"🌐 Google Sheet: <b>Đã đồng bộ thành công! (+{LAST_GAS_STATUS['count_appended']} dòng mới)</b>"
                    elif LAST_GAS_STATUS["status"] == "processing-in-background":
                        gas_msg = "🌐 Google Sheet: <b>Dữ liệu đã nhận! Google Sheet đang tính toán lại 4 sheet ngầm (khoảng 30-60s).</b>"
                    elif LAST_GAS_STATUS["status"] == "no-gas-url":
                        gas_msg = "🌐 Google Sheet: <b>⚠️ Chưa cấu hình biến GAS_WEBAPP_URL trên Render!</b>"
                    elif LAST_GAS_STATUS["status"] == "non-json-200":
                        gas_msg = f"🌐 Google Sheet: <b>⚠️ Lỗi: Webhook bị chuyển hướng (Google Sign-In). Hãy triển khai lại Apps Script với quyền truy cập 'Anyone' (Bất kỳ ai).</b>"
                    elif LAST_GAS_STATUS["status"] != "pending":
                        gas_msg = f"🌐 Google Sheet: <b>⚠️ Lỗi ({LAST_GAS_STATUS['status']}):</b> <code>{str(LAST_GAS_STATUS['response'])[:120]}</code>"
                    else:
                        gas_msg = "🌐 Google Sheet: <b>Đang chờ lượt đồng bộ tiếp theo.</b>"

                    if count_new > 0:
                        msg = (
                            f"✅ <b>ĐỒNG BỘ THÀNH CÔNG (+{count_new} KỲ MỚI)</b>\n\n"
                            f"🎯 Đã cập nhật đến kỳ: <b>#{latest['draw_id']}</b>\n"
                            f"⏰ Giờ quay: <b>{time_str}</b> (Slot {slot}/159)\n"
                            f"🎲 Kết quả: <code>{latest['d1']} - {latest['d2']} - {latest['d3']}</code> (Tổng <b>{latest['total']}</b>)\n"
                            f"📅 Ngày: <b>{date_str}</b>\n"
                            f"📊 Tiến độ hôm nay: <b>{today_count}/159 kỳ</b>\n"
                            f"{gas_msg}"
                        )
                    else:
                        msg = (
                            f"✨ <b>HỆ THỐNG ĐÃ Ở TRẠNG THÁI MỚI NHẤT!</b>\n\n"
                            f"🎯 Đã cập nhật đến kỳ: <b>#{latest['draw_id']}</b>\n"
                            f"⏰ Giờ quay: <b>{time_str}</b> (Slot {slot}/159)\n"
                            f"🎲 Kết quả: <code>{latest['d1']} - {latest['d2']} - {latest['d3']}</code> (Tổng <b>{latest['total']}</b>)\n"
                            f"📅 Ngày: <b>{date_str}</b>\n"
                            f"📊 Tiến độ hôm nay: <b>{today_count}/159 kỳ</b>\n"
                            f"{gas_msg}"
                        )
                else:
                    msg = "⚠️ Không tìm thấy dữ liệu kỳ quay."
                self.send_message(msg, message_id)
            except Exception as e:
                self.send_message(f"❌ <b>Lỗi khi đồng bộ:</b> <code>{e}</code>", message_id)

        elif matched_cmd == "status":
            latest = get_latest_local_draw()
            today_count = get_today_draws_count()
            gas_status = "Đã cấu hình ✅" if os.getenv("GAS_WEBAPP_URL") else "Chưa cấu hình (đang dùng Git fallback) ⚠️"
            now_str = datetime.now(VN_TZ).strftime("%H:%M:%S %d/%m/%Y")

            if latest:
                nid = int(latest["draw_id"])
                _, time_str, slot, _ = compute_draw_metadata(nid)

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

        elif matched_cmd == "predict":
            latest = get_latest_local_draw()
            if latest:
                nid = int(latest["draw_id"])
                next_id = nid + 1
                _, next_time, next_slot, _ = compute_draw_metadata(next_id)

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

        elif matched_cmd == "streak":
            from crawler.streak_monitor import analyze_current_streaks, STAKING_PLAN, load_streak_state
            data_dir = ROOT_DIR / "data"
            analysis = analyze_current_streaks(data_dir)
            latest = analysis.get("latest_draw")
            streaks = analysis.get("streaks")
            if latest and streaks:
                curr_id = latest["draw_id"]
                tot = latest["total"]
                date_str, time_str, slot, _ = compute_draw_metadata(int(curr_id))

                def format_status(gap: int) -> str:
                    if gap >= 11:
                        step = gap - 10
                        if step <= len(STAKING_PLAN):
                            bet = STAKING_PLAN[step - 1]["bet"]
                            return f"🚨 <b>VÀO LỆNH (Bước {step}/7 - Cược {bet:,}đ)</b>"
                        return f"🛑 <b>Stop-loss ({gap} kỳ)</b>"
                    elif gap == 10:
                        return "⚠️ <b>Cảnh báo sớm (Chuẩn bị vốn)</b>"
                    elif gap >= 7:
                        return f"👀 Đang theo dõi ({gap} kỳ)"
                    return f"✅ Bình thường ({gap} kỳ)"

                stat_lon = format_status(streaks["LON"]["gap"])
                stat_nho = format_status(streaks["NHO"]["gap"])
                stat_hoa = f"{streaks['HOA']['gap']} kỳ liên tiếp"

                streak_text = (
                    "📊 <b>BẢNG THEO DÕI NHỊP GAN (STREAK MONITOR)</b>\n\n"
                    f"🎯 Kỳ mới nhất: <b>#{curr_id}</b> (Slot {slot}/159 lúc <b>{time_str}</b>)\n"
                    f"🎲 Kết quả: <code>{latest['d1']} - {latest['d2']} - {latest['d3']}</code> (Tổng <b>{tot}</b>)\n\n"
                    f"🔵 <b>Cửa LỚN (Tổng 12..18):</b>\n"
                    f"• Chưa về: <b>{streaks['LON']['gap']} kỳ liên tiếp</b>\n"
                    f"• Trạng thái: {stat_lon}\n\n"
                    f"🔴 <b>Cửa NHỎ (Tổng 3..9):</b>\n"
                    f"• Chưa về: <b>{streaks['NHO']['gap']} kỳ liên tiếp</b>\n"
                    f"• Trạng thái: {stat_nho}\n\n"
                    f"⚪ <b>Cửa HÒA (Tổng 10..11):</b> Chưa về {stat_hoa}\n\n"
                    f"💡 <i>Quy tắc: Khi cửa đạt 10 kỳ chưa về bot sẽ cảnh báo sớm; đạt ≥ 11 kỳ bot sẽ tự động bắn tín hiệu và mức tiền vào lệnh!</i>"
                )
            else:
                streak_text = "⚠️ Chưa có dữ liệu để phân tích nhịp gan."
            self.send_message(streak_text, message_id)

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
                            text = msg.get("text", "").strip()
                            msg_id = msg.get("message_id")
                            if text:
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
                # Trong giờ quay: kiểm tra mỗi 120 giây (2 phút) để bóc tách kết quả sớm nhất
                time.sleep(120)
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


def start_health_server():
    """Khởi chạy máy chủ HTTP tối giản phục vụ Health Check cho Render/Koyeb Web Service."""
    port_str = os.getenv("PORT")
    if not port_str:
        return
    try:
        port = int(port_str)
        class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                latest = get_latest_local_draw()
                from crawler.run import LAST_GAS_STATUS, LAST_CRAWL_STATUS
                resp = json.dumps({
                    "status": "healthy",
                    "service": "bingo18-agent-daemon",
                    "latest_draw": latest.get("draw_id") if latest else None,
                    "crawl_status": LAST_CRAWL_STATUS,
                    "gas_sync": LAST_GAS_STATUS
                })
                self.wfile.write(resp.encode("utf-8"))

            def log_message(self, format, *args):
                pass  # Tắt log HTTP của health check để không làm rác log

        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("0.0.0.0", port), HealthCheckHandler) as httpd:
            logger.info(f"Health Check Web Server đang lắng nghe trên cổng {port} cho Render...")
            httpd.serve_forever()
    except Exception as e:
        logger.warning(f"Lỗi khởi động Health Check Web Server: {e}")


def main():
    logger.info("==================================================")
    logger.info("   BINGO18 PRO AUTONOMOUS AGENT DAEMON 24/7      ")
    logger.info("==================================================")

    # 0. Khởi chạy Health Check Web Server nếu Render cấp biến PORT
    if os.getenv("PORT"):
        web_thread = threading.Thread(target=start_health_server, daemon=True)
        web_thread.start()

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
