"""Parser phân tích phản hồi từ Vietlott AjaxPro bằng selectolax."""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from selectolax.lexbor import LexborHTMLParser as HTMLParser

logger = logging.getLogger(__name__)


def parse_ajaxpro_html_content(raw_response_text: str) -> Optional[str]:
    """Trích xuất chuỗi HTML bên trong gói tin JSON AjaxPro."""
    try:
        data = json.loads(raw_response_text)
        val = data.get("value")
        if isinstance(val, dict):
            return val.get("HtmlContent")
        if isinstance(val, str):
            return val
    except Exception as e:
        logger.error(f"Lỗi giải mã JSON phản hồi từ Vietlott: {e}")
    return None


def parse_draw_rows(
    html_content: str, snapshot_id: str, fetched_at: Optional[str] = None
) -> Tuple[List[Dict], List[Dict]]:
    """Phân tích các dòng kết quả từ HTML bảng Vietlott.

    Trả về (valid_records, error_records).
    """
    if fetched_at is None:
        fetched_at = datetime.now().isoformat()

    parser = HTMLParser(html_content)
    table = parser.css_first("table")
    if not table:
        logger.warning("Không tìm thấy bảng kết quả trong HTML")
        return [], []

    valid_records: List[Dict] = []
    error_records: List[Dict] = []

    rows = table.css("tr")
    for r_idx, row in enumerate(rows):
        # Bỏ qua dòng tiêu đề có chứa th
        if row.css_first("th"):
            continue

        tds = row.css("td")
        if len(tds) < 4:
            continue

        try:
            # 1. Trích xuất Ngày và Mã kỳ từ tds[0]
            links = tds[0].css("a")
            if len(links) < 2:
                raise ValueError("Cột 1 thiếu liên kết Ngày hoặc Mã kỳ")

            date_raw = links[0].text().strip()
            # Định dạng: DD/MM/YYYY -> YYYY-MM-DD
            d_parts = date_raw.split("/")
            if len(d_parts) != 3:
                raise ValueError(f"Định dạng ngày không hợp lệ: {date_raw}")
            iso_date = f"{d_parts[2]}-{d_parts[1].zfill(2)}-{d_parts[0].zfill(2)}"

            draw_id_raw = links[1].text().strip()
            draw_id = draw_id_raw.replace("#", "").strip()
            if not draw_id.isdigit():
                raise ValueError(f"Mã kỳ quay không phải số: {draw_id_raw}")

            # 2. Trích xuất kết quả 3 viên xúc xắc từ tds[1]
            dice_spans = tds[1].css("span.bong_tron_bingo")
            if len(dice_spans) != 3:
                raise ValueError(f"Số lượng viên xúc xắc khác 3: {len(dice_spans)}")

            d1 = int(dice_spans[0].text().strip())
            d2 = int(dice_spans[1].text().strip())
            d3 = int(dice_spans[2].text().strip())

            for i, d in enumerate((d1, d2, d3), start=1):
                if not (1 <= d <= 6):
                    raise ValueError(f"Xúc xắc d{i}={d} nằm ngoài miền [1, 6]")

            # 3. Trích xuất Tổng từ tds[2]
            total_raw = tds[2].text().strip()
            total = int(total_raw)
            if total != (d1 + d2 + d3):
                raise ValueError(f"Tổng {total} không bằng {d1} + {d2} + {d3}")

            result_str = f"{d1} {d2} {d3} {total}"

            valid_records.append({
                "draw_id": draw_id,
                "draw_datetime": f"{iso_date}T00:00:00+07:00",
                "date": iso_date,
                "time": "",
                "slot_in_day": 0,
                "d1": d1,
                "d2": d2,
                "d3": d3,
                "total": total,
                "result": result_str,
                "source": "vietlott_official",
                "snapshot_id": snapshot_id,
                "fetched_at": fetched_at,
                "status": "confirmed"
            })

        except Exception as e:
            error_records.append({
                "draw_id": draw_id if "draw_id" in locals() else "",
                "raw_row": row.text().replace("\n", " ").strip(),
                "error_reason": str(e),
                "source": "vietlott_official",
                "timestamp": fetched_at
            })

    return valid_records, error_records
