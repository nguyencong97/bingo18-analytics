"""Quản lý lưu trữ tệp phẳng CSV append-only, snapshot thô và chuỗi checksum SHA-256."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

from backfill.reconcile import CSV_HEADER, update_checksums

logger = logging.getLogger(__name__)


class DataStorage:
    """Quản lý lưu trữ dữ liệu Bingo18 tuân thủ nguyên tắc chỉ-thêm (append-only)."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.raw_dir = data_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.all_csv = data_dir / "all.csv"
        self.errors_csv = data_dir / "errors.csv"
        self.gaps_csv = data_dir / "gaps.csv"
        self._existing_ids: Set[str] = self._load_existing_draw_ids()

    def _load_existing_draw_ids(self) -> Set[str]:
        """Tải tập hợp các draw_id đã tồn tại để chống ghi trùng (dedupe)."""
        ids = set()
        if self.all_csv.exists() and self.all_csv.stat().st_size > 0:
            with open(self.all_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    draw_id = row.get("draw_id")
                    if draw_id:
                        ids.add(draw_id)
        return ids

    def save_raw_snapshot(
        self, raw_content: str, date_iso: str, draw_id: str, fetched_at: str
    ) -> Path:
        """Lưu snapshot thô nguyên bản vào data/raw/YYYY/MM/DD/<draw_id>_<fetched_at>.json."""
        dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        year_str = f"{dt.year:04d}"
        month_str = f"{dt.month:02d}"
        day_str = f"{dt.day:02d}"

        target_dir = self.raw_dir / year_str / month_str / day_str
        target_dir.mkdir(parents=True, exist_ok=True)

        clean_ts = fetched_at.replace(":", "-").replace(".", "-")
        snapshot_file = target_dir / f"{draw_id}_{clean_ts}.json"
        with open(snapshot_file, "w", encoding="utf-8") as f:
            f.write(raw_content)
        return snapshot_file

    def append_new_draws(
        self, valid_records: List[Dict], error_records: List[Dict]
    ) -> Tuple[int, List[str]]:
        """Ghi nhận các kỳ quay mới chưa từng xuất hiện.

        Đảm bảo append-only, cập nhật all.csv và tính lại checksum.
        Trả về (số kỳ mới, danh sách mã kỳ mới).
        """
        # 1. Ghi nhận lỗi nếu có
        if error_records:
            file_exists = self.errors_csv.exists() and self.errors_csv.stat().st_size > 0
            with open(self.errors_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["draw_id", "raw_row", "error_reason", "source", "timestamp"]
                )
                if not file_exists:
                    writer.writeheader()
                for err in error_records:
                    writer.writerow(err)

        # 2. Lọc bỏ các kỳ đã tồn tại
        new_records = [
            r for r in valid_records if r["draw_id"] not in self._existing_ids
        ]
        if not new_records:
            return 0, []

        # Sắp xếp các kỳ mới theo ID tăng dần
        new_records.sort(key=lambda x: int(x["draw_id"]))

        # 3. Ghi vào các tệp tháng tương ứng
        by_month: Dict[str, List[Dict]] = {}
        for r in new_records:
            ym = r["date"][:7]
            by_month.setdefault(ym, []).append(r)

        for ym, recs in by_month.items():
            mfile = self.data_dir / f"{ym}.csv"
            file_exists = mfile.exists() and mfile.stat().st_size > 0
            with open(mfile, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
                if not file_exists:
                    writer.writeheader()
                for r in recs:
                    writer.writerow(r)

        # 4. Cập nhật data/all.csv
        # Đọc tất cả các kỳ cũ và gộp với kỳ mới, sau đó sắp xếp theo ID
        all_records: List[Dict] = []
        if self.all_csv.exists() and self.all_csv.stat().st_size > 0:
            with open(self.all_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                all_records.extend(reader)

        all_records.extend(new_records)
        all_records.sort(key=lambda x: int(x["draw_id"]))

        temp_all = self.all_csv.with_suffix(".tmp")
        with open(temp_all, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            for r in all_records:
                writer.writerow(r)
        temp_all.replace(self.all_csv)

        # 4b. Tự động đồng bộ data/sheet_initial_import.csv chuẩn 9 cột
        sheet_csv = self.data_dir / "sheet_initial_import.csv"
        sheet_headers = ["Mã kỳ", "Ngày quay", "Giờ", "Slot", "Xúc xắc 1", "Xúc xắc 2", "Xúc xắc 3", "Tổng", "Bộ số"]
        temp_sheet = sheet_csv.with_suffix(".tmp")
        with open(temp_sheet, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(sheet_headers)
            for r in all_records:
                d_id = r["draw_id"].replace("#", "").strip().zfill(7)
                num_id = int(d_id)
                d_date = r["date"]
                slot = int(r.get("slot_in_day") or 0)
                if not slot or slot < 1:
                    slot = ((num_id - 195421) % 159 + 1)
                if slot < 1: slot = 1
                if slot > 159: slot = 159

                tot_min = 6 * 60 + slot * 6
                hh = tot_min // 60
                mm = tot_min % 60
                d_time = f"{hh:02d}:{mm:02d}"

                d1 = int(r["d1"])
                d2 = int(r["d2"])
                d3 = int(r["d3"])
                tot = int(r["total"])
                res = r.get("result") or f"{d1} {d2} {d3} {tot}"
                writer.writerow([d_id, d_date, d_time, slot, d1, d2, d3, tot, res])
        temp_sheet.replace(sheet_csv)

        # Cập nhật cache ID
        for r in new_records:
            self._existing_ids.add(r["draw_id"])

        # 5. Cập nhật chuỗi SHA-256 kế thừa
        monthly_files = list(self.data_dir.glob("????-??.csv"))
        update_checksums(self.data_dir, monthly_files)

        new_ids = [r["draw_id"] for r in new_records]
        return len(new_records), new_ids
