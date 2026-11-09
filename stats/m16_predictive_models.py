"""Mô-đun M16: Đánh giá và Backtest các mô hình dự báo không rò rỉ dữ liệu tương lai."""

from collections import Counter
import math
from typing import Callable, Dict, List, Tuple
import numpy as np
from scipy import stats

from stats.constants import THEORETICAL_PROB_SUM
from stats.m9_m13_analysis import apply_benjamini_hochberg


def diebold_mariano_test(
    loss_baseline: np.ndarray, loss_candidate: np.ndarray
) -> Tuple[float, float]:
    """Kiểm định Diebold-Mariano hai phía giữa 2 chuỗi mất mát dự báo.

    d_t = loss_candidate_t - loss_baseline_t
    H0: E[d_t] == 0 (hai mô hình có độ chính xác dự báo tương đương)
    """
    d = loss_candidate - loss_baseline
    n = len(d)
    if n < 10:
        return 0.0, 1.0

    mean_d = float(np.mean(d))
    # Ước lượng phương sai tiệm cận (HAC lag 0)
    gamma0 = float(np.var(d, ddof=1))
    std_err = math.sqrt(gamma0 / n) if gamma0 > 0 else 1.0

    dm_stat = mean_d / std_err if std_err > 0 else 0.0
    # Phân phối tiệm cận chuẩn N(0, 1)
    p_value = float(2.0 * (1.0 - stats.norm.cdf(abs(dm_stat))))
    return dm_stat, p_value


