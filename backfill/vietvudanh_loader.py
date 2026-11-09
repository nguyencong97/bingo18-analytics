"""Bộ nạp dữ liệu lịch sử từ kho lưu trữ vietvudanh/vietlott-data."""

import json
import logging
import urllib.request
from typing import Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

VIETVUDANH_BINGO18_URL = (
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/bingo18.jsonl"
)


def stream_vietvudanh_records(
    url: str = VIETVUDANH_BINGO18_URL, timeout: int = 30
) -> Generator[Dict, None, None]:
    """Tải và duyệt từng dòng dữ liệu từ kho GitHub."""
    req = urllib.request.Request(url, headers={"User-Agent": "Bingo18Analytics/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        for line_bytes in res:
            line_str = line_bytes.decode("utf-8").strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
                yield data
            except json.JSONDecodeError as e:
                logger.warning(f"Lỗi đọc JSON line: {e} trong dòng: {line_str}")


def normalize_vietvudanh_record(raw: Dict) -> Optional[Dict]:
    """Chuẩn hóa một bản ghi từ vietvudanh sang schema chuẩn của hệ thống.

    Kiểm tra tính hợp lệ: d1..d3 in [1..6] và sum == total.
    Trả về None nếu bản ghi không hợp lệ.
    """
    draw_id = str(raw.get("id", "")).strip().lstrip("#")
    if not draw_id:
        return None

    date_str = str(raw.get("date", "")).strip()
    result_list = raw.get("result", [])
    if len(result_list) != 3:
        return None

    try:
        d1, d2, d3 = (int(x) for x in result_list)
    except (ValueError, TypeError):
        return None

    if not (1 <= d1 <= 6 and 1 <= d2 <= 6 and 1 <= d3 <= 6):
        return None

    total = raw.get("total")
    if total is None or int(total) != (d1 + d2 + d3):
        return None
    total = int(total)

    result_str = f"{d1} {d2} {d3} {total}"
    process_time = raw.get("process_time", "")

    return {
        "draw_id": draw_id,
        "draw_datetime": f"{date_str}T00:00:00+07:00",  # Sẽ được hiệu chỉnh theo slot_in_day
        "date": date_str,
        "time": "",
        "slot_in_day": 0,
        "d1": d1,
        "d2": d2,
        "d3": d3,
        "total": total,
        "result": result_str,
        "source": "vietvudanh_github",
        "snapshot_id": f"gh_{draw_id}",
        "fetched_at": process_time,
        "status": "confirmed"
    }
