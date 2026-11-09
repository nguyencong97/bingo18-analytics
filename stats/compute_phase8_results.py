"""Tính toán M15 EV và M16 Backtest mô hình dự báo."""

import csv
import json
from pathlib import Path
import sys

from stats.m15_ev_calculator import compute_expected_values
from stats.m16_predictive_models import PredictiveBacktester


def run_phase8_compute():
    results_dir = Path(__file__).resolve().parent.parent / "results"
    public_results_dir = Path(__file__).resolve().parent.parent / "web" / "public" / "results"
    data_dir = Path(__file__).resolve().parent.parent / "data"
    all_csv = data_dir / "all.csv"

    # 1. Tính toán M15 EV
    print("Đang tính toán M15 EV & RTP...")
    ev_data = compute_expected_values()
    ev_file = results_dir / "m15_ev.json"
    with open(ev_file, "w", encoding="utf-8") as f:
        json.dump(ev_data, f, indent=2, ensure_ascii=False)
    with open(public_results_dir / "m15_ev.json", "w", encoding="utf-8") as f:
        json.dump(ev_data, f, indent=2, ensure_ascii=False)
    print(f"Đã lưu EV vào: {ev_file}")

    # 2. Tính toán M16 Walk-Forward Backtest
    sums = []
    with open(all_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            sums.append(int(r["total"]))

    print(f"Đang chạy Walk-Forward Backtest (test 5,000 kỳ gần nhất)...")
    backtester = PredictiveBacktester(sums, window_size=500)
    backtest_res = backtester.run_backtest(test_steps=5000)

    bt_file = results_dir / "m16_backtest.json"
    with open(bt_file, "w", encoding="utf-8") as f:
        json.dump(backtest_res, f, indent=2, ensure_ascii=False)
    with open(public_results_dir / "m16_backtest.json", "w", encoding="utf-8") as f:
        json.dump(backtest_res, f, indent=2, ensure_ascii=False)

    print(f"Đã lưu kết quả Backtest vào: {bt_file}")
    print("\n--- KẾT QUẢ SO SÁNH MÔ HÌNH VỚI BASELINE (DIEBOLD-MARIANO) ---")
    for m_name, m_info in backtest_res["models"].items():
        print(f"[{m_name}] Mean Log-Loss: {m_info['mean_log_loss']}, Brier: {m_info['mean_brier_score']}, Top3: {m_info['top3_hit_rate']}% | DM p-val: {m_info['diebold_mariano_p_value']}")
    print(f"\n>> {backtest_res['conclusion']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run_phase8_compute()
