/**
 * =========================================================================
 * BINGO18 ANALYTICS - GOOGLE APPS SCRIPT WEB APP
 * =========================================================================
 * Bảng tính: https://docs.google.com/spreadsheets/d/1X5bozWVSq1_Nzag87b5OdNQ1BUAvoDwriWLnvwZ9xbY/
 *
 * HƯỚNG DẪN CÀI ĐẶT 1 LẦN DUY NHẤT:
 * 1. Mở bảng tính Google Sheet trên trình duyệt.
 * 2. Trên thanh menu, chọn: Tiện ích mở rộng (Extensions) -> Apps Script.
 * 3. Xóa nội dung mặc định trong tệp Code.gs và dán toàn bộ đoạn mã này vào.
 * 4. Bấm biểu tượng "Lưu" (Ctrl + S).
 * 5. Bấm nút màu xanh "Triển khai" (Deploy) ở góc trên bên phải -> "Tùy chọn triển khai mới" (New deployment).
 * 6. Bấm biểu tượng bánh răng chọn loại: "Ứng dụng web" (Web app).
 * 7. Thiết lập cấu hình:
 *    - Mô tả: Bingo18 Live Sync
 *    - Thực thi dưới dạng: Tôi (email của bạn)
 *    - Ai có quyền truy cập: "Bất kỳ ai" (Anyone)
 * 8. Bấm "Triển khai" (Deploy) và cấp quyền (Authorize access).
 * 9. Sao chép "URL ứng dụng web" (Web App URL) nhận được.
 */

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "No post data" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var payload = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Chi tiết");
    
    // Nếu chưa có sheet 'Chi tiết', khởi tạo tự động
    if (!sheet) {
      sheet = ss.getActiveSheet();
      sheet.setName("Chi tiết");
      sheet.appendRow(["Mã kỳ", "Ngày quay", "Giờ", "Slot", "Xúc xắc 1", "Xúc xắc 2", "Xúc xắc 3", "Tổng", "Bộ số", "Thời điểm ghi nhận"]);
      sheet.getRange(1, 1, 1, 10).setFontWeight("bold").setBackground("#F18806").setFontColor("#FFFFFF");
    }

    // Ghi nhận bản ghi đơn lẻ hoặc danh sách
    var records = payload.records || (payload.record ? [payload.record] : []);
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      sheet.appendRow([
        r.draw_id || "",
        r.date || "",
        r.time || "",
        r.slot_in_day || "",
        r.d1 || "",
        r.d2 || "",
        r.d3 || "",
        r.total || "",
        r.result || "",
        new Date().toISOString()
      ]);
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      appended: records.length,
      timestamp: new Date().toISOString()
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("Bingo18 Analytics Web App is active and running!")
    .setMimeType(ContentService.MimeType.TEXT);
}
