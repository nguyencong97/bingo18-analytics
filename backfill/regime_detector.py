"""Thuật toán phát hiện thay đổi chu kỳ quay (Regime Detection).

Quy tắc:
1. KHÔNG hardcode. Phát hiện chu kỳ từ dữ liệu.
2. median(Δt giữa kỳ liên tiếp) theo tuần.
3. Tách 'regime' khi median đổi quá 20% bền vững >= 7 ngày.
4. Mọi phân tích theo giờ/slot chạy riêng từng regime.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics


class RegimeDetector:
    """Bộ phát hiện và phân đoạn chu kỳ quay."""

    def __init__(self, shift_threshold_pct: float = 20.0, min_sustained_days: int = 7):
        self.shift_threshold_pct = shift_threshold_pct
        self.min_sustained_days = min_sustained_days

    def detect_regimes_from_daily_counts(
        self, daily_draw_counts: Dict[str, int]
    ) -> List[Dict]:
        """Phát hiện regime dựa trên số lượng kỳ trong các ngày đầy đủ.

        Ví dụ: ~96 kỳ/ngày (chu kỳ 10 phút) -> ~159 kỳ/ngày (chu kỳ 6 phút).
        daily_draw_counts: { "YYYY-MM-DD": count, ... } đã được sắp xếp theo ngày.
        """
        sorted_dates = sorted(daily_draw_counts.keys())
        if not sorted_dates:
            return []

        # Ước lượng khoảng cách phút trung bình mỗi ngày:
        # Giờ hoạt động ~ 06:00 đến 21:54 = 954 phút
        daily_intervals: Dict[str, float] = {}
        for d in sorted_dates:
            count = daily_draw_counts[d]
            if count >= 30:  # Chỉ tính ngày có số kỳ hợp lý
                daily_intervals[d] = 954.0 / max(1, count - 1)

        # Tính median trượt theo tuần (7 ngày)
        rolling_medians: List[Dict] = []
        for i in range(len(sorted_dates)):
            window = [
                daily_intervals[d]
                for d in sorted_dates[max(0, i - 6) : i + 1]
                if d in daily_intervals
            ]
            if window:
                med = statistics.median(window)
                rolling_medians.append({"date": sorted_dates[i], "median_dt": med})

        if not rolling_medians:
            return []

        regimes: List[Dict] = []
        current_regime_start = rolling_medians[0]["date"]
        baseline_dt = rolling_medians[0]["median_dt"]
        regime_index = 1

        sustained_shift_count = 0
        potential_new_dt = baseline_dt
        potential_shift_date = None

        for item in rolling_medians[1:]:
            cur_dt = item["median_dt"]
            diff_pct = abs(cur_dt - baseline_dt) / baseline_dt * 100.0

            if diff_pct > self.shift_threshold_pct:
                if sustained_shift_count == 0:
                    potential_shift_date = item["date"]
                    potential_new_dt = cur_dt
                sustained_shift_count += 1

                if sustained_shift_count >= self.min_sustained_days:
                    # Đã duy trì đủ >= 7 ngày -> Chốt regime cũ và mở regime mới
                    regimes.append({
                        "regime_id": f"regime_{regime_index}",
                        "start_date": current_regime_start,
                        "end_date": potential_shift_date,
                        "approx_interval_minutes": round(baseline_dt, 1),
                        "approx_draws_per_day": round(954.0 / baseline_dt) + 1
                    })
                    regime_index += 1
                    current_regime_start = potential_shift_date
                    baseline_dt = potential_new_dt
                    sustained_shift_count = 0
                    potential_shift_date = None
            else:
                sustained_shift_count = 0
                potential_shift_date = None

        # Đóng regime cuối cùng
        regimes.append({
            "regime_id": f"regime_{regime_index}",
            "start_date": current_regime_start,
            "end_date": sorted_dates[-1],
            "approx_interval_minutes": round(baseline_dt, 1),
            "approx_draws_per_day": round(954.0 / baseline_dt) + 1
        })

        return regimes
