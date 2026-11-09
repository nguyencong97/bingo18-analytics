function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🎲 Bingo18")
    .addItem("📥 Nạp dữ liệu gần nhất", "loadRecentData")
    .addToUi();
}

function loadRecentData() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
  sheet.setName("Chi tiết");
  sheet.clear();
  var url = "https://raw.githubusercontent.com/nguyencong97/bingo18-analytics/main/data/sheet_initial_import.csv";
  var resp = UrlFetchApp.fetch(url);
  var csvData = Utilities.parseCsv(resp.getContentText());
  var header = csvData[0];
  var recentRows = csvData.slice(-3000); // 3,000 kỳ mới nhất
  var allRows = [header].concat(recentRows);
  sheet.getRange(1, 1, allRows.length, header.length).setValues(allRows);
  sheet.getRange(1, 1, 1, header.length).setFontWeight("bold").setBackground("#F18806").setFontColor("#FFFFFF");
  SpreadsheetApp.getUi().alert("✅ Đã nạp thành công " + recentRows.length + " kỳ quay mới nhất vào Sheet!");
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Chi tiết") || SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var list = data.records || (data.record ? [data.record] : []);
    for (var i = 0; i < list.length; i++) {
      var r = list[i];
      if (r && r.draw_id) {
        sheet.appendRow([r.draw_id, r.date, r.time, r.slot_in_day, r.d1, r.d2, r.d3, r.total, r.result, new Date()]);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({ status: "ok", count: list.length })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", msg: err.toString() })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet() {
  return ContentService.createTextOutput("Bingo18 Web App OK");
}
