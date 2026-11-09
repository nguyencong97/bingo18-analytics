"""Bộ phân tích (parser) cho sheet 'Chi tiết' từ Google Sheets của người dùng.

Hỗ trợ đọc từ tệp CSV cục bộ hoặc tải trực tiếp qua Google Sheets Export URL.
Tuân thủ nguyên tắc:
1. Dữ liệu thật 100%: không nội suy, không đoán mò, không sửa kỳ lỗi.
2. Ràng buộc d1..d3 in [1..6] và sum == total.
3. Bản ghi lỗi đưa vào errors.csv, KHÔNG vào dữ liệu chính.
"""

import csv
import io
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import urllib.request


def parse_cell_result(cell_text: str) -> Optional[Tuple[int, int, int, int]]:
    """Phân tích nội dung ô kết quả.

    Ví dụ: '2\\n5\\n1\\n\\n8' hoặc '2 5 1 8' -> (2, 5, 1, 8)
    Trả về None nếu ô trống.
    Ném ValueError nếu định dạng không hợp lệ hoặc sai ràng buộc toán học.
    """
    if not cell_text:
        return None
    cleaned = cell_text.strip()
    if not cleaned:
        return None

    # Tách theo khoảng trắng hoặc xuống dòng
    tokens = [t for t in re.split(r'[\s\n\r]+', cleaned) if t]
    if len(tokens) != 4:
        raise ValueError(f"Số lượng phần tử khác 4: {tokens}")

    try:
        d1, d2, d3, total = (int(t) for t in tokens)
    except ValueError as e:
        raise ValueError(f"Giá trị không phải số nguyên: {tokens}") from e

    # Ràng buộc miền giá trị
    for idx, d in enumerate((d1, d2, d3), start=1):
        if not (1 <= d <= 6):
            raise ValueError(f"Xúc xắc d{idx}={d} ngoài khoảng [1, 6]")

    # Ràng buộc tổng
    if d1 + d2 + d3 != total:
        raise ValueError(f"Tổng {total} không khớp với {d1} + {d2} + {d3} = {d1+d2+d3}")

    return d1, d2, d3, total


def normalize_date_column(col_header: str, default_year: int = 2026) -> Optional[str]:
    """Chuẩn hóa tiêu đề cột ngày thành định dạng ISO YYYY-MM-DD.

    Ví dụ: '01/11' -> '2026-11-01'
    'Hôm nay' -> ánh xạ tới ngày hiện tại hoặc 2026-11-09 nếu trong bối cảnh dữ liệu.
    """
    header = col_header.strip()
    if not header or header.lower() == "thời gian":
        return None

    if "hôm nay" in header.lower():
        # Cột 'Hôm nay' trong sheet nằm giữa 08/11 và 10/11 -> 2026-11-09
        return f"{default_year:04d}-11-09"

    match = re.match(r"^(\d{1,2})/(\d{1,2})$", header)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        return f"{default_year:04d}-{month:02d}-{day:02d}"

    match_full = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", header)
    if match_full:
        day, month, year = int(match_full.group(1)), int(match_full.group(2)), int(match_full.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    return None


class UserSheetParser:
    """Parser xử lý toàn diện bảng Chi tiết."""

    def __init__(self, default_year: int = 2026):
        self.default_year = default_year

    def parse_csv_content(
        self, csv_text: str, fetched_at: Optional[str] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """Phân tích toàn bộ nội dung CSV của sheet Chi tiết.

        Trả về (valid_records, error_records)
        """
        if fetched_at is None:
            fetched_at = datetime.now().isoformat()

        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)
        if not rows:
            return [], []

        header = rows[0]
        # Tìm các cột ngày hợp lệ
        date_columns: List[Tuple[int, str]] = []
        for col_idx in range(1, len(header)):
            iso_date = normalize_date_column(header[col_idx], default_year=self.default_year)
            if iso_date:
                date_columns.append((col_idx, iso_date))

        valid_records: List[Dict] = []
        error_records: List[Dict] = []

        # Duyệt từng dòng (khung giờ)
        for row_idx, row in enumerate(rows[1:], start=1):
            if not row or not row[0].strip():
                continue
            time_str = row[0].strip()
            slot_in_day = row_idx  # 1..159

            for col_idx, iso_date in date_columns:
                if col_idx >= len(row):
                    continue
                cell_val = row[col_idx].strip()
                if not cell_val:
                    continue  # Ô trống không phải lỗi

                try:
                    res = parse_cell_result(cell_val)
                    if res is None:
                        continue
                    d1, d2, d3, total = res
                    result_str = f"{d1} {d2} {d3} {total}"
                    draw_datetime = f"{iso_date}T{time_str}:00+07:00"

                    valid_records.append({
                        "draw_id": "",  # Sẽ được ghép nối (reconcile) qua ID chính thức
                        "draw_datetime": draw_datetime,
                        "date": iso_date,
                        "time": time_str,
                        "slot_in_day": slot_in_day,
                        "d1": d1,
                        "d2": d2,
                        "d3": d3,
                        "total": total,
                        "result": result_str,
                        "source": "user_sheet",
                        "snapshot_id": "google_sheet_user",
                        "fetched_at": fetched_at,
                        "status": "confirmed"
                    })
                except Exception as e:
                    error_records.append({
                        "draw_id": "",
                        "raw_row": f"{iso_date} {time_str} [slot {slot_in_day}]: {repr(cell_val)}",
                        "error_reason": str(e),
                        "source": "user_sheet",
                        "timestamp": fetched_at
                    })

        return valid_records, error_records

    def fetch_from_google_sheet(
        self, doc_id: str, gid: str = "1029885527", timeout: int = 20
    ) -> Tuple[List[Dict], List[Dict]]:
        """Tải trực tiếp từ Google Sheet Export URL."""
        url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"
        req = urllib.request.Request(url, headers={"User-Agent": "Bingo18Analytics/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            csv_text = res.read().decode("utf-8")
        return self.parse_csv_content(csv_text, fetched_at=datetime.now().isoformat())
