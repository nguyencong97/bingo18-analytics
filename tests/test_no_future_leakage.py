"""Kiểm thử tự động kiểm tra KHÔNG RÒ RỈ DỮ LIỆU TƯƠNG LAI (No future data leakage)."""

import pytest
import numpy as np
from stats.m16_predictive_models import PredictiveBacktester


def test_no_future_leakage_assertion():
    """Đảm bảo tại mỗi bước t, hàm dự đoán chỉ nhận history[:t], không thể thấy sums[t] hoặc sums[t+1:]."""
    # Mẫu 600 số
    np.random.seed(42)
    fake_sums = np.random.randint(3, 19, size=600).tolist()
    backtester = PredictiveBacktester(fake_sums, window_size=500)

    # Đánh chặn dự đoán và kiểm tra độ dài dữ liệu truyền vào
    step_history_lens = []

    def mock_predict(history):
        step_history_lens.append(len(history))
        return backtester.theoretical_vec.copy()

    # Thực hiện test 50 bước
    backtester._predict_uniform = mock_predict
    res = backtester.run_backtest(test_steps=50)

    # Kiểm tra: Độ dài lịch sử mỗi bước t phải tăng đơn điệu từ 550 đến 599
    expected_lens = list(range(550, 600))
    assert step_history_lens == expected_lens
    for h_len in step_history_lens:
        assert h_len < 600  # Luôn nhỏ hơn tổng số phần tử


def test_diebold_mariano_identical_loss():
    """Hai mô hình mất mát y hệt nhau thì DM stat = 0 và p-value = 1.0."""
    from stats.m16_predictive_models import diebold_mariano_test
    loss = np.ones(100)
    stat, p = diebold_mariano_test(loss, loss)
    assert stat == 0.0
    assert p == 1.0
