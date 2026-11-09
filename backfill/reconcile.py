"""Mô-đun đối chiếu (reconcile) giữa bảng tính người dùng và kho dữ liệu vietvudanh."""

import csv
import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backfill.regime_detector import RegimeDetector
from backfill.user_sheet_parser import UserSheetParser
from backfill.vietvudanh_loader import normalize_vietvudanh_record, stream_vietvudanh_records

logger = logging.getLogger(__name__)

CSV_HEADER = [
    "draw_id", "draw_datetime", "date", "time", "slot_in_day",
    "d1", "d2", "d3", "total", "result", "source", "snapshot_id",
    "fetched_at", "status"
]


def compute_file_sha256(file_path: Path) -> str:
    """Tính mã băm SHA-256 của tệp tin (chuẩn hóa LF để độc lập nền tảng Windows/Linux)."""
    with open(file_path, "rb") as f:
        content = f.read()
    normalized = content.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def update_checksums(data_dir: Path, monthly_files: List[Path]) -> None:
    """Cập nhật data/checksums.txt theo cơ chế chuỗi kế thừa SHA-256."""
    checksums_file = data_dir / "checksums.txt"
    lines = ["# Format: <cumulative_sha256>  <filename>  <timestamp_iso>\n"]
    cumulative_hash = "0" * 64

    for mfile in sorted(monthly_files):
        if not mfile.exists() or mfile.stat().st_size == 0:
            continue
        file_hash = compute_file_sha256(mfile)
        # Nối chuỗi hash kế thừa: SHA-256(cumulative + file_hash)
        combined = hashlib.sha256(f"{cumulative_hash}:{file_hash}".encode("utf-8")).hexdigest()
        cumulative_hash = combined
        timestamp = datetime.now().isoformat()
        lines.append(f"{cumulative_hash}  {mfile.name}  {timestamp}\n")

    with open(checksums_file, "w", encoding="utf-8") as f:
        f.writelines(lines)


