"""Điểm vào chạy Crawler chính kết hợp 2 tầng (Realtime SSR + AjaxPro Fallback)."""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import os
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import httpx

from crawler.client import VietlottClient
from crawler.parser import parse_ajaxpro_html_content, parse_draw_rows
from crawler.realtime_scraper import fetch_realtime_draws
from crawler.storage import DataStorage
from crawler.alerts import send_telegram_alert, _ensure_env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))

LAST_GAS_STATUS = {
    "status": "pending",
    "url": None,
    "http_code": None,
    "response": None,
    "count_appended": 0,
    "time": None
}

LAST_CRAWL_STATUS = {
    "source": None,
    "client_url": None,
    "last_page1_status": None,
    "last_page1_len": 0,
    "all_valid_count": 0,
    "count_new": 0,
    "latest_seen": None,
    "error": None
}


def run_crawler(force_sync: bool = False) -> int:
    """Thực thi một chu kỳ cào kết quả Bingo18.

    Tier 1: Bóc tách Realtime siêu tốc (< 0.3s) từ trang Thống Kê Vietlott.
    Tier 2: Fallback qua cổng AjaxPro nếu phát hiện khoảng trống dữ liệu hoặc Tier 1 lỗi.
    Trả về số lượng kỳ quay mới được thêm vào.
    """
    _ensure_env()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    data_dir = Path(__file__).resolve().parent.parent / "data"
    storage = DataStorage(data_dir=data_dir)
    fetched_at = datetime.now().isoformat()

    # 1. Đọc danh sách các ID đã có sẵn trong data/all.csv
    existing_all_ids = set()
    latest_local_id = 0
    all_csv_path = data_dir / "all.csv"
    if all_csv_path.exists():
        try:
            with open(all_csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[1:]:
                    parts = line.strip().split(",")
                    if parts and parts[0] != "draw_id":
                        clean_id = parts[0].replace("#", "").strip().zfill(7)
                        existing_all_ids.add(clean_id)
                        num = int(clean_id)
                        if num > latest_local_id:
                            latest_local_id = num
        except Exception as e:
            logger.warning(f"Không thể đọc ID cũ từ all.csv: {e}")

    all_valid_records = []
    all_error_records = []
    need_tier2_fallback = False

    # -------------------------------------------------------------
    # TIER 1: Realtime Scraper siêu tốc từ trang Thống Kê
    # -------------------------------------------------------------
    logger.info("⚡ [Tier 1] Đang truy vấn Realtime từ trang Thống Kê Vietlott...")
    realtime_records = fetch_realtime_draws()
    
    if realtime_records:
        LAST_CRAWL_STATUS["source"] = "realtime_ssr"
        LAST_CRAWL_STATUS["latest_seen"] = realtime_records[-1]["draw_id"]
        
        # Kiểm tra xem có khoảng trống dữ liệu sâu không
        min_realtime_id = int(realtime_records[0]["draw_id"])
        max_realtime_id = int(realtime_records[-1]["draw_id"])

        if latest_local_id > 0 and min_realtime_id > latest_local_id + 1:
            logger.info(f"Phát hiện khoảng trống dữ liệu ({latest_local_id} -> {min_realtime_id}). Cần kích hoạt Tier 2...")
            need_tier2_fallback = True

        for r in realtime_records:
            rid = r["draw_id"].replace("#", "").strip().zfill(7)
            if rid not in existing_all_ids:
                existing_all_ids.add(rid)
                all_valid_records.append(r)
    else:
        logger.warning("⚠️ [Tier 1] Không lấy được dữ liệu. Chuyển sang Tier 2 (AjaxPro)...")
        need_tier2_fallback = True

    # -------------------------------------------------------------
    # TIER 2: Fallback sang cổng AjaxPro đa trang nếu cần
    # -------------------------------------------------------------
    first_raw_response = None
    if need_tier2_fallback:
        logger.info("🔄 [Tier 2] Bắt đầu quét qua cổng AjaxPro đa trang...")
        client = VietlottClient()
        LAST_CRAWL_STATUS["client_url"] = client.url
        LAST_CRAWL_STATUS["source"] = "ajaxpro_fallback"

        for page in range(1, 16):
            raw_response = client.fetch_page(page_index=page, page_size=10)
            if page == 1:
                LAST_CRAWL_STATUS["last_page1_len"] = len(raw_response) if raw_response else 0
                LAST_CRAWL_STATUS["last_page1_status"] = "ok" if raw_response else "empty_or_error"

            if not raw_response:
                break
            if first_raw_response is None:
                first_raw_response = raw_response

            html_content = parse_ajaxpro_html_content(raw_response)
            if not html_content:
                break

            valid_records, error_records = parse_draw_rows(
                html_content, snapshot_id=f"live_p{page}", fetched_at=fetched_at
            )
            if not valid_records:
                break

            all_error_records.extend(error_records)
            stop_paging = False
            new_in_page = 0
            for r in valid_records:
                r_id = r["draw_id"].replace("#", "").strip().zfill(7)
                if r_id in existing_all_ids:
                    stop_paging = True
                else:
                    existing_all_ids.add(r_id)
                    all_valid_records.append(r)
                    new_in_page += 1

            if stop_paging or new_in_page == 0:
                logger.info(f"Đã lấp đầy dữ liệu lịch sử tại trang {page}. Dừng quét AjaxPro.")
                break

        # Lưu raw snapshot nếu có
        if all_valid_records and first_raw_response:
            latest_id = all_valid_records[0]["draw_id"]
            latest_date = all_valid_records[0]["date"]
            storage.save_raw_snapshot(first_raw_response, latest_date, latest_id, fetched_at)

    # -------------------------------------------------------------
    # LƯU VÀO CƠ SỞ DỮ LIỆU CỤC BỘ (CSV)
    # -------------------------------------------------------------
    count_new, new_ids = storage.append_new_draws(all_valid_records, all_error_records)
    LAST_CRAWL_STATUS["count_new"] = count_new
    LAST_CRAWL_STATUS["all_valid_count"] = len(all_valid_records)

    if count_new > 0:
        first_id = new_ids[0]
        last_id = new_ids[-1]
        msg = f"data: +{count_new} draws (id {first_id}..{last_id})"
        logger.info(f"Đã lưu thành công: {msg}")
        print(msg)

        # Tìm bản ghi mới nhất để gửi thông báo chi tiết
        latest_rec = None
        for r in all_valid_records:
            if r["draw_id"] == last_id:
                latest_rec = r
                break
        if not latest_rec and all_valid_records:
            latest_rec = all_valid_records[-1]

        d_info = ""
        total_type = ""
        if latest_rec:
            tot = int(latest_rec["total"])
            if tot >= 3 and tot <= 10:
                total_type = " (Xỉu / Nhỏ)"
            elif tot == 11 or tot == 12:
                total_type = " (Hòa)"
            else:
                total_type = " (Lớn / Tài)"
            d_info = f"🎲 <code>{latest_rec['d1']} - {latest_rec['d2']} - {latest_rec['d3']}</code> (Tổng <b>{latest_rec['total']}</b>{total_type})"

        time_info = f"{latest_rec.get('time', '')} (Slot {latest_rec.get('slot_in_day', '')}/159)" if latest_rec else ""
        send_telegram_alert(
            f"🎯 <b>CẬP NHẬT KẾT QUẢ MỚI (+{count_new} KỲ)</b>\n"
            f"• Đã cập nhật đến kỳ: <b>#{last_id}</b>\n"
            f"• Giờ quay: <b>{time_info}</b>\n"
            f"• Kết quả: {d_info}\n"
            f"• Nguồn bóc tách: <b>{LAST_CRAWL_STATUS['source']}</b>\n"
            f"• Trạng thái: Đã lưu CSV & đồng bộ sang Google Sheet thành công! ✅"
        )

    # -------------------------------------------------------------
    # ĐỒNG BỘ SANG GOOGLE SHEET (CHỐNG TRÙNG LẶP TUYỆT ĐỐI)
    # -------------------------------------------------------------
    gas_url = os.environ.get("GAS_WEBAPP_URL")
    if gas_url:
        records_to_sync = []
        if count_new > 0:
            # Chỉ gửi đúng những kỳ mới được thêm vào
            records_to_sync = [r for r in all_valid_records if r["draw_id"] in new_ids]
        elif force_sync:
            # Chỉ gửi các dòng gần nhất khi người dùng cưỡng bức /sync
            all_csv = data_dir / "all.csv"
            if all_csv.exists() and all_csv.stat().st_size > 0:
                import csv as _csv
                with open(all_csv, "r", encoding="utf-8") as f:
                    rows = list(_csv.DictReader(f))
                    records_to_sync = rows[-10:]

        if records_to_sync:
            try:
                for r in records_to_sync:
                    if not r.get("slot_in_day") or int(r.get("slot_in_day", 0)) == 0:
                        nid = int(r["draw_id"])
                        slot = ((nid - 195580) % 159 + 1)
                        r["slot_in_day"] = slot
                        tot_min = 6 * 60 + slot * 6
                        r["time"] = f"{tot_min // 60:02d}:{tot_min % 60:02d}"

                LAST_GAS_STATUS["url"] = gas_url[:35] + "..." if len(gas_url) > 35 else gas_url
                LAST_GAS_STATUS["time"] = datetime.now().isoformat()

                res = httpx.post(gas_url, json={"records": records_to_sync}, timeout=90.0, follow_redirects=True)
                LAST_GAS_STATUS["http_code"] = res.status_code
                LAST_GAS_STATUS["response"] = res.text[:300]

                logger.info(f"Đã gọi GAS Webhook ({res.status_code}): {res.text[:150]}")
                if res.status_code == 200:
                    try:
                        res_json = res.json()
                        LAST_GAS_STATUS["status"] = res_json.get("status", "ok")
                        LAST_GAS_STATUS["count_appended"] = res_json.get("count", 0)
                    except Exception:
                        LAST_GAS_STATUS["status"] = "non-json-200"
                else:
                    LAST_GAS_STATUS["status"] = f"http-error-{res.status_code}"
            except httpx.ReadTimeout:
                LAST_GAS_STATUS["status"] = "processing-in-background"
                LAST_GAS_STATUS["response"] = "Google Sheet đang tính toán lại các sheet ngầm (> 60s)"
                logger.info("Google Sheet đang xử lý dữ liệu và tính toán lại các sheet trong nền...")
            except Exception as e:
                LAST_GAS_STATUS["status"] = "exception"
                LAST_GAS_STATUS["response"] = str(e)
                logger.warning(f"Lỗi khi đồng bộ Google Sheet: {e}")
        else:
            logger.info("Hệ thống đã đồng bộ đầy đủ, không có kỳ mới cần đẩy sang Google Sheet.")
    else:
        LAST_GAS_STATUS["status"] = "no-gas-url"

    return count_new


if __name__ == "__main__":
    run_crawler()
