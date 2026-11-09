"""Kiểm thử chuẩn hóa bản ghi từ vietvudanh."""

import pytest
from backfill.vietvudanh_loader import normalize_vietvudanh_record


def test_normalize_valid_record():
    raw = {
        "date": "2024-12-03",
        "id": "0083123",
        "result": [2, 6, 1],
        "total": 9,
        "large_small": "Nhỏ",
        "process_time": "2025-06-23T14:52:28+07:00"
    }
    norm = normalize_vietvudanh_record(raw)
    assert norm is not None
    assert norm["draw_id"] == "0083123"
    assert norm["d1"] == 2 and norm["d2"] == 6 and norm["d3"] == 1
    assert norm["total"] == 9
    assert norm["result"] == "2 6 1 9"
    assert norm["source"] == "vietvudanh_github"


def test_normalize_invalid_dice():
    # Xúc xắc có giá trị 0 hoặc 7
    raw = {"date": "2024-12-03", "id": "1", "result": [0, 5, 4], "total": 9}
    assert normalize_vietvudanh_record(raw) is None

    raw2 = {"date": "2024-12-03", "id": "2", "result": [7, 1, 1], "total": 9}
    assert normalize_vietvudanh_record(raw2) is None


def test_normalize_sum_mismatch():
    raw = {"date": "2024-12-03", "id": "3", "result": [2, 2, 2], "total": 7}
    assert normalize_vietvudanh_record(raw) is None
