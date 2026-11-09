"""Mô-đun M14: Bộ sinh mô phỏng ngẫu nhiên công bằng đối chứng (Null Simulation Engine).

TUYỆT ĐỐI TUÂN THỦ NGUYÊN TẮC:
1. Dữ liệu mô phỏng CHỈ nằm trong sim/ và kết quả trong results/, KHÔNG BAO GIỜ ghi vào data/.
2. Mọi kết quả mô phỏng luôn gắn nhãn rõ ràng: 'MÔ PHỎNG'.
3. Sử dụng seed cố định để đảm bảo tính tái lập 100%.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

from stats.constants import THEORETICAL_PROB_SUM


class NullSimulationEngine:
    """Bộ máy mô phỏng null đối chứng độc lập."""

    def __init__(self, seed: int = 20261109):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate_fair_draws(self, n: int) -> Tuple[np.ndarray, np.ndarray]:
        """Sinh n kỳ quay xúc xắc công bằng 100% (3 xúc xắc 1..6 độc lập).

        Trả về (dice_matrix: shape [n, 3], sums: shape [n]).
        """
        dice = self.rng.integers(1, 7, size=(n, 3))
        sums = dice.sum(axis=1)
        return dice, sums

    def run_monte_carlo_null_distribution(
        self, real_n: int, real_chi2_sum: float, num_simulations: int = 1000
    ) -> Dict:
        """Chạy B >= 1000 bộ mô phỏng để tính p-value thực nghiệm cho Chi-square."""
        expected_counts = np.array([
            real_n * float(THEORETICAL_PROB_SUM[s]) for s in range(3, 19)
        ])

        sim_chi2_values = []
        count_extreme = 0

        for b in range(num_simulations):
            _, sim_sums = self.generate_fair_draws(real_n)
            # Đếm số lần về của các tổng 3..18
            counts = np.bincount(sim_sums, minlength=19)[3:19]
            chi2_stat = float(np.sum(((counts - expected_counts) ** 2) / expected_counts))
            sim_chi2_values.append(chi2_stat)

            if chi2_stat >= real_chi2_sum:
                count_extreme += 1

        empirical_p_value = (1 + count_extreme) / (1 + num_simulations)

        # Tính toán phân vị của phân phối mô phỏng
        quantiles = {
            "p50": float(np.percentile(sim_chi2_values, 50)),
            "p90": float(np.percentile(sim_chi2_values, 90)),
            "p95": float(np.percentile(sim_chi2_values, 95)),
            "p99": float(np.percentile(sim_chi2_values, 99)),
        }

        # Sinh một chuỗi mô phỏng mẫu 159 kỳ (1 ngày) để so sánh trực quan "Ảo giác quy luật"
        sample_dice, sample_sums = self.generate_fair_draws(159)
        sample_draws = []
        for i in range(159):
            d1, d2, d3 = sample_dice[i].tolist()
            tot = int(sample_sums[i])
            sample_draws.append({
                "slot": i + 1,
                "d1": d1,
                "d2": d2,
                "d3": d3,
                "total": tot,
                "label": "MÔ PHỎNG",
                "classification": "Lớn" if tot >= 12 else ("Nhỏ" if tot <= 9 else "Hòa")
            })

        return {
            "label": "MÔ PHỎNG",
            "seed": self.seed,
            "num_simulations": num_simulations,
            "real_n": real_n,
            "real_chi2_sum": round(real_chi2_sum, 4),
            "empirical_p_value": round(empirical_p_value, 5),
            "extreme_count": count_extreme,
            "sim_chi2_quantiles": quantiles,
            "sample_1day_simulated": sample_draws
        }