class PredictiveBacktester:
    """Bộ máy Backtest tuần tự Walk-Forward (không rò rỉ tương lai)."""

    def __init__(self, sums: List[int], window_size: int = 500):
        self.sums = sums
        self.window_size = window_size
        self.n = len(sums)
        self.theoretical_vec = np.array([float(THEORETICAL_PROB_SUM[s]) for s in range(3, 19)])

    def _predict_uniform(self, history: List[int]) -> np.ndarray:
        """Baseline lý thuyết ngẫu nhiên đều."""
        return self.theoretical_vec.copy()

    def _predict_hot_n(self, history: List[int], n_hot: int = 3) -> np.ndarray:
        """Mô hình chuỗi nóng (Hot-N): tăng xác suất các tổng về nhiều gần đây."""
        sub = history[-self.window_size :]
        counts = Counter(sub)
        probs = self.theoretical_vec.copy()
        top_sums = [s for s, _ in counts.most_common(n_hot)]
        for s in top_sums:
            probs[s - 3] *= 1.3
        return probs / probs.sum()

    def _predict_cold_n(self, history: List[int], n_cold: int = 3) -> np.ndarray:
        """Mô hình chuỗi lạnh (Cold-N / Gambler's Fallacy): đặt cược vào số ít về."""
        sub = history[-self.window_size :]
        counts = Counter(sub)
        probs = self.theoretical_vec.copy()
        # Tìm các số xuất hiện ít nhất
        least_common = sorted(range(3, 19), key=lambda s: counts.get(s, 0))[:n_cold]
        for s in least_common:
            probs[s - 3] *= 1.3
        return probs / probs.sum()

    def _predict_bayes(self, history: List[int]) -> np.ndarray:
        """Mô hình Bayes Dirichlet-Multinomial posterior trong cửa sổ gần nhất."""
        sub = history[-self.window_size :]
        counts = Counter(sub)
        alphas = np.array([1.0 + counts.get(s, 0) for s in range(3, 19)])
        return alphas / alphas.sum()

    def _predict_markov1(self, history: List[int]) -> np.ndarray:
        """Mô hình Markov bậc 1 dựa trên tổng kỳ liền trước trong cửa sổ gần nhất."""
        prev_sum = history[-1]
        sub = history[-self.window_size :]
        transitions = Counter()
        for t in range(len(sub) - 1):
            if sub[t] == prev_sum:
                transitions[sub[t + 1]] += 1

        total_t = sum(transitions.values())
        if total_t < 5:
            return self.theoretical_vec.copy()

        # Làm trơn Laplace với prior lý thuyết
        smoothed = np.array([
            (transitions.get(s, 0) + 5.0 * self.theoretical_vec[s - 3])
            / (total_t + 5.0)
            for s in range(3, 19)
        ])
        return smoothed / smoothed.sum()

    def run_backtest(self, test_steps: int = 5000) -> Dict:
        """Chạy backtest tuần tự qua test_steps kỳ gần nhất."""
        if self.n <= self.window_size + 10:
            return {}

        start_idx = max(self.window_size, self.n - test_steps)
        eval_indices = range(start_idx, self.n)
        n_eval = len(eval_indices)

        models = {
            "uniform_baseline": self._predict_uniform,
            "hot_3": self._predict_hot_n,
            "cold_3": self._predict_cold_n,
            "bayes": self._predict_bayes,
            "markov_1": self._predict_markov1,
        }

        # Lưu log-loss và brier score từng bước
        losses_log = {m: np.zeros(n_eval) for m in models}
        losses_brier = {m: np.zeros(n_eval) for m in models}
        top3_hits = {m: 0 for m in models}

        for step_i, t in enumerate(eval_indices):
            # Dữ liệu huấn luyện CHỈ đến t-1 (TUYỆT ĐỐI KHÔNG CÓ TƯƠNG LAI)
            history = self.sums[:t]
            actual_y = self.sums[t]
            y_idx = actual_y - 3

            one_hot = np.zeros(16)
            one_hot[y_idx] = 1.0

            for m_name, predict_fn in models.items():
                p_vec = predict_fn(history)
                # Đảm bảo phân phối xác suất hợp lệ
                p_vec = np.clip(p_vec, 1e-12, 1.0)
                p_vec = p_vec / p_vec.sum()

                # Log-loss: -log P(y)
                losses_log[m_name][step_i] = -math.log(p_vec[y_idx])

                # Brier score: sum((p_s - 1_{y=s})^2)
                losses_brier[m_name][step_i] = np.sum((p_vec - one_hot) ** 2)

                # Top-3 hit
                top3_indices = np.argsort(p_vec)[-3:]
                if y_idx in top3_indices:
                    top3_hits[m_name] += 1

        baseline_loss = losses_log["uniform_baseline"]
        model_results = {}
        dm_p_values = []
        candidate_names = []

        for m_name in models:
            avg_log_loss = float(np.mean(losses_log[m_name]))
            avg_brier = float(np.mean(losses_brier[m_name]))
            top3_rate = float(top3_hits[m_name] / n_eval)

            dm_stat, dm_p = 0.0, 1.0
            if m_name != "uniform_baseline":
                dm_stat, dm_p = diebold_mariano_test(baseline_loss, losses_log[m_name])
                dm_p_values.append(dm_p)
                candidate_names.append(m_name)

            model_results[m_name] = {
                "model_name": m_name,
                "mean_log_loss": round(avg_log_loss, 5),
                "mean_brier_score": round(avg_brier, 5),
                "top3_hit_rate": round(top3_rate * 100.0, 2),
                "diebold_mariano_stat": round(dm_stat, 4),
                "diebold_mariano_p_value": round(dm_p, 4),
            }

        # Áp dụng Benjamini-Hochberg cho các phép so sánh Diebold-Mariano
        fdr_dm = apply_benjamini_hochberg(dm_p_values, alpha=0.05)
        for idx, m_name in enumerate(candidate_names):
            model_results[m_name]["dm_p_adjusted"] = fdr_dm[idx]["adj_p"]
            model_results[m_name]["is_significantly_better"] = (
                fdr_dm[idx]["is_significant"]
                and model_results[m_name]["diebold_mariano_stat"] < 0
            )

        return {
            "evaluated_draws": n_eval,
            "models": model_results,
            "conclusion": (
                "Không có mô hình nào vượt qua được Baseline ngẫu nhiên (Uniform) có ý nghĩa thống kê."
                if not any(r.get("is_significantly_better", False) for r in model_results.values())
                else "Có mô hình vượt trội."
            ),
        }
