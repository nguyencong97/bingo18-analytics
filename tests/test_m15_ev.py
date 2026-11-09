"""Kiểm thử tính toán EV, RTP, House Edge."""

from pathlib import Path
import pytest
from stats.m15_ev_calculator import compute_expected_values

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "payouts.json"


def test_ev_calculator_basic():
    res = compute_expected_values(CONFIG_PATH)
    assert "bets" in res
    assert "sum" in res["bets"]
    assert "big_small_draw" in res["bets"]
    assert "any_triple" in res["bets"]

    # Kiểm tra House Edge của tất cả các cửa cược đều > 0 (nhà cái luôn có lợi thế)
    for s, item in res["bets"]["sum"].items():
        assert item["house_edge_pct"] > 0
        assert item["expected_value"] < 0
        assert item["rtp_pct"] < 100.0

    # Lớn/Nhỏ/Hòa
    for name, item in res["bets"]["big_small_draw"].items():
        assert item["house_edge_pct"] > 0
        assert item["rtp_pct"] < 100.0


def test_unverified_warning():
    res = compute_expected_values(CONFIG_PATH)
    # Vì payouts.json đang để verified: false nên bắt buộc phải có cảnh báo
    assert res["verified"] is False
    assert res["warning"] is not None
    assert "CẢNH BÁO" in res["warning"]
