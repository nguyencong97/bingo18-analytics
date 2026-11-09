"""Chạy 1000 bộ mô phỏng null đối chứng và xuất kết quả."""

import json
from pathlib import Path
import sys

from sim.null_generator import NullSimulationEngine

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    results_dir = Path(__file__).resolve().parent.parent / "results"
    stats_file = results_dir / "all_stats_real.json"

    real_chi2 = 7.9668
    real_n = 99561
    if stats_file.exists():
        with open(stats_file, "r", encoding="utf-8") as f:
            stats_data = json.load(f)
            real_chi2 = stats_data["m3_chi2_tests"]["sums_df15"]["chi2"]
            real_n = stats_data["metadata"]["total_draws"]

    print(f"Bắt đầu chạy 1,000 mô phỏng đối chứng (seed=20261109, n={real_n}, real_chi2={real_chi2})...")
    engine = NullSimulationEngine(seed=20261109)
    result = engine.run_monte_carlo_null_distribution(
        real_n=real_n, real_chi2_sum=real_chi2, num_simulations=1000
    )

    out_file = results_dir / "m14_null_simulation.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    public_file = (
        Path(__file__).resolve().parent.parent
        / "web"
        / "public"
        / "results"
        / "m14_null_simulation.json"
    )
    with open(public_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Đã lưu kết quả mô phỏng vào {out_file} và {public_file}")
    print(f"Empirical p-value: {result['empirical_p_value']}")
    print(f"Extreme count (sim >= real): {result['extreme_count']} / 1000")
