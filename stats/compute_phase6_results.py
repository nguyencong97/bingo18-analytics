"""Tính toán toàn bộ kiểm định thống kê M1-M13 trên dữ liệu thật và xuất ra results/."""

import csv
from datetime import datetime
import json
from pathlib import Path
import sys

from backfill.reconcile import compute_file_sha256
from stats.m1_m3_distributions import (
    compute_sum_distribution,
    compute_chisquare_sums,
    compute_dice_goodness_of_fit,
    compute_ordered_combinations_chisquare,
    compute_unordered_combinations_chisquare,
)
from stats.m4_m7_advanced import (
    compute_dice_pair_independence,
    compute_markov_transition_matrix,
    compute_autocorrelation_and_runs,
    compute_return_gaps,
)
from stats.m8_date_distributions import compute_date_sum_matrix
from stats.m9_m13_analysis import (
    apply_benjamini_hochberg,
    compute_time_and_day_independence,
    compute_spectral_and_entropy,
    compute_cusum_drift,
    compute_bayesian_dirichlet,
)


def compute_all_stats():
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
    print(f"Đang tính toán toàn bộ thống kê M1-M13 trên n={n:,} kỳ quay thật...")

    # M1 - M3
    dist_res = compute_sum_distribution(sums)
    chi2_sums = compute_chisquare_sums(sums)
    chi2_dice = compute_dice_goodness_of_fit(all_dice)
    chi2_ordered = compute_ordered_combinations_chisquare(draw_tuples)
    chi2_unordered = compute_unordered_combinations_chisquare(draw_tuples)

    # M4 - M7
    dice_pairs = compute_dice_pair_independence(draw_tuples)
    markov_res = compute_markov_transition_matrix(sums)
    acf_runs = compute_autocorrelation_and_runs(sums)
    return_gaps = compute_return_gaps(sums)

    # M8
    m8_res = compute_date_sum_matrix(records)

    # M9 - M13
    time_day_res = compute_time_and_day_independence(records)
    spectral_entropy = compute_spectral_and_entropy(sums)
    cusum_res = compute_cusum_drift(sums)
    bayes_res = compute_bayesian_dirichlet(sums)

    # M10: Tổng hợp các p-value chính để hiệu chỉnh Benjamini-Hochberg (FDR)
    p_values_family = [
        chi2_sums["p_value"],
        chi2_dice["p_value"],
        chi2_ordered["p_value"],
        chi2_unordered["p_value"],
        dice_pairs["d1_d2"]["p_value"],
        dice_pairs["d1_d3"]["p_value"],
        dice_pairs["d2_d3"]["p_value"],
        markov_res["consecutive_repeat"]["p_value"],
        markov_res["independence_test_binned_df81"]["p_value"],
        acf_runs["ljung_box"]["p_value"],
        acf_runs["runs_test_big_small"]["p_value"],
        time_day_res["day_of_week_test"]["p_value"],
        time_day_res["time_slot_test"]["p_value"]
    ]
    fdr_results = apply_benjamini_hochberg(p_values_family, alpha=0.05)

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
        "m4_dice_independence": dice_pairs,
        "m5_markov": markov_res,
        "m6_autocorrelation_runs": acf_runs,
        "m7_return_gaps": return_gaps,
        "m8_date_analysis": {
            "num_days": m8_res["num_days"],
            "sum_outlier_tests": m8_res["sum_outlier_tests"],
            "total_outlier_instances": m8_res["total_outlier_instances"]
        },
        "m9_time_and_day": time_day_res,
        "m10_multiple_testing_fdr": {
            "alpha": 0.05,
            "tests_evaluated": len(fdr_results),
            "any_significant": any(t["is_significant"] for t in fdr_results),
            "results": fdr_results
        },
        "m11_spectral_entropy": spectral_entropy,
        "m12_cusum_drift": cusum_res,
        "m13_bayesian": bayes_res
    }

    out_file = results_dir / "all_stats_real.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Sao chép vào web/public/results/
    public_res = Path(__file__).resolve().parent.parent / "web" / "public" / "results" / "all_stats_real.json"
    public_res.parent.mkdir(parents=True, exist_ok=True)
    with open(public_res, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Đã lưu kết quả tính toán vào: {out_file} và {public_res}")
    print(f">> CUSUM Drift detected: {cusum_res['has_drift']}")
    print(f">> FDR Significant count: {sum(1 for t in fdr_results if t['is_significant'])} / {len(fdr_results)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    compute_all_stats()
