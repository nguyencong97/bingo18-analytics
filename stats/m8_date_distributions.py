"""Mô-đun M8: Phân phối theo Ngày và Kiểm định Ngoại lai (Date x Sum Distributions)."""

from collections import Counter, defaultdict
from typing import Dict, List, Tuple
from scipy import stats

from stats.constants import THEORETICAL_PROB_SUM


def compute_date_sum_matrix(records: List[Dict]) -> Dict:
    """M8: Tính ma trận Ngày x Tổng và kiểm định các ngày vượt dải tin cậy 95% nhị thức.

    Với mỗi ngày d có N_d kỳ:
    - Kỳ vọng e_{d,s} = N_d * p_s
    - Ngưỡng dưới/trên từ phân phối Binomial(N_d, p_s) tại mức 2.5% và 97.5%
    - So sánh tổng số ngày ngoại lai với phân phối Binomial(tổng số ngày, 0.05).
    """
    by_date: Dict[str, List[int]] = defaultdict(list)
    for r in records:
        date = r["date"]
        total = int(r["total"])
        by_date[date].append(total)

    sorted_dates = sorted(by_date.keys())
    num_days = len(sorted_dates)
    daily_matrix = {}
    outlier_counts_by_sum = {s: 0 for s in range(3, 19)}
    total_outlier_instances = 0

    for d in sorted_dates:
        sums_in_day = by_date[d]
        n_d = len(sums_in_day)
        counts = Counter(sums_in_day)

        day_stats = {
            "date": d,
            "draw_count": n_d,
            "sums": {},
            "has_outlier": False
        }

        for s in range(3, 19):
            p_s = float(THEORETICAL_PROB_SUM[s])
            obs = counts.get(s, 0)
            exp = n_d * p_s

            # Ngưỡng nhị thức 95% cho n_d phép thử
            low_bound = int(stats.binom.ppf(0.025, n_d, p_s))
            high_bound = int(stats.binom.ppf(0.975, n_d, p_s))

            is_outlier = obs < low_bound or obs > high_bound
            if is_outlier:
                day_stats["has_outlier"] = True
                outlier_counts_by_sum[s] += 1
                total_outlier_instances += 1

            day_stats["sums"][s] = {
                "observed": obs,
                "expected": round(exp, 2),
                "lower_95": low_bound,
                "upper_95": high_bound,
                "is_outlier": is_outlier
            }

        daily_matrix[d] = day_stats

    # Kiểm định binomial cho số ngày ngoại lai:
    # Kỳ vọng mỗi tổng có khoảng 5% số ngày ngoại lai
    expected_outlier_days_per_sum = num_days * 0.05
    sum_outlier_tests = {}
    for s in range(3, 19):
        obs_days = outlier_counts_by_sum[s]
        # P-value hai phía từ Binomial(num_days, 0.05)
        p_val = float(stats.binomtest(obs_days, num_days, 0.05).pvalue) if num_days > 0 else 1.0
        sum_outlier_tests[s] = {
            "outlier_days": obs_days,
            "expected_outlier_days": round(expected_outlier_days_per_sum, 1),
            "p_value": round(p_val, 4),
            "is_anomalous": p_val < 0.05
        }

    return {
        "num_days": num_days,
        "daily_matrix": daily_matrix,
        "sum_outlier_tests": sum_outlier_tests,
        "total_outlier_instances": total_outlier_instances
    }
