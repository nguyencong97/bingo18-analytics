"""Bộ kiểm tra tính toàn vẹn dữ liệu (Data Integrity Checker).

Kiểm tra:
1. Chuỗi băm SHA-256 kế thừa trong data/checksums.txt
2. Tính đơn điệu tăng của draw_id trong all.csv
3. Ràng buộc toán học d1..d3 in [1, 6] và d1+d2+d3 == total
"""

import csv
import hashlib
import logging
from pathlib import Path
import sys

from backfill.reconcile import compute_file_sha256

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def verify_integrity(data_dir: Path) -> bool:
    """Xác thực toàn vẹn toàn bộ dữ liệu trong data/."""
    checksums_file = data_dir / "checksums.txt"
    all_csv = data_dir / "all.csv"

    if not checksums_file.exists():
        logger.error(f"Tệp kiểm tra {checksums_file} không tồn tại!")
        return False

    # 1. Kiểm tra chuỗi hash kế thừa
    cumulative_hash = "0" * 64
    with open(checksums_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            expected_cum_hash = parts[0]
            filename = parts[1]
            file_path = data_dir / filename

            if not file_path.exists():
                logger.error(f"Dòng {line_num}: Tệp {filename} được ghi trong checksums nhưng không tồn tại!")
                return False

            file_hash = compute_file_sha256(file_path)
            calculated_cum_hash = hashlib.sha256(
                f"{cumulative_hash}:{file_hash}".encode("utf-8")
            ).hexdigest()

            if calculated_cum_hash != expected_cum_hash:
                logger.error(
                    f"Dòng {line_num}: Chuỗi băm SHA-256 bị sai lệch trên tệp {filename}!\n"
                    f"  Kỳ vọng: {expected_cum_hash}\n"
                    f"  Thực tế: {calculated_cum_hash}"
                )
                return False

            cumulative_hash = calculated_cum_hash

    logger.info("Xác thực chuỗi SHA-256 kế thừa: HỢP LỆ (100% OK)")

    # 2. Kiểm tra tính đơn điệu và ràng buộc toán học trong all.csv
    if all_csv.exists() and all_csv.stat().st_size > 0:
        prev_id = -1
        with open(all_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r_idx, row in enumerate(reader, start=2):
                draw_id = int(row["draw_id"])
                if draw_id <= prev_id:
                    logger.error(f"Dòng {r_idx} trong all.csv: draw_id {draw_id} không đơn điệu tăng (trước đó: {prev_id})!")
                    return False
                prev_id = draw_id

                d1, d2, d3 = int(row["d1"]), int(row["d2"]), int(row["d3"])
                total = int(row["total"])

                if not (1 <= d1 <= 6 and 1 <= d2 <= 6 and 1 <= d3 <= 6):
                    logger.error(f"Dòng {r_idx} trong all.csv: Xúc xắc ({d1},{d2},{d3}) ngoài [1, 6]!")
                    return False

                if d1 + d2 + d3 != total:
                    logger.error(f"Dòng {r_idx} trong all.csv: Tổng {total} != {d1}+{d2}+{d3}!")
                    return False

        logger.info(f"Xác thực toàn vẹn all.csv ({prev_id} kỳ): HỢP LỆ (100% OK)")

    return True


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    data_dir = Path(__file__).resolve().parent.parent / "data"
    is_valid = verify_integrity(data_dir)
    if not is_valid:
        sys.exit(1)
    print("DỮ LIỆU TOÀN VẸN: PASSED")