class BackfillReconciler:
    """Quản lý nạp lịch sử, đối chiếu chéo và tổng hợp dữ liệu."""

    def __init__(self, data_dir: Path, config_path: Optional[Path] = None):
        self.data_dir = data_dir
        self.config_path = config_path or (data_dir.parent / "config" / "settings.json")
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def run_reconciliation(self, max_gh_records: Optional[int] = None) -> Dict:
        """Thực hiện toàn bộ quy trình đối chiếu và trả về báo cáo tổng kết."""
        print(">>> [1/5] Tải dữ liệu từ kho GitHub vietvudanh...")
        gh_draws: Dict[str, Dict] = {}  # draw_id -> record
        gh_by_date: Dict[str, List[Dict]] = defaultdict(list)
        count = 0

        for raw in stream_vietvudanh_records():
            norm = normalize_vietvudanh_record(raw)
            if norm:
                gh_draws[norm["draw_id"]] = norm
                gh_by_date[norm["date"]].append(norm)
                count += 1
                if max_gh_records and count >= max_gh_records:
                    break

        print(f"    Đã nạp {len(gh_draws):,} kỳ hợp lệ từ kho GitHub.")

        print(">>> [2/5] Tải và phân tích sheet 'Chi tiết' của người dùng...")
        sheet_cfg = self.settings.get("google_sheet", {})
        doc_id = sheet_cfg.get("doc_id", "1-A-ssc7nxooZMDjYrz8v-EBsjUex24g18TjOjVDFyL0")
        parser = UserSheetParser(default_year=2026)
        user_valid, user_errors = parser.fetch_from_google_sheet(doc_id)
        print(f"    Sheet người dùng: {len(user_valid)} bản ghi hợp lệ, {len(user_errors)} lỗi định dạng.")

        # Ghi các bản ghi lỗi vào data/errors.csv
        errors_file = self.data_dir / "errors.csv"
        if user_errors:
            with open(errors_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["draw_id", "raw_row", "error_reason", "source", "timestamp"])
                for err in user_errors:
                    writer.writerow(err)

        print(">>> [3/5] Đối chiếu từng kỳ giữa Sheet và GitHub...")
        discrepancies: List[Dict] = []
        # Nhóm user_valid theo (date, slot_in_day)
        user_by_date_slot: Dict[Tuple[str, int], Dict] = {}
        for r in user_valid:
            user_by_date_slot[(r["date"], r["slot_in_day"])] = r

        # Đối chiếu: trên các ngày người dùng có số liệu, kiểm tra khớp
        reconciled_user_draws = 0
        for date_str, draws in gh_by_date.items():
            # Sắp xếp các kỳ trong ngày theo draw_id tăng dần để gán slot_in_day
            sorted_draws = sorted(draws, key=lambda x: int(x["draw_id"]))
            for slot_idx, gh_rec in enumerate(sorted_draws, start=1):
                gh_rec["slot_in_day"] = slot_idx
                # Thời gian quay ước tính: 06:05 + (slot_idx - 1) * 6 phút
                start_minute = 6 * 60 + 5 + (slot_idx - 1) * 6
                h, m = divmod(start_minute, 60)
                gh_rec["time"] = f"{h:02d}:{m:02d}"
                gh_rec["draw_datetime"] = f"{date_str}T{gh_rec['time']}:00+07:00"

                # Đối chiếu với user sheet nếu có
                user_rec = user_by_date_slot.get((date_str, slot_idx))
                if user_rec:
                    # So sánh kết quả
                    if gh_rec["result"] != user_rec["result"]:
                        disc = {
                            "draw_id": gh_rec["draw_id"],
                            "date": date_str,
                            "source_a": "user_sheet",
                            "result_a": user_rec["result"],
                            "source_b": "vietvudanh_github",
                            "result_b": gh_rec["result"],
                            "recorded_at": datetime.now().isoformat(),
                            "status": "unconfirmed_conflict"
                        }
                        discrepancies.append(disc)
                    else:
                        reconciled_user_draws += 1
                        user_rec["draw_id"] = gh_rec["draw_id"]

        print(f"    Số kỳ trùng khớp hoàn toàn giữa 2 nguồn: {reconciled_user_draws}")
        print(f"    Số kỳ sai lệch (discrepancies): {len(discrepancies)}")

        # Ghi discrepancies vào data/discrepancies.csv
        disc_file = self.data_dir / "discrepancies.csv"
        if discrepancies:
            with open(disc_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "draw_id", "date", "source_a", "result_a", "source_b", "result_b", "recorded_at", "status"
                ])
                for d in discrepancies:
                    writer.writerow(d)

        print(">>> [4/5] Phát hiện kỳ thiếu (gaps) trong dãy ID...")
        all_draw_ids = sorted([int(k) for k in gh_draws.keys()])
        gaps: List[Dict] = []
        if all_draw_ids:
            for i in range(len(all_draw_ids) - 1):
                diff = all_draw_ids[i + 1] - all_draw_ids[i]
                if diff > 1:
                    gaps.append({
                        "draw_id_from": f"{all_draw_ids[i]:07d}",
                        "draw_id_to": f"{all_draw_ids[i+1]:07d}",
                        "detected_at": datetime.now().isoformat(),
                        "status": "missing"
                    })

        print(f"    Phát hiện {len(gaps)} khoảng kỳ thiếu.")
        gaps_file = self.data_dir / "gaps.csv"
        if gaps:
            with open(gaps_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["draw_id_from", "draw_id_to", "detected_at", "status"])
                writer.writeheader()
                for g in gaps:
                    writer.writerow(g)

        print(">>> [5/5] Ghi dữ liệu chuẩn hóa theo tháng và phát hiện Regime...")
        # Nhóm theo YYYY-MM
        by_month: Dict[str, List[Dict]] = defaultdict(list)
        daily_counts: Dict[str, int] = defaultdict(int)

        for rec in gh_draws.values():
            ym = rec["date"][:7]
            by_month[ym].append(rec)
            daily_counts[rec["date"]] += 1

        monthly_files: List[Path] = []
        all_records_sorted = sorted(gh_draws.values(), key=lambda x: int(x["draw_id"]))

        # Ghi các tệp tháng
        for ym, recs in by_month.items():
            mfile = self.data_dir / f"{ym}.csv"
            monthly_files.append(mfile)
            recs_sorted = sorted(recs, key=lambda x: int(x["draw_id"]))
            with open(mfile, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
                writer.writeheader()
                for r in recs_sorted:
                    writer.writerow(r)

        # Ghi data/all.csv
        all_csv = self.data_dir / "all.csv"
        with open(all_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            for r in all_records_sorted:
                writer.writerow(r)

        # Cập nhật checksums SHA-256
        update_checksums(self.data_dir, monthly_files)

        # Phát hiện Regime
        regime_detector = RegimeDetector()
        regimes = regime_detector.detect_regimes_from_daily_counts(daily_counts)

        report = {
            "total_draws": len(gh_draws),
            "date_range": {
                "start": all_records_sorted[0]["date"] if all_records_sorted else "",
                "end": all_records_sorted[-1]["date"] if all_records_sorted else ""
            },
            "user_sheet_matches": reconciled_user_draws,
            "discrepancies_count": len(discrepancies),
            "gaps_count": len(gaps),
            "monthly_files_created": len(monthly_files),
            "regimes": regimes
        }
        return report
