"""Mô-đun M9 - M13: Phân tích Khung giờ/Thứ, Benjamini-Hochberg FDR, Phổ & Entropy, CUSUM Drift, Bayesian Dirichlet."""

from collections import Counter, defaultdict
from datetime import datetime
import math
from typing import Dict, List, Tuple
import numpy as np
from scipy import stats

from stats.constants import THEORETICAL_PROB_SUM


def apply_benjamini_hochberg(p_values: List[float], alpha: float = 0.05) -> List[Dict]:
    """M10: Hiệu chỉnh đa so sánh Benjamini-Hochberg (FDR).

    Trả về danh sách các bản ghi kèm raw_p, adj_p, is_significant.
    """
    m = len(p_values)
    if m == 0:
        return []

    # Ghép cặp chỉ số ban đầu để hoàn trả theo đúng thứ tự
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m

    # Bước tính q-value theo thứ tự tăng dần
    # adj_p[i] = min(1.0, raw_p * m / rank)
    cum_min = 1.0
    for rank_rev, (orig_idx, p_val) in enumerate(reversed(indexed)):
        rank = m - rank_rev
        adj = min(cum_min, p_val * m / rank)
        adjusted[orig_idx] = min(1.0, adj)
        cum_min = adj

    results = []
    for orig_idx, p_val in enumerate(p_values):
        adj_p = adjusted[orig_idx]
        results.append({
            "raw_p": round(p_val, 6),
            "adj_p": round(adj_p, 6),
            "is_significant": adj_p < alpha
        })
    return results


def compute_time_and_day_independence(records: List[Dict]) -> Dict:
    """M9: Phân tích Khung giờ x Tổng và Thứ trong tuần x Tổng (df=90)."""
    # 1. Thứ trong tuần (0: Thứ 2 .. 6: Chủ Nhật)
    dow_matrix = np.zeros((7, 16), dtype=int)
    # 2. Khung 30 phút trong ngày (từ 06:00 đến 22:00 -> 32 khung)
    slot30_matrix = defaultdict(lambda: np.zeros(16, dtype=int))

    for r in records:
        date_str = r["date"]
        time_str = r["time"]
        total = int(r["total"]) - 3
        if not (0 <= total <= 15):
            continue

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            dow = dt.weekday()
            dow_matrix[dow, total] += 1
        except Exception:
            pass

        if time_str and ":" in time_str:
            parts = time_str.split(":")
            h, m = int(parts[0]), int(parts[1])
            slot_idx = h * 2 + (1 if m >= 30 else 0)
            slot30_matrix[slot_idx][total] += 1

    # Chi-square kiểm định độc lập cho Thứ x Tổng (7x16)
    # Bỏ các hàng có tổng = 0 nếu có
    valid_dow = dow_matrix[dow_matrix.sum(axis=1) > 0]
    dow_chi2, dow_p, dow_df, _ = stats.chi2_contingency(valid_dow)

    # Chi-square cho Khung 30-phút x Tổng
    valid_slots = [slot30_matrix[k] for k in sorted(slot30_matrix.keys()) if slot30_matrix[k].sum() > 0]
    if len(valid_slots) > 1:
        slot_matrix = np.array(valid_slots)
        slot_chi2, slot_p, slot_df, _ = stats.chi2_contingency(slot_matrix)
    else:
        slot_chi2, slot_p, slot_df = 0.0, 1.0, 0

    return {
        "day_of_week_test": {
            "chi2": round(float(dow_chi2), 4),
            "df": int(dow_df),
            "p_value": float(dow_p),
            "is_significant": float(dow_p) < 0.05
        },
        "time_slot_test": {
            "chi2": round(float(slot_chi2), 4),
            "df": int(slot_df),
            "p_value": float(slot_p),
            "is_significant": float(slot_p) < 0.05
        }
    }


