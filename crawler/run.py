"""Điểm vào chạy Crawler chính."""

from datetime import datetime
from pathlib import Path
import logging
import sys

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
    logger.info("Bắt đầu truy vấn kết quả mới nhất từ cổng Vietlott...")
    raw_response = client.fetch_page(page_index=1, page_size=20)
    if not raw_response:
        logger.error("Không nhận được dữ liệu từ Vietlott.")
        return 0

    html_content = parse_ajaxpro_html_content(raw_response)
    if not html_content:
        logger.error("Không thể giải mã HtmlContent từ phản hồi.")
        return 0

    valid_records, error_records = parse_draw_rows(
        html_content, snapshot_id="live_crawl", fetched_at=fetched_at
    )
    logger.info(f"Phân tích thành công: {len(valid_records)} kỳ hợp lệ, {len(error_records)} lỗi.")

    # Lưu snapshot thô
    if valid_records:
        latest_id = valid_records[0]["draw_id"]
        latest_date = valid_records[0]["date"]
        storage.save_raw_snapshot(raw_response, latest_date, latest_id, fetched_at)

    count_new, new_ids = storage.append_new_draws(valid_records, error_records)
    if count_new > 0:
        first_id = new_ids[0]
        last_id = new_ids[-1]
        msg = f"data: +{count_new} draws (id {first_id}..{last_id})"
        logger.info(f"Đã lưu thành công: {msg}")
        print(msg)
        send_telegram_alert(f"🎯 <b>Cập nhật kết quả mới</b>: +{count_new} kỳ (Mã kỳ {first_id}..{last_id})")
    else:
        logger.info("Không có kỳ quay mới nào cần cập nhật.")

    return count_new


if __name__ == "__main__":
    run_crawler()
