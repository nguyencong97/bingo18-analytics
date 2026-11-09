"""Mô-đun M4 - M7: Độc lập giữa các viên, Ma trận chuyển Markov, ACF & Runs Test, Return Gaps."""

from collections import Counter, defaultdict
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

from stats.constants import (
    THEORETICAL_PROB_SUM,
    P_CONSECUTIVE_SAME_SUM,
    TOTAL_ORDERED_OUTCOMES
)


def compute_dice_pair_independence(draws: List[Tuple[int, int, int]]) -> Dict:
    """M4: Bảng 6x6 kiểm định độc lập giữa các cặp xúc xắc (d1,d2), (d1,d3), (d2,d3).

    Kỳ vọng e_ij = n / 36, chi-square df = 25.
    """
    n = len(draws)
    if n == 0:
        return {}

    pairs = [("d1_d2", 0, 1), ("d1_d3", 0, 2), ("d2_d3", 1, 2)]
    results = {}
    e_ij = n / 36.0

    for pair_name, idx1, idx2 in pairs:
        matrix = np.zeros((6, 6), dtype=int)
        for d in draws:
            v1 = d[idx1] - 1
            v2 = d[idx2] - 1
            matrix[v1, v2] += 1

        observed = matrix.flatten()
        expected = np.full(36, e_ij)
        res = stats.chisquare(f_obs=observed, f_exp=expected)

        results[pair_name] = {
            "chi2": round(float(res.statistic), 4),
            "df": 25,
            "p_value": float(res.pvalue),
            "is_significant": float(res.pvalue) < 0.05,
        }

    return results


def compute_markov_transition_matrix(sums: List[int]) -> Dict:
    """M5: Ma trận chuyển bậc 1 T[i][j] (16x16) và kiểm định lặp tổng.

    Kỳ vọng dưới giả thuyết độc lập: E[i][j] = r_i * p_j.
    Kiểm định P(sum_{t+1} == sum_t) so với 4332/46656 ≈ 0.092850.
    """
    n = len(sums)
    if n < 2:
        return {}

    # Bảng 16x16 từ tổng 3 đến 18 (index 0..15)
    t_matrix = np.zeros((16, 16), dtype=int)
    consecutive_same_count = 0

    for t in range(n - 1):
        s_curr = sums[t] - 3
        s_next = sums[t + 1] - 3
        t_matrix[s_curr, s_next] += 1
        if sums[t] == sums[t + 1]:
            consecutive_same_count += 1

    total_transitions = n - 1
    # Kiểm định lặp tổng: P(tổng sau = tổng trước)
    p_obs = consecutive_same_count / total_transitions
    p_theo = float(P_CONSECUTIVE_SAME_SUM)
    std_err = math.sqrt(p_theo * (1.0 - p_theo) / total_transitions)
    z_repeat = (p_obs - p_theo) / std_err if std_err > 0 else 0.0
    p_val_repeat = float(2.0 * (1.0 - stats.norm.cdf(abs(z_repeat))))

    # Chi-square trên ma trận gộp 10 lớp để tránh ô thưa (E < 5):
    # Lớp: [3-6], 7, 8, 9, 10, 11, 12, 13, 14, [15-18]
    def bin_idx(s: int) -> int:
        if s <= 6:
            return 0
        elif s >= 15:
            return 9
        return s - 6

    binned_matrix = np.zeros((10, 10), dtype=int)
    for t in range(n - 1):
        binned_matrix[bin_idx(sums[t]), bin_idx(sums[t + 1])] += 1

    row_sums = binned_matrix.sum(axis=1)
    col_sums = binned_matrix.sum(axis=0)
    expected_binned = np.outer(row_sums, col_sums) / total_transitions

    # Chi-square df = (10-1)*(10-1) = 81
    res_binned = stats.chisquare(f_obs=binned_matrix.flatten(), f_exp=expected_binned.flatten())

    return {
        "n_transitions": total_transitions,
        "consecutive_repeat": {
            "observed_count": consecutive_same_count,
            "observed_prob": round(p_obs, 6),
            "theoretical_prob": round(p_theo, 6),
            "z_score": round(z_repeat, 4),
            "p_value": p_val_repeat,
            "is_significant": p_val_repeat < 0.05,
        },
        "independence_test_binned_df81": {
            "chi2": round(float(res_binned.statistic), 4),
            "df": 81,
            "p_value": float(res_binned.pvalue),
            "is_significant": float(res_binned.pvalue) < 0.05,
        },
    }


