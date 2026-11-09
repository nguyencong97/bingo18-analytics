"""Kiểm thử bộ phân tích crawler dựa trên fixtures mẫu thật."""

import json
from pathlib import Path
import pytest

from crawler.parser import parse_ajaxpro_html_content, parse_draw_rows
from crawler.storage import DataStorage
from backfill.reconcile import compute_file_sha256

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.parametrize("sample_idx", [1, 2, 3, 4, 5])
def test_parse_real_fixtures(sample_idx):
    """Kiểm tra parser hoạt động chính xác 100% trên cả 5 mẫu thật từ Vietlott."""
    fixture_file = FIXTURES_DIR / f"vietlott_sample_{sample_idx}.json"
    assert fixture_file.exists(), f"Thiếu tệp fixture: {fixture_file}"

    with open(fixture_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    html_content = parse_ajaxpro_html_content(raw_text)
    assert html_content is not None
    assert "<table" in html_content

    valid, errors = parse_draw_rows(html_content, snapshot_id=f"test_sample_{sample_idx}")
    assert len(errors) == 0, f"Có lỗi khi phân tích fixture {sample_idx}: {errors}"
    assert len(valid) == 6, f"Mỗi mẫu thật có 6 kỳ quay, thực tế trích xuất được: {len(valid)}"

    for rec in valid:
        assert 1 <= rec["d1"] <= 6
        assert 1 <= rec["d2"] <= 6
        assert 1 <= rec["d3"] <= 6
        assert rec["d1"] + rec["d2"] + rec["d3"] == rec["total"]
        assert len(rec["draw_id"]) >= 6
        assert rec["status"] == "confirmed"


def test_parser_quarantines_invalid_sum():
    """Kiểm tra hàng có tổng sai lệch bị đưa vào danh sách lỗi."""
    html_bad = (
        '<table><tr><th>Header</th></tr>'
        '<tr>'
        '  <td><a href="...">09/11/2026</a><div><a href="...">#9999999</a></div></td>'
        '  <td><span class="bong_tron_bingo">2</span><span class="bong_tron_bingo">3</span><span class="bong_tron_bingo">4</span></td>'
        '  <td>15</td>'  # 2 + 3 + 4 = 9 != 15
        '  <td>Lớn</td>'
        '</tr></table>'
    )
    valid, errors = parse_draw_rows(html_bad, snapshot_id="bad_test")
    assert len(valid) == 0
    assert len(errors) == 1
    assert "Tổng 15 không bằng" in errors[0]["error_reason"]


def test_checksum_tamper_detection(tmp_path):
    """Kiểm tra sửa 1 byte dữ liệu làm đổi mã băm SHA-256."""
    dummy_csv = tmp_path / "2026-11.csv"
    dummy_csv.write_text("draw_id,total\n001,10\n", encoding="utf-8")
    hash_orig = compute_file_sha256(dummy_csv)

    # Sửa 1 ký tự
    dummy_csv.write_text("draw_id,total\n001,11\n", encoding="utf-8")
    hash_tampered = compute_file_sha256(dummy_csv)

    assert hash_orig != hash_tampered
