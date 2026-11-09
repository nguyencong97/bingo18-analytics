# Tài liệu cấu trúc phản hồi dữ liệu Bingo18 từ Vietlott

## 1. Giao thức mạng & Điểm cuối (Endpoint)
- **URL**: `https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.GameBingoCompareWebPart,Vietlott.PlugIn.WebParts.ashx`
- **Phương thức HTTP**: `POST`
- **HTTP Headers bắt buộc**:
  - `Content-Type`: `text/plain; charset=utf-8`
  - `X-AjaxPro-Method`: `ServerSideDrawResult`
  - `Origin`: `https://vietlott.vn`
  - `Referer`: `https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-bingo18`
- **Cấu trúc Payload (JSON dạng thô)**:
  ```json
  {
    "ORenderInfo": {
      "SiteId": "main.frontend.vi",
      "SiteAlias": "main.vi",
      "SiteLang": "vi",
      "SiteName": "Vietlott"
    },
    "GameId": "8",
    "GameDrawNo": "",
    "number": "",
    "DrawDate": "",
    "PageIndex": 1,
    "TotalRow": 10
  }
  ```

## 2. Cấu trúc phản hồi JSON
Phản hồi là một đối tượng JSON có khóa `value`:
```json
{
  "value": {
    "HtmlContent": "<table>...</table>"
  }
}
```

## 3. Cấu trúc bảng HTML bên trong `HtmlContent`
- Thẻ bảng: `<table class="table table-hover"><tbody>...</tbody></table>`
- Dòng tiêu đề (header): `<tr>` đầu tiên chứa các cột:
  - Cột 1: `Ngày /Kỳ`
  - Cột 2: `Kết quả`
  - Cột 3: `Tổng`
  - Cột 4: `Lớn/hòa/nhỏ`
- Dòng dữ liệu: Các thẻ `<tr>` tiếp theo:
  - **Cột 1 (`<td>`)**: Chứa 2 thẻ `<a>`:
    - Thẻ `<a>` thứ 1: Chuỗi ngày định dạng `DD/MM/YYYY` (ví dụ `09/11/2026`).
    - Thẻ `<a>` thứ 2: Mã kỳ quay dạng `#0195407` (loại bỏ ký tự `#` để lấy mã `0195407`).
  - **Cột 2 (`<td>`)**: Chứa kết quả 3 viên xúc xắc:
    - Nằm trong `<span class="bong_tron_bingo small">X</span>` (lặp 3 lần ứng với $d_1, d_2, d_3$).
  - **Cột 3 (`<td>`)**: Giá trị tổng (`total`), dạng số nguyên chuỗi (ví dụ `13`).
  - **Cột 4 (`<td>`)**: Phân loại (`Lớn`, `Hòa`, `Nhỏ`).

## 4. Ràng buộc toàn vẹn dữ liệu
- $d_1, d_2, d_3 \in [1, 6]$.
- $d_1 + d_2 + d_3 == \text{total}$.
- `draw_id` là chuỗi số 7 chữ số (ví dụ `0195407`), tăng đơn điệu.
