"""Kiểm thử cho các mô-đun M4-M7 và M9-M13."""

import numpy as np
import pytest

from stats.m4_m7_advanced import (
    compute_dice_pair_independence,
    compute_markov_transition_matrix,
    compute_autocorrelation_and_runs,
    compute_return_gaps
)
from stats.m9_m13_analysis import (
    apply_benjamini_hochberg,
    compute_time_and_day_independence,
    compute_spectral_and_entropy,
    compute_cusum_drift,
    compute_bayesian_dirichlet
)


def test_benjamini_hochberg_correction():
    """Kiểm tra thuật toán FDR Benjamini-Hochberg."""
    # 4 giả thuyết: raw_p = [0.01, 0.04, 0.03, 0.20]
    raw_p = [0.01, 0.04, 0.03, 0.20]
    res = apply_benjamini_hochberg(raw_p, alpha=0.05)
    assert len(res) == 4
    # rank 1: 0.01 * 4 / 1 = 0.04 < 0.05 -> significant
    assert res[0]["raw_p"] == 0.01
    assert res[0]["adj_p"] <= 0.05
    assert res[0]["is_significant"] is True
    # rank 4: 0.20 * 4 / 4 = 0.20 > 0.05 -> not significant
    assert res[3]["raw_p"] == 0.20
    assert res[3]["is_significant"] is False


def test_dice_pair_independence_on_fair_sample():
    """Xúc xắc ngẫu nhiên công bằng phải độc lập giữa các cặp."""
    np.random.seed(42)
    d1 = np.random.randint(1, 7, size=3600)
    d2 = np.random.randint(1, 7, size=3600)
    d3 = np.random.randint(1, 7, size=3600)
    draws = list(zip(d1, d2, d3))

    res = compute_dice_pair_independence(draws)
    assert "d1_d2" in res
    assert "d1_d3" in res
    assert "d2_d3" in res
    for pair in res.values():
        assert pair["df"] == 25
        assert pair["p_value"] > 0.01


def test_shannon_entropy():
    """Kiểm tra Shannon entropy tiệm cận giá trị lý thuyết ~3.598 bits."""
    np.random.seed(42)
    d1 = np.random.randint(1, 7, size=20000)
    d2 = np.random.randint(1, 7, size=20000)
    d3 = np.random.randint(1, 7, size=20000)
    sums = (d1 + d2 + d3).tolist()

    res = compute_spectral_and_entropy(sums)
    assert abs(res["actual_entropy_bits"] - 3.598) < 0.05
    assert res["is_entropy_close"] is True


def test_bayesian_dirichlet_credible_interval():
    """Khoảng tin cậy hậu nghiệm 95% Dirichlet phải bao phủ xác suất lý thuyết."""
    np.random.seed(42)
    d1 = np.random.randint(1, 7, size=10000)
    d2 = np.random.randint(1, 7, size=10000)
    d3 = np.random.randint(1, 7, size=10000)
    sums = (d1 + d2 + d3).tolist()

    res = compute_bayesian_dirichlet(sums)
    # Với 16 tổng ở mức tin cậy 95%, kỳ vọng ít nhất 14/16 tổng nằm trong dải
    covered = sum(
        1 for item in res["bayesian_sums"].values()
        if item["theoretical_in_credible_interval"]
    )
    assert covered >= 14