def compute_spectral_and_entropy(sums: List[int]) -> Dict:
    """M11: Periodogram FFT của chuỗi tổng chuẩn hóa và Shannon Entropy."""
    n = len(sums)
    if n < 100:
        return {}

    arr = np.array(sums, dtype=float)
    standardized = (arr - np.mean(arr)) / (np.std(arr) or 1.0)

    # FFT Periodogram
    fft_vals = np.fft.rfft(standardized)
    power_spectrum = (np.abs(fft_vals) ** 2) / n
    # Bỏ thành phần DC (index 0)
    max_power = float(np.max(power_spectrum[1:]))

    # Shannon Entropy thực tế: H = -sum(p * log2(p))
    counts = Counter(sums)
    actual_entropy = 0.0
    for s in range(3, 19):
        cnt = counts.get(s, 0)
        if cnt > 0:
            p = cnt / n
            actual_entropy -= p * math.log2(p)

    # Shannon Entropy lý thuyết
    theoretical_entropy = 0.0
    for s in range(3, 19):
        p_theo = float(THEORETICAL_PROB_SUM[s])
        theoretical_entropy -= p_theo * math.log2(p_theo)

    return {
        "max_spectral_power": round(max_power, 4),
        "actual_entropy_bits": round(actual_entropy, 5),
        "theoretical_entropy_bits": round(theoretical_entropy, 5),
        "entropy_diff": round(abs(actual_entropy - theoretical_entropy), 5),
        "is_entropy_close": abs(actual_entropy - theoretical_entropy) < 0.05
    }


def compute_cusum_drift(sums: List[int], window_size: int = 5000, step: int = 500) -> Dict:
    """M12: CUSUM trên chỉ số Chi-square của cửa sổ trượt (Window=5000, Step=500)."""
    n = len(sums)
    if n < window_size:
        return {"has_drift": False, "windows_evaluated": 0}

    rolling_chi2 = []
    for start in range(0, n - window_size + 1, step):
        w_sums = sums[start : start + window_size]
        counts = Counter(w_sums)
        obs = [counts.get(s, 0) for s in range(3, 19)]
        exp = [window_size * float(THEORETICAL_PROB_SUM[s]) for s in range(3, 19)]
        chi2_val = float(stats.chisquare(obs, exp).statistic)
        rolling_chi2.append(chi2_val)

    # Ngưỡng cảnh báo CUSUM: Chi2(15) phân phối có trung bình 15, độ lệch chuẩn sqrt(30) ≈ 5.48
    # CUSUM phát hiện khi Chi-square vượt quá ngưỡng 99.9% (~37.7)
    max_rolling_chi2 = max(rolling_chi2) if rolling_chi2 else 0.0
    has_drift = max_rolling_chi2 > 37.697

    return {
        "windows_evaluated": len(rolling_chi2),
        "max_rolling_chi2": round(max_rolling_chi2, 4),
        "threshold_999": 37.697,
        "has_drift": has_drift
    }


def compute_bayesian_dirichlet(sums: List[int]) -> Dict:
    """M13: Dirichlet(alpha=1) posterior phân phối tổng và 95% Credible Intervals."""
    n = len(sums)
    counts = Counter(sums)
    results = {}

    # Prior Dirichlet(alpha_0 = 1) -> Posterior Dirichlet(alpha_s = 1 + o_s)
    alpha_post = {s: 1.0 + counts.get(s, 0) for s in range(3, 19)}
    sum_alpha = sum(alpha_post.values())

    for s in range(3, 19):
        a = alpha_post[s]
        b = sum_alpha - a
        # Marginal posterior của từng p_s là phân phối Beta(a, b)
        cred_lower = float(stats.beta.ppf(0.025, a, b))
        cred_upper = float(stats.beta.ppf(0.975, a, b))
        p_theo = float(THEORETICAL_PROB_SUM[s])

        results[s] = {
            "sum": s,
            "posterior_mean": round(a / sum_alpha, 6),
            "theoretical_prob": round(p_theo, 6),
            "credible_95_lower": round(cred_lower, 6),
            "credible_95_upper": round(cred_upper, 6),
            "theoretical_in_credible_interval": cred_lower <= p_theo <= cred_upper
        }

    return {"bayesian_sums": results}