def compute_autocorrelation_and_runs(sums: List[int], max_lags: int = 50) -> Dict:
    """M6: Tự tương quan ACF(k) k=1..50, Ljung-Box test, và Runs test."""
    n = len(sums)
    if n < max_lags + 10:
        return {}

    arr = np.array(sums, dtype=float)
    mean = np.mean(arr)
    var = np.var(arr)
    centered = arr - mean

    # ACF(k)
    acf_values = []
    bound_95 = 1.96 / math.sqrt(n)
    for lag in range(1, max_lags + 1):
        cov = np.mean(centered[lag:] * centered[:-lag])
        r_k = float(cov / var) if var > 0 else 0.0
        acf_values.append({
            "lag": lag,
            "acf": round(r_k, 5),
            "bound_upper": round(bound_95, 5),
            "bound_lower": round(-bound_95, 5),
            "is_significant": abs(r_k) > bound_95,
        })

    # Ljung-Box statistic Q(m) = n(n+2) * sum(r_k^2 / (n - k))
    q_stat = 0.0
    for item in acf_values:
        k = item["lag"]
        r_k = item["acf"]
        q_stat += (r_k ** 2) / (n - k)
    q_stat *= n * (n + 2)
    p_val_ljung_box = float(1.0 - stats.chi2.cdf(q_stat, df=max_lags))

    # Runs test trên chuỗi Lớn/Nhỏ (bỏ Hòa: 10..11)
    big_small_seq = []
    for s in sums:
        if s >= 12:
            big_small_seq.append(1)  # Lớn
        elif s <= 9:
            big_small_seq.append(0)  # Nhỏ

    n_bs = len(big_small_seq)
    n1 = sum(big_small_seq)
    n0 = n_bs - n1
    runs = 1
    for i in range(1, n_bs):
        if big_small_seq[i] != big_small_seq[i - 1]:
            runs += 1

    mu_runs = (2.0 * n0 * n1 / n_bs) + 1.0
    var_runs = (2.0 * n0 * n1 * (2.0 * n0 * n1 - n_bs)) / ((n_bs ** 2) * (n_bs - 1.0))
    z_runs = (runs - mu_runs) / math.sqrt(var_runs) if var_runs > 0 else 0.0
    p_val_runs = float(2.0 * (1.0 - stats.norm.cdf(abs(z_runs))))

    return {
        "acf_lags": acf_values,
        "ljung_box": {
            "q_stat": round(q_stat, 4),
            "df": max_lags,
            "p_value": p_val_ljung_box,
            "is_significant": p_val_ljung_box < 0.05,
        },
        "runs_test_big_small": {
            "n_trials": n_bs,
            "runs": runs,
            "expected_runs": round(mu_runs, 2),
            "z_score": round(z_runs, 4),
            "p_value": p_val_runs,
            "is_random": p_val_runs >= 0.05,
        },
    }


def compute_return_gaps(sums: List[int]) -> Dict:
    """M7: Phân phối khoảng cách giữa hai lần về liên tiếp của từng tổng G ~ Geometric(p)."""
    n = len(sums)
    gap_stats = {}

    for s in range(3, 19):
        p_s = float(THEORETICAL_PROB_SUM[s])
        gaps = []
        last_idx = -1

        for i, val in enumerate(sums):
            if val == s:
                if last_idx != -1:
                    gaps.append(i - last_idx)
                last_idx = i

        if not gaps:
            continue

        mean_gap = float(np.mean(gaps))
        expected_mean = 1.0 / p_s
        max_gap = max(gaps)

        # KS test so với Geometric(p_s)
        # scipy.stats.kstest với cdf của geom
        ks_res = stats.kstest(gaps, "geom", args=(p_s,))

        gap_stats[s] = {
            "sum": s,
            "hits": len(gaps) + 1,
            "mean_gap": round(mean_gap, 2),
            "expected_mean_gap": round(expected_mean, 2),
            "max_gap": max_gap,
            "ks_statistic": round(float(ks_res.statistic), 4),
            "ks_p_value": float(ks_res.pvalue),
            "is_geometric": float(ks_res.pvalue) >= 0.05,
        }

    return gap_stats
