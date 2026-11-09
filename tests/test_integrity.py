"""Kiểm thử cho bộ kiểm tra tính toàn vẹn (stats/integrity.py)."""

from pathlib import Path
import pytest
from stats.integrity import verify_integrity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_verify_integrity_passes_on_current_data():
    """Kiểm tra dữ liệu hiện tại trong data/ phải vượt qua 100% các kiểm định."""
    assert verify_integrity(DATA_DIR) is True
