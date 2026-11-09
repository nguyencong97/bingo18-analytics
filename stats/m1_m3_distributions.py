"""Mô-đun M1 - M3: Phân phối lý thuyết, Z-score, Clopper-Pearson và Chi-Square Goodness-of-Fit."""

from collections import Counter
from fractions import Fraction
import itertools
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

from stats.constants import (
    TOTAL_ORDERED_OUTCOMES,
    THEORETICAL_WAYS,
    THEORETICAL_PROB_SUM,
    UNORDERED_COMBINATIONS
)


def compute_clopper_pearson_ci(
    k: int, n: int, confidence: float = 0.95
) -> Tuple[float, float]:
    """Tính khoảng tin cậy Clopper-Pearson 95% (Exact Binomial CI).

    Sử dụng phân phối Beta theo công thức chính xác:
    Lower = Beta(alpha/2; k, n - k + 1)
    Upper = Beta(1 - alpha/2; k + 1, n - k)
    """
    if n == 0:
        return 0.0, 0.0
    alpha = 1.0 - confidence
    lower = stats.beta.ppf(alpha / 2.0, k, n - k + 1) if k > 0 else 0.0
    upper = stats.beta.ppf(1.0 - alpha / 2.0, k + 1, n - k) if k < n else 1.0
    return float(lower), float(upper)


def compute_sum_distribution(sums: List[int]) -> Dict:
    """M1 - M2: Đếm thực tế, kỳ vọng, Z-score và Clopper-Pearson 95% cho các tổng 3..18."""
    n = len(sums)
    counts = Counter(sums)
    results = {}

    for s in range(3, 19):
        p_s = float(THEORETICAL_PROB_SUM[s])
        o_s = counts.get(s, 0)
        e_s = n * p_s

        # Z-score chuẩn hóa: z = (o - e) / sqrt(n * p * (1 - p))
        std_err = np.sqrt(n * p_s * (1.0 - p_s)) if n > 0 else 1.0
        z_s = (o_s - e_s) / std_err if std_err > 0 else 0.0

        ci_lower, ci_upper = compute_clopper_pearson_ci(o_s, n, confidence=0.95)

        results[s] = {
            "sum": s,
            "ways": THEORETICAL_WAYS[s],
            "prob_theoretical": p_s,
            "observed": o_s,
            "expected": round(e_s, 2),
            "ratio": round(o_s / n, 6) if n > 0 else 0.0,
            "z_score": round(float(z_s), 4),
            "ci_95_lower": round(ci_lower, 6),
            "ci_95_upper": round(ci_upper, 6),
        }

    return {"n": n, "distribution": results}


def compute_chisquare_sums(sums: List[int]) -> Dict:
    """M3: Kiểm định Chi-square goodness-of-fit cho phân phối tổng (df=15)."""
    n = len(sums)
    if n == 0:
        return {"chi2": 0.0, "df": 15, "p_value": 1.0, "is_significant": False}

    counts = Counter(sums)
    observed = [counts.get(s, 0) for s in range(3, 19)]
    expected = [n * float(THEORETICAL_PROB_SUM[s]) for s in range(3, 19)]

    # Chi-square stat: sum((o - e)^2 / e)
    res = stats.chisquare(f_obs=observed, f_exp=expected)
    chi2_stat = float(res.statistic)
    p_value = float(res.pvalue)

    return {
        "n": n,
        "chi2": round(chi2_stat, 4),
        "df": 15,
        "p_value": p_value,
        "is_significant": p_value < 0.05,
    }


def compute_dice_goodness_of_fit(all_dice: List[int]) -> Dict:
    """Kiểm định Chi-square đều cho từng mặt xúc xắc 1..6 (df=5)."""
    n = len(all_dice)
    if n == 0:
        return {"chi2": 0.0, "df": 5, "p_value": 1.0, "is_significant": False}

    counts = Counter(all_dice)
    observed = [counts.get(face, 0) for face in range(1, 7)]
    expected = [n / 6.0] * 6

    res = stats.chisquare(f_obs=observed, f_exp=expected)
    return {
        "n": n,
        "chi2": round(float(res.statistic), 4),
        "df": 5,
        "p_value": float(res.pvalue),
        "is_significant": float(res.pvalue) < 0.05,
        "counts": {face: counts.get(face, 0) for face in range(1, 7)},
    }


def compute_ordered_combinations_chisquare(draws: List[Tuple[int, int, int]]) -> Dict:
    """Kiểm định Chi-square đều cho 216 tổ hợp có thứ tự (df=215)."""
    n = len(draws)
    if n == 0:
        return {"chi2": 0.0, "df": 215, "p_value": 1.0, "is_significant": False}

    counts = Counter(draws)
    all_combos = list(itertools.product(range(1, 7), repeat=3))
    observed = [counts.get(c, 0) for c in all_combos]
    expected = [n / 216.0] * 216

    res = stats.chisquare(f_obs=observed, f_exp=expected)
    return {
        "n": n,
        "chi2": round(float(res.statistic), 4),
        "df": 215,
        "p_value": float(res.pvalue),
        "is_significant": float(res.pvalue) < 0.05,
    }


def compute_unordered_combinations_chisquare(draws: List[Tuple[int, int, int]]) -> Dict:
    """Kiểm định Chi-square cho 56 tổ hợp không thứ tự (df=55)."""
    n = len(draws)
    if n == 0:
        return {"chi2": 0.0, "df": 55, "p_value": 1.0, "is_significant": False}

    sorted_draws = [tuple(sorted(d)) for d in draws]
    counts = Counter(sorted_draws)

    observed = []
    expected = []
    for item in UNORDERED_COMBINATIONS:
        combo = item["combination"]
        observed.append(counts.get(combo, 0))
        expected.append(n * float(item["probability"]))

    res = stats.chisquare(f_obs=observed, f_exp=expected)
    return {
        "n": n,
        "chi2": round(float(res.statistic), 4),
        "df": 55,
        "p_value": float(res.pvalue),
        "is_significant": float(res.pvalue) < 0.05,
    }
