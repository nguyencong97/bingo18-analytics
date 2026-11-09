"""Kiểm thử chấp nhận các hằng số toán học lý thuyết cho Bingo18."""

import pytest
from fractions import Fraction
from scipy.stats import chi2

from stats.constants import (
    TOTAL_ORDERED_OUTCOMES,
    THEORETICAL_WAYS,
    THEORETICAL_PROB_SUM,
    P_SMALL,
    P_DRAW,
    P_BIG,
    P_ANY_TRIPLE,
    P_EXACT_ONE_PAIR,
    P_THREE_DISTINCT,
    P_NUMBER_OCCURRENCE,
    P_CONSECUTIVE_SAME_SUM,
    UNORDERED_COMBINATIONS,
    CHI2_CRITICAL_DF15_ALPHA05
)


def test_sum_ways_and_probabilities():
    """Kiểm tra tổng số cách xuất hiện w(s) và xác suất p(s)."""
    assert sum(THEORETICAL_WAYS.values()) == 216
    assert sum(THEORETICAL_PROB_SUM.values()) == Fraction(1, 1)

    # Đối xứng: p(s) == p(21 - s)
    for s in range(3, 11):
        assert THEORETICAL_WAYS[s] == THEORETICAL_WAYS[21 - s]
        assert THEORETICAL_PROB_SUM[s] == THEORETICAL_PROB_SUM[21 - s]


def test_big_small_draw_fractions():
    """Kiểm tra xác suất Lớn, Hòa, Nhỏ."""
    assert P_SMALL == Fraction(81, 216)
    assert P_DRAW == Fraction(54, 216)
    assert P_BIG == Fraction(81, 216)
    assert P_SMALL + P_DRAW + P_BIG == Fraction(1, 1)

    # Rút gọn phân số:
    # 81/216 = 3/8 = 0.375
    # 54/216 = 1/4 = 0.25
    assert P_SMALL == Fraction(3, 8)
    assert P_DRAW == Fraction(1, 4)
    assert P_BIG == Fraction(3, 8)


def test_combination_types():
    """Kiểm tra phân loại kết quả: Tam hoa, Cặp, 3 số khác nhau."""
    assert P_ANY_TRIPLE == Fraction(6, 216)
    assert P_EXACT_ONE_PAIR == Fraction(90, 216)
    assert P_THREE_DISTINCT == Fraction(120, 216)
    assert P_ANY_TRIPLE + P_EXACT_ONE_PAIR + P_THREE_DISTINCT == Fraction(1, 1)


def test_single_number_occurrences():
    """Kiểm tra phân phối số lần xuất hiện của một số cụ thể k in 0..3."""
    assert P_NUMBER_OCCURRENCE[0] == Fraction(125, 216)
    assert P_NUMBER_OCCURRENCE[1] == Fraction(75, 216)
    assert P_NUMBER_OCCURRENCE[2] == Fraction(15, 216)
    assert P_NUMBER_OCCURRENCE[3] == Fraction(1, 216)
    assert sum(P_NUMBER_OCCURRENCE.values()) == Fraction(1, 1)


def test_consecutive_same_sum_probability():
    """Kiểm tra xác suất hai kỳ liên tiếp có cùng tổng."""
    expected = Fraction(4332, 46656)
    assert P_CONSECUTIVE_SAME_SUM == expected
    # Xấp xỉ ~0.092850
    assert abs(float(P_CONSECUTIVE_SAME_SUM) - 0.09285) < 1e-4


def test_unordered_combinations_count():
    """Kiểm tra 56 tổ hợp không thứ tự."""
    assert len(UNORDERED_COMBINATIONS) == 56
    assert sum(c["permutations"] for c in UNORDERED_COMBINATIONS) == 216


def test_chi2_threshold_matches_scipy():
    """Kiểm tra ngưỡng Chi-Square 15 df tại alpha=0.05 khớp với scipy."""
    scipy_val = chi2.ppf(0.95, df=15)
    assert abs(CHI2_CRITICAL_DF15_ALPHA05 - scipy_val) < 1e-12
    # Giá trị nằm trong khoảng ~ 24.996
    assert round(scipy_val, 3) == 24.996
