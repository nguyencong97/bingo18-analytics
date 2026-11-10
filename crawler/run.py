"""Điểm vào chạy Crawler chính."""

from datetime import datetime
from pathlib import Path
import logging
import os
import sys
import httpx

from crawler.client import VietlottClient
from crawler.parser import parse_ajaxpro_html_content, parse_draw_rows
from crawler.storage import DataStorage
from crawler.alerts import send_telegram_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def run_crawler() -> int:
    """Thực thi một chu kỳ cào kết quả Bingo18.

    Trả về số lượng kỳ quay mới được thêm vào.
    """
    sys.stdout.reconfigure(encoding="utf-8")
    data_dir = Path(__file__).resolve().parent.parent / "data"
    storage = DataStorage(data_dir=data_dir)
    client = VietlottClient()

    fetched_at = datetime.now().isoformat()
    logger.info("Bắt đầu truy vấn kết quả mới nhất từ cổng Vietlott qua đa trang...")
    
    all_valid_records = []
    all_error_records = []
    first_raw_response = None
    existing_all_ids = set()
    
    # Đọc nhanh các ID gần nhất từ all.csv để dừng lặp sớm
    all_csv_path = data_dir / "all.csv"
    if all_csv_path.exists():
        try:
            with open(all_csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-200:]:
                    parts = line.strip().split(",")
                    if parts and parts[0] != "draw_id":
                        existing_all_ids.add(parts[0].replace("#", "").strip().zfill(7))
        except Exception as e:
            logger.warning(f"Không thể đọc nhanh ID cũ: {e}")

    for page in range(1, 16):
        raw_response = client.fetch_page(page_index=page, page_size=10)
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
            logger.info(f"Đã chạm đến kỳ quay đã có sẵn tại trang {page}. Dừng quét.")
            break

    logger.info(f"Phân tích thành công: {len(all_valid_records)} kỳ hợp lệ mới, {len(all_error_records)} lỗi.")

    # Lưu snapshot thô
    if all_valid_records and first_raw_response:
        latest_id = all_valid_records[0]["draw_id"]
        latest_date = all_valid_records[0]["date"]
        storage.save_raw_snapshot(first_raw_response, latest_date, latest_id, fetched_at)

    count_new, new_ids = storage.append_new_draws(all_valid_records, all_error_records)
    if count_new > 0:
        first_id = new_ids[0]
        last_id = new_ids[-1]
        msg = f"data: +{count_new} draws (id {first_id}..{last_id})"
        logger.info(f"Đã lưu thành công: {msg}")
        print(msg)
        send_telegram_alert(f"🎯 <b>Cập nhật kết quả mới</b>: +{count_new} kỳ (Mã kỳ {first_id}..{last_id})")
        gas_url = os.environ.get("GAS_WEBAPP_URL")
        if gas_url:
            try:
                new_records = [r for r in valid_records if r["draw_id"] in new_ids]
                httpx.post(gas_url, json={"records": new_records}, timeout=15, follow_redirects=True)
                logger.info(f"Đã đồng bộ {len(new_records)} kỳ sang Google Sheet thành công.")
            except Exception as e:
                logger.warning(f"Lỗi khi đồng bộ Google Sheet: {e}")
    else:
        logger.info("Không có kỳ quay mới nào cần cập nhật.")

    return count_new


if __name__ == "__main__":
    run_crawler()
