"""Tính toán thống kê M1-M3 và M8 trên toàn bộ dữ liệu thật và lưu vào results/."""

import csv
import json
from pathlib import Path
from datetime import datetime
import sys

from backfill.reconcile import compute_file_sha256
from stats.m1_m3_distributions import (
    compute_sum_distribution,
    compute_chisquare_sums,
    compute_dice_goodness_of_fit,
    compute_ordered_combinations_chisquare,
    compute_unordered_combinations_chisquare
)
from stats.m8_date_distributions import compute_date_sum_matrix


def run_compute():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    results_dir = Path(__file__).resolve().parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    all_csv = data_dir / "all.csv"

    if not all_csv.exists():
        print("all.csv không tồn tại.")
        return

    data_hash = compute_file_sha256(all_csv)

    records = []
    sums = []
    all_dice = []
    draw_tuples = []

    with open(all_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d1, d2, d3 = int(row["d1"]), int(row["d2"]), int(row["d3"])
            total = int(row["total"])
            records.append(row)
            sums.append(total)
            all_dice.extend([d1, d2, d3])
            draw_tuples.append((d1, d2, d3))

    n = len(records)
    print(f"Đang tính toán thống kê M1-M3, M8 trên n={n:,} kỳ quay thật...")

    dist_res = compute_sum_distribution(sums)
    chi2_sums = compute_chisquare_sums(sums)
    chi2_dice = compute_dice_goodness_of_fit(all_dice)
    chi2_ordered = compute_ordered_combinations_chisquare(draw_tuples)
    chi2_unordered = compute_unordered_combinations_chisquare(draw_tuples)
    m8_res = compute_date_sum_matrix(records)

    payload = {
        "metadata": {
            "data_hash": data_hash,
            "total_draws": n,
            "version": "1.0.0",
            "seed": 20261109,
            "computed_at": datetime.now().isoformat()
        },
        "m1_m2_distribution": dist_res,
        "m3_chi2_tests": {
            "sums_df15": chi2_sums,
            "dice_df5": chi2_dice,
            "ordered_216_df215": chi2_ordered,
            "unordered_56_df55": chi2_unordered
        },
        "m8_date_analysis": {
            "num_days": m8_res["num_days"],
            "sum_outlier_tests": m8_res["sum_outlier_tests"],
            "total_outlier_instances": m8_res["total_outlier_instances"]
        }
    }

    out_file = results_dir / "m1_m3_m8_real.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Đã lưu kết quả tính toán vào: {out_file}")
    print("\n--- TÓM TẮT KIỂM ĐỊNH H0 (MÁY QUAY CÔNG BẰNG) ---")
    print(f"1. Tổng 3..18 (df=15): Chi2 = {chi2_sums['chi2']}, p-value = {chi2_sums['p_value']:.4f}")
    print(f"2. Từng viên 1..6 (df=5): Chi2 = {chi2_dice['chi2']}, p-value = {chi2_dice['p_value']:.4f}")
    print(f"3. 216 tổ hợp (df=215): Chi2 = {chi2_ordered['chi2']}, p-value = {chi2_ordered['p_value']:.4f}")
    print(f"4. 56 tổ hợp (df=55): Chi2 = {chi2_unordered['chi2']}, p-value = {chi2_unordered['p_value']:.4f}")
    if chi2_sums['p_value'] >= 0.05 and chi2_dice['p_value'] >= 0.05:
        print(">> KẾT LUẬN: KHÔNG PHÁT HIỆN BẤT THƯỜNG. Máy quay hoàn toàn tuân thủ phân phối ngẫu nhiên lý thuyết.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run_compute()
