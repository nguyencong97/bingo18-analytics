"""Kiểm thử cho RegimeDetector."""

import pytest
from backfill.regime_detector import RegimeDetector


def test_detect_regimes_transition():
    """Kiểm tra phát hiện chuyển đổi từ 96 kỳ/ngày (10 phút) sang 159 kỳ/ngày (6 phút)."""
    detector = RegimeDetector(shift_threshold_pct=20.0, min_sustained_days=7)

    # Giả lập 20 ngày 96 kỳ/ngày và 20 ngày 159 kỳ/ngày
    daily_counts = {}
    for day in range(1, 21):
        daily_counts[f"2024-01-{day:02d}"] = 96
    for day in range(1, 21):
        daily_counts[f"2024-02-{day:02d}"] = 159

    regimes = detector.detect_regimes_from_daily_counts(daily_counts)
    assert len(regimes) == 2

    # Regime 1: ~10 phút
    assert regimes[0]["approx_draws_per_day"] == 96
    assert abs(regimes[0]["approx_interval_minutes"] - 10.0) < 0.2

    # Regime 2: ~6 phút
    assert regimes[1]["approx_draws_per_day"] == 159
    assert abs(regimes[1]["approx_interval_minutes"] - 6.0) < 0.2
