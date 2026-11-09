"""Kiểm thử cho UserSheetParser."""

import pytest
from backfill.user_sheet_parser import parse_cell_result, normalize_date_column, UserSheetParser


def test_parse_cell_result_valid():
    """Kiểm tra parse các chuỗi hợp lệ dạng ngắt dòng và khoảng trắng."""
    assert parse_cell_result("2\n5\n1\n\n8") == (2, 5, 1, 8)
    assert parse_cell_result("2 5 1 8") == (2, 5, 1, 8)
    assert parse_cell_result("  6  6  6  18  ") == (6, 6, 6, 18)
    assert parse_cell_result("1\r\n1\r\n1\r\n\r\n3") == (1, 1, 1, 3)


def test_parse_cell_result_empty():
    """Ô trống trả về None."""
    assert parse_cell_result("") is None
    assert parse_cell_result("   ") is None
    assert parse_cell_result("\n\n") is None


def test_parse_cell_result_invalid_sum():
    """Tổng không khớp phải báo lỗi."""
    with pytest.raises(ValueError, match="Tổng 9 không khớp"):
        parse_cell_result("2 5 1 9")


def test_parse_cell_result_out_of_range():
    """Xúc xắc ngoài [1, 6] phải báo lỗi."""
    with pytest.raises(ValueError, match="ngoài khoảng"):
        parse_cell_result("7 1 1 9")
    with pytest.raises(ValueError, match="ngoài khoảng"):
        parse_cell_result("0 4 4 8")


def test_parse_cell_result_wrong_token_count():
    """Thiếu hoặc thừa số phải báo lỗi."""
    with pytest.raises(ValueError, match="Số lượng phần tử khác 4"):
        parse_cell_result("2 5 1")
    with pytest.raises(ValueError, match="Số lượng phần tử khác 4"):
        parse_cell_result("2 5 1 8 10")


def test_normalize_date_column():
    """Kiểm tra chuẩn hóa định dạng ngày."""
    assert normalize_date_column("Thời gian") is None
    assert normalize_date_column("01/11", default_year=2026) == "2026-11-01"
    assert normalize_date_column("08/11", default_year=2026) == "2026-11-08"
    assert normalize_date_column("Hôm nay", default_year=2026) == "2026-11-09"
    assert normalize_date_column("15/12/2025") == "2025-12-15"


def test_parse_csv_content():
    """Kiểm tra parse toàn bộ bảng CSV mô phỏng."""
    csv_mock = (
        "Thời gian,01/11,Hôm nay\n"
        '06:05,"2\n5\n1\n\n8","4\n1\n1\n\n6"\n'
        '06:11,"1\n6\n6\n\n13",\n'
        '06:17,"2\n5\n1\n\n9","5\n6\n1\n\n12"\n'  # 2 5 1 9 là lỗi tổng
    )
    parser = UserSheetParser(default_year=2026)
    valid, errors = parser.parse_csv_content(csv_mock, fetched_at="2026-11-09T10:00:00Z")

    # Có 4 ô có dữ liệu:
    # 06:05 (01/11): hợp lệ
    # 06:05 (Hôm nay): hợp lệ
    # 06:11 (01/11): hợp lệ
    # 06:17 (01/11): lỗi tổng (2+5+1 != 9)
    # 06:17 (Hôm nay): hợp lệ
    assert len(valid) == 4
    assert len(errors) == 1

    assert errors[0]["error_reason"].startswith("Tổng 9 không khớp")
    assert valid[0]["d1"] == 2 and valid[0]["d2"] == 5 and valid[0]["d3"] == 1 and valid[0]["total"] == 8
    assert valid[0]["slot_in_day"] == 1
    assert valid[0]["date"] == "2026-11-01"
