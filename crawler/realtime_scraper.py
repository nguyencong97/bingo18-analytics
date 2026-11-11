"""Bộ bóc tách Realtime siêu tốc từ trang Thống Kê Vietlott Bingo 18.

Endpoint: https://vietlott.vn/vi/choi/bingo/thong-ke-so-trung
Tốc độ: < 0.3s (SSR Table trực tiếp hoặc qua Cloudflare Edge Proxy)
"""

from datetime import date, datetime, timedelta, timezone
import logging
import os
import re
from typing import Dict, List, Optional
import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))

# Mốc quy chiếu chuẩn xác: Kỳ #0195580 là kỳ 1 (slot 1) ngày 2026-11-11
ANCHOR_ID = 195580
ANCHOR_DATE = date(2026, 11, 11)


def compute_draw_metadata(num_id: int):
    """Tính toán ngày, slot và giờ quay từ mã kỳ theo lịch quay chuẩn Vietlott."""
    days_diff = (num_id - ANCHOR_ID) // 159
    draw_date = ANCHOR_DATE + timedelta(days=days_diff)
    slot = ((num_id - ANCHOR_ID) % 159) + 1
    total_minutes = 6 * 60 + slot * 6
    hour = total_minutes // 60
    minute = total_minutes % 60
    time_str = f"{hour:02d}:{minute:02d}"
    date_str = draw_date.strftime("%Y-%m-%d")
    draw_datetime = f"{date_str}T{time_str}:00+07:00"
    return date_str, time_str, slot, draw_datetime


def fetch_realtime_draws(proxy_base_url: Optional[str] = None) -> List[Dict]:
    """Lấy danh sách 10 kỳ quay mới nhất từ trang thống kê Vietlott.

    Thử qua Cloudflare Worker trước nếu có cấu hình, tự động fallback sang Vietlott trực tiếp.
    """
    candidates = []
    
    # 1. Thử qua Cloudflare Worker Proxy nếu có
    cf_url = proxy_base_url or os.getenv("CLOUDFLARE_WORKER_URL") or os.getenv("PROXY_URL")
    if cf_url:
        cf_clean = cf_url.rstrip("/")
        if not cf_clean.endswith("/thong-ke"):
            candidates.append(f"{cf_clean}/thong-ke")
        else:
            candidates.append(cf_clean)

    # 2. Luôn có endpoint trực tiếp Vietlott làm fallback
    candidates.append("https://vietlott.vn/vi/choi/bingo/thong-ke-so-trung")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }

    last_err = None
    for target_url in candidates:
        try:
            logger.info(f"Đang bóc tách Realtime từ: {target_url}")
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(target_url, headers=headers)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    records = parse_realtime_html(resp.text)
                    if records:
                        logger.info(f"⚡ Trích xuất thành công {len(records)} kỳ mới nhất qua Realtime Scraper!")
                        return records
        except Exception as e:
            last_err = e
            logger.warning(f"Lỗi khi truy vấn {target_url}: {e}")

    if last_err:
        logger.error(f"Tất cả các nguồn Realtime đều thất bại. Lỗi cuối: {last_err}")
    return []


def parse_realtime_html(html_text: str) -> List[Dict]:
    """Phân tích HTML bảng kết quả 10 kỳ mới nhất."""
    parser = HTMLParser(html_text)
    table = parser.css_first("table")
    if not table:
        return []

    rows = table.css("tr")
    if len(rows) < 5:
        return []

    # Row 0: Mã kỳ quay
    draw_cells = rows[0].css("th,td")[1:]
    draw_ids = [c.text().strip().replace("#", "").zfill(7) for c in draw_cells]

    # Row 1: Xúc xắc 1
    d1_cells = rows[1].css("th,td")[1:]
    d1_list = [int(re.sub(r"[^\d]", "", c.text())) for c in d1_cells if re.sub(r"[^\d]", "", c.text())]

    # Row 2: Xúc xắc 2 (Không có nhãn đầu hàng, 10 cells)
    d2_cells = rows[2].css("th,td")
    d2_list = [int(re.sub(r"[^\d]", "", c.text())) for c in d2_cells if re.sub(r"[^\d]", "", c.text())]

    # Row 3: Xúc xắc 3 (Không có nhãn đầu hàng, 10 cells)
    d3_cells = rows[3].css("th,td")
    d3_list = [int(re.sub(r"[^\d]", "", c.text())) for c in d3_cells if re.sub(r"[^\d]", "", c.text())]

    # Row 4: Tổng điểm
    tot_cells = rows[4].css("th,td")[1:]
    tot_list = [int(re.sub(r"[^\d]", "", c.text())) for c in tot_cells if re.sub(r"[^\d]", "", c.text())]

    n = min(len(draw_ids), len(d1_list), len(d2_list), len(d3_list), len(tot_list))
    if n == 0:
        return []

    fetched_at = datetime.now().isoformat()
    records = []

    for i in range(n):
        r_id = draw_ids[i]
        d1 = d1_list[i]
        d2 = d2_list[i]
        d3 = d3_list[i]
        tot = tot_list[i]

        # Kiểm định tính toàn vẹn số học
        if d1 + d2 + d3 != tot:
            logger.warning(f"Bỏ qua kỳ {r_id} do tổng điểm không khớp ({d1}+{d2}+{d3} != {tot})")
            continue

        num_id = int(r_id)
        date_str, time_str, slot, draw_datetime = compute_draw_metadata(num_id)

        rec = {
            "draw_id": r_id,
            "draw_datetime": draw_datetime,
            "date": date_str,
            "time": time_str,
            "slot_in_day": slot,
            "d1": str(d1),
            "d2": str(d2),
            "d3": str(d3),
            "total": str(tot),
            "result": f"{d1} {d2} {d3} {tot}",
            "source": "vietlott_realtime_ssr",
            "snapshot_id": f"realtime_{r_id}",
            "fetched_at": fetched_at,
            "status": "confirmed"
        }
        records.append(rec)

    # Sắp xếp theo thứ tự kỳ tăng dần
    records.sort(key=lambda x: int(x["draw_id"]))
    return records


if __name__ == "__main__":
    recs = fetch_realtime_draws()
    print(f"Bóc tách được {len(recs)} kỳ:")
    for r in recs:
        print(f"Kỳ #{r['draw_id']} ({r['date']} {r['time']} - Slot {r['slot_in_day']}): {r['d1']} - {r['d2']} - {r['d3']} = {r['total']}")
