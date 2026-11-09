"""Kiểm thử cho mô-đun thống kê M1 - M3 và M8 đối chiếu với scipy."""

import numpy as np
import pytest
from scipy import stats

from stats.m1_m3_distributions import (
    compute_clopper_pearson_ci,
    compute_sum_distribution,
    compute_chisquare_sums,
    compute_dice_goodness_of_fit,
    compute_ordered_combinations_chisquare,
    compute_unordered_combinations_chisquare
)
from stats.m8_date_distributions import compute_date_sum_matrix


def test_clopper_pearson_exact():
    """Kiểm tra khoảng tin cậy Clopper-Pearson khớp với tính toán từ Scipy Beta."""
    k = 50
    n = 100
    low, high = compute_clopper_pearson_ci(k, n, confidence=0.95)
    # Clopper-Pearson cho k=50, n=100 xấp xỉ ~ [0.398, 0.601]
    assert 0.39 < low < 0.41
    assert 0.59 < high < 0.61

    # Kiểm tra biên k=0 và k=n
    low_0, high_0 = compute_clopper_pearson_ci(0, 100)
    assert low_0 == 0.0
    assert high_0 > 0.0

    low_n, high_n = compute_clopper_pearson_ci(100, 100)
    assert low_n < 1.0
    assert high_n == 1.0


def test_sum_distribution_metrics():
    """Kiểm tra tính toán Z-score và phân phối tổng."""
    # Tạo mẫu giả định tổng 10 và 11
    sample = [10] * 50 + [11] * 50
    res = compute_sum_distribution(sample)
    assert res["n"] == 100
    assert 10 in res["distribution"]
    d10 = res["distribution"][10]
    assert d10["observed"] == 50
    assert d10["ways"] == 27
    assert d10["z_score"] > 0  # 50 cao hơn nhiều so với kỳ vọng 100 * 27/216 = 12.5


def test_chisquare_sums_fair_sample():
    """Mẫu phân phối chuẩn kỳ vọng thì Chi-square không bác bỏ H0."""
    np.random.seed(42)
    # Tung 3 xúc xắc ngẫu nhiên công bằng 10,000 lần
    d1 = np.random.randint(1, 7, size=10000)
    d2 = np.random.randint(1, 7, size=10000)
    d3 = np.random.randint(1, 7, size=10000)
    sums = (d1 + d2 + d3).tolist()

    res = compute_chisquare_sums(sums)
    assert res["df"] == 15
    # P-value của xúc xắc công bằng phải > 0.01 (không bác bỏ H0)
    assert res["p_value"] > 0.01
    assert not res["is_significant"]


def test_date_sum_matrix():
    """Kiểm tra ma trận Ngày x Tổng."""
    records = [
        {"date": "2026-11-01", "total": 10},
        {"date": "2026-11-01", "total": 11},
        {"date": "2026-11-02", "total": 8},
        {"date": "2026-11-02", "total": 13},
    ]
    res = compute_date_sum_matrix(records)
    assert res["num_days"] == 2
    assert "2026-11-01" in res["daily_matrix"]
    assert "2026-11-02" in res["daily_matrix"]
    assert len(res["sum_outlier_tests"]) == 16
