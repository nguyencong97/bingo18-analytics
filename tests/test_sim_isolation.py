"""Kiểm thử tính cách ly của bộ mô phỏng (sim/) và tính bất biến theo seed."""

from pathlib import Path
import pytest
import numpy as np

from sim.null_generator import NullSimulationEngine

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_seed_reproducibility():
    """Cùng seed phải sinh ra kết quả xúc xắc hoàn toàn trùng khớp."""
    engine1 = NullSimulationEngine(seed=20261109)
    d1, s1 = engine1.generate_fair_draws(100)

    engine2 = NullSimulationEngine(seed=20261109)
    d2, s2 = engine2.generate_fair_draws(100)

    assert np.array_equal(d1, d2)
    assert np.array_equal(s1, s2)


def test_label_mandatory():
    """Mọi kết quả mô phỏng bắt buộc phải mang nhãn 'MÔ PHỎNG'."""
    engine = NullSimulationEngine(seed=20261109)
    res = engine.run_monte_carlo_null_distribution(real_n=1000, real_chi2_sum=15.0, num_simulations=10)
    assert res["label"] == "MÔ PHỎNG"
    for item in res["sample_1day_simulated"]:
        assert item["label"] == "MÔ PHỎNG"


def test_no_sim_files_in_data():
    """Tuyệt đối không có tệp tin mô phỏng nào nằm trong data/."""
    for file in DATA_DIR.rglob("*"):
        if file.is_file():
            assert "sim" not in file.name.lower()
            assert "null" not in file.name.lower()
            assert "mock" not in file.name.lower()
