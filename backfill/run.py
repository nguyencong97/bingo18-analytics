"""Chạy nạp và đối chiếu lịch sử dữ liệu."""

from pathlib import Path
import json
import sys

from backfill.reconcile import BackfillReconciler

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    data_dir = Path(__file__).resolve().parent.parent / "data"
    reconciler = BackfillReconciler(data_dir=data_dir)
    report = reconciler.run_reconciliation()
    print("\n" + "="*50)
    print("BÁO CÁO NẠP VÀ ĐỐI CHIẾU LỊCH SỬ (BACKFILL REPORT)")
    print("="*50)
    print(json.dumps(report, indent=2, ensure_ascii=False))
