/**
 * =========================================================================
 * BINGO18 ANALYTICS PRO - HỆ THỐNG ĐÁM MÂY TỰ ĐỘNG 24/7 & DỰ ĐOÁN M16
 * =========================================================================
 * Tính năng chính:
 * 1. Bóc tách trực tiếp Vietlott AjaxPro bằng regex span.bong_tron_bingo
 * 2. Cố định chuẩn 9 cột dữ liệu (Mã kỳ đến Bộ số), loại bỏ cột thừa
 * 3. Nút 1-click '🧹 Chuẩn hóa dữ liệu Sheet Chi tiết' đồng bộ kiểu dữ liệu
 * 4. Tự động hóa 24/7 (Time-driven Trigger mỗi 10 phút, 06:00 - 22:15 VN)
 * 5. Bảng Thống kê & Biểu đồ nhúng đa khung thời gian (Hôm nay, Tuần này, Tuần trước)
 * 6. Bảng Dự đoán Hợp nhất M16 (Markov, Bayes, Hot-500, H0)
 * 7. BẢNG DỰ ĐOÁN BỘ SỐ THEO TỪNG KỲ QUAY (Xúc xắc 1-2-3, Tổng dự đoán, Đối chiếu thực tế, Tỉ lệ trong ngày)
 * 8. Tự động đồng bộ khi có thay đổi (autoSyncJob, doPost webhook, và trigger onEdit)
 */

// -------------------------------------------------------------------------
// 1. MENU VÀ GIAO DIỆN NGƯỜI DÙNG
// -------------------------------------------------------------------------
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🎲 Bingo18 Pro")
    .addItem("🚀 Kích hoạt Tự động hóa 24/7 (10 phút/lần)", "installAutoJob")
    .addItem("🔄 Đồng bộ & Cập nhật tất cả ngay bây giờ", "manualRunAll")
    .addSeparator()
    .addItem("🧹 Chuẩn hóa dữ liệu Sheet Chi tiết (Đồng bộ kiểu dữ liệu)", "standardizeChiTietSheetWithAlert")
    .addItem("📊 Tạo / Cập nhật Sheet Thống kê & Biểu đồ", "setupStatsAndChartsSheet")
    .addItem("🔮 Tạo / Cập nhật Sheet Dự đoán Hàng ngày", "setupPredictionSheet")
    .addSeparator()
    .addItem("⏸️ Tạm dừng Tự động hóa", "removeAutoJob")
    .addToUi();
}

// -------------------------------------------------------------------------
// 2. TỰ ĐỘNG HÓA 24/7 (TIME-DRIVEN TRIGGER & ONEDIT TRIGGER)
// -------------------------------------------------------------------------
function installAutoJob() {
  removeAutoJobQuietly();
  
  ScriptApp.newTrigger("autoSyncVietlottJob")
    .timeBased()
    .everyMinutes(10)
    .create();

  manualRunAll();

  SpreadsheetApp.getUi().alert(
    "✅ Tự động hóa 24/7 đã kích hoạt thành công!\n\n" +
    "- Tần suất: Cứ mỗi 10 phút hệ thống sẽ tự động kéo các kỳ quay mới về.\n" +
    "- Khung giờ: 06:00 đến 22:15 giờ Việt Nam (ngoài giờ này job tự nghỉ để tiết kiệm quota).\n" +
    "- Tự động đồng bộ: Cả 2 sheet Thống kê và Dự đoán sẽ tự động cập nhật ngay khi có kỳ mới!\n" +
    "- Hệ thống chạy ngầm vĩnh viễn trên đám mây của Google, bạn không cần mở máy hay thao tác gì nữa!"
  );
}

function removeAutoJob() {
  removeAutoJobQuietly();
  SpreadsheetApp.getUi().alert("⏸️ Đã tạm dừng Tự động hóa thành công.");
}

function removeAutoJobQuietly() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "autoSyncVietlottJob") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

function manualRunAll() {
  autoSyncVietlottJob();
  setupStatsAndChartsSheet();
  setupPredictionSheet();
}

/**
 * Trigger tự động khi người dùng chỉnh sửa hoặc dán thêm dữ liệu thủ công vào sheet 'Chi tiết'
 */
function onEdit(e) {
  try {
    if (!e || !e.range) return;
    var sheet = e.range.getSheet();
    if (sheet && sheet.getName() === "Chi tiết") {
      if (e.range.getRow() >= 2) {
        updateStatsAndChartsSheet();
        updatePredictionSheet();
      }
    }
  } catch (err) {
    Logger.log("onEdit error: " + err);
  }
}

// -------------------------------------------------------------------------
// 3. CHUẨN HÓA ĐỊNH DẠNG SHEET 'CHI TIẾT' (9 CỘT ĐỒNG NHẤT 100%)
// -------------------------------------------------------------------------
function standardizeChiTietSheetWithAlert() {
  standardizeChiTietSheet();
  SpreadsheetApp.getUi().alert(
    "✅ Đã chuẩn hóa thành công sheet 'Chi tiết'!\n\n" +
    "- Toàn bộ cột đã về đúng 9 cột chuẩn.\n" +
    "- Kiểu dữ liệu đã được đồng bộ thống nhất: Mã kỳ (text 7 chữ số), Ngày (yyyy-mm-dd), Xúc xắc & Tổng (số nguyên)."
  );
}

function standardizeChiTietSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
  sheet.setName("Chi tiết");

  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  if (lastRow < 1) return;

  // 1. Chuẩn hóa tiêu đề chính xác 9 cột
  var headers = [["Mã kỳ", "Ngày quay", "Giờ", "Slot", "Xúc xắc 1", "Xúc xắc 2", "Xúc xắc 3", "Tổng", "Bộ số"]];
  sheet.getRange(1, 1, 1, 9).setValues(headers)
    .setFontWeight("bold").setBackground("#F18806").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  // Xóa các cột thừa từ cột 10 trở đi (nếu có cột thứ 10 cũ bị ghi đè)
  if (lastCol > 9) {
    sheet.deleteColumns(10, lastCol - 9);
  }

  // 2. Chuẩn hóa kiểu dữ liệu cho toàn bộ các dòng
  if (lastRow > 1) {
    var numRows = lastRow - 1;
    // Cột A: Mã kỳ dạng Text (giữ đủ 7 chữ số có số 0 ở đầu)
    sheet.getRange(2, 1, numRows, 1).setNumberFormat("@").setHorizontalAlignment("center");
    // Cột B: Ngày quay dạng yyyy-mm-dd
    sheet.getRange(2, 2, numRows, 1).setNumberFormat("yyyy-mm-dd").setHorizontalAlignment("center");
    // Cột C: Giờ
    sheet.getRange(2, 3, numRows, 1).setNumberFormat("@").setHorizontalAlignment("center");
    // Cột D: Slot
    sheet.getRange(2, 4, numRows, 1).setNumberFormat("#,##0").setHorizontalAlignment("center");
    // Cột E..H: Xúc xắc 1, 2, 3 và Tổng (Số nguyên)
    sheet.getRange(2, 5, numRows, 4).setNumberFormat("#,##0").setHorizontalAlignment("center");
    // Cột I: Bộ số dạng Text
    sheet.getRange(2, 9, numRows, 1).setNumberFormat("@").setHorizontalAlignment("center");
  }

  sheet.setFrozenRows(1);
}

// -------------------------------------------------------------------------
// 4. JOB TỰ ĐỘNG KÉO KẾT QUẢ VIETLOTT (MỖI 10 PHÚT)
// -------------------------------------------------------------------------
function autoSyncVietlottJob() {
  try {
    var vnHour = Number(Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "HH"));
    var vnMin = Number(Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "mm"));
    if (vnHour < 6 || (vnHour >= 22 && vnMin > 15)) {
      Logger.log("Ngoài khung giờ quay số Vietlott (06:00 - 22:15 VN). Job tạm nghỉ.");
      return;
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
    sheet.setName("Chi tiết");

    var lastRow = sheet.getLastRow();
    var existingIds = {};
    if (lastRow > 1) {
      var checkRows = Math.min(300, lastRow - 1);
      var idValues = sheet.getRange(lastRow - checkRows + 1, 1, checkRows, 1).getValues();
      for (var i = 0; i < idValues.length; i++) {
        var rawId = String(idValues[i][0]).trim();
        if (rawId) {
          var cleanId = rawId.replace("#", "").padStart(7, "0");
          existingIds[cleanId] = true;
          existingIds[rawId] = true;
        }
      }
    }

    var newRecords = fetchLatestDrawsFromSources();
    var toAppend = [];
    for (var j = 0; j < newRecords.length; j++) {
      var r = newRecords[j];
      var rId = String(r.draw_id).replace("#", "").trim().padStart(7, "0");
      if (rId && !existingIds[rId]) {
        toAppend.push([
          rId,
          r.date,
          r.time || "",
          Number(r.slot_in_day || 0),
          Number(r.d1),
          Number(r.d2),
          Number(r.d3),
          Number(r.total),
          r.result || (r.d1 + " " + r.d2 + " " + r.d3 + " " + r.total)
        ]);
        existingIds[rId] = true;
      }
    }

    if (toAppend.length > 0) {
      toAppend.sort(function(a, b) { return String(a[0]).localeCompare(String(b[0])); });
      sheet.getRange(sheet.getLastRow() + 1, 1, toAppend.length, 9).setValues(toAppend);
      Logger.log("Đã thêm thành công " + toAppend.length + " kỳ quay mới vào sheet Chi tiết.");

      // Tự động làm mới cả 2 sheet Thống kê và Dự đoán
      updateStatsAndChartsSheet();
      updatePredictionSheet();
    } else {
      Logger.log("Không có kỳ quay mới nào cần thêm.");
    }
  } catch (err) {
    Logger.log("Lỗi trong autoSyncVietlottJob: " + err);
  }
}

function fetchLatestDrawsFromSources() {
  var records = [];
  
  // NGUỒN 1: CỔNG CHÍNH THỨC VIETLOTT AJAXPRO
  try {
    var url = "https://vietlott.vn/ajaxpro/Vietlott.PlugIn.WebParts.GameBingoCompareWebPart,Vietlott.PlugIn.WebParts.ashx";
    var options = {
      method: "post",
      headers: {
        "X-AjaxPro-Method": "ServerSideDrawResult",
        "Content-Type": "text/plain; charset=UTF-8",
        "User-Agent": "Mozilla/5.0"
      },
      payload: JSON.stringify({ PageIndex: 1, PageSize: 20 }),
      muteHttpExceptions: true
    };
    var resp = UrlFetchApp.fetch(url, options);
    if (resp.getResponseCode() === 200) {
      records = parseVietlottAjaxProResponse(resp.getContentText());
      if (records.length > 0) {
        Logger.log("Lấy trực tiếp từ Vietlott thành công: " + records.length + " kỳ.");
        return records;
      }
    }
  } catch (e) {
    Logger.log("Fetch Vietlott direct failed: " + e);
  }

  // NGUỒN 2: KHO GITHUB DỮ LIỆU THẬT (FALLBACK TỨC THÌ)
  try {
    var ym = Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "yyyy-MM");
    var ghUrl = "https://raw.githubusercontent.com/nguyencong97/bingo18-analytics/main/data/" + ym + ".csv";
    var ghResp = UrlFetchApp.fetch(ghUrl, { muteHttpExceptions: true });
    if (ghResp.getResponseCode() === 200) {
      records = parseCsvToRecords(ghResp.getContentText());
      if (records.length > 0) {
        Logger.log("Lấy từ GitHub fallback thành công: " + records.length + " kỳ.");
        return records;
      }
    }
  } catch (e2) {
    Logger.log("Fetch GitHub fallback failed: " + e2);
  }

  return records;
}

function parseVietlottAjaxProResponse(rawText) {
  var records = [];
  try {
    var jsonMatch = rawText.match(/\"HtmlContent\":\"([^\"]+)\"/);
    var html = jsonMatch ? jsonMatch[1].replace(/\\\"/g, '"').replace(/\\r\\n/g, '') : rawText;

    var rowRegex = /<tr[^>]*>([\s\S]*?)<\/tr>/gi;
    var match;
    while ((match = rowRegex.exec(html)) !== null) {
      var rowHtml = match[1];
      if (rowHtml.indexOf("<th") !== -1) continue;

      var idMatch = rowHtml.match(/#(\d{7})/);
      var dateMatch = rowHtml.match(/(\d{2})\/(\d{2})\/(\d{4})/);

      // BÓC TÁCH CHÍNH XÁC 3 VIÊN XÚC XẮC TỪ THẺ SPAN.BONG_TRON_BINGO
      var diceRegex = /<span[^>]*bong_tron_bingo[^>]*>(\d)<\/span>/gi;
      var diceMatch, dices = [];
      while ((diceMatch = diceRegex.exec(rowHtml)) !== null) {
        dices.push(Number(diceMatch[1]));
      }

      if (idMatch && dateMatch && dices.length === 3) {
        var d1 = dices[0], d2 = dices[1], d3 = dices[2];
        var total = d1 + d2 + d3;
        var drawId = idMatch[1];
        var dateFormatted = dateMatch[3] + "-" + dateMatch[2] + "-" + dateMatch[1];

        records.push({
          draw_id: drawId,
          date: dateFormatted,
          time: "",
          slot_in_day: 0,
          d1: d1, d2: d2, d3: d3, total: total,
          result: d1 + " " + d2 + " " + d3 + " " + total
        });
      }
    }
  } catch (e) {
    Logger.log("parseVietlottAjaxProResponse error: " + e);
  }
  return records;
}

function parseCsvToRecords(csvContent) {
  var lines = Utilities.parseCsv(csvContent);
  if (lines.length <= 1) return [];
  var records = [];
  var header = lines[0];

  var idxId = 0, idxDate = 1, idxTime = 2, idxSlot = 3, idxD1 = 4, idxD2 = 5, idxD3 = 6, idxTot = 7, idxRes = 8;
  if (header.indexOf("draw_id") !== -1) {
    idxId = header.indexOf("draw_id");
    idxDate = header.indexOf("date");
    idxTime = header.indexOf("time");
    idxSlot = header.indexOf("slot_in_day");
    idxD1 = header.indexOf("d1");
    idxD2 = header.indexOf("d2");
    idxD3 = header.indexOf("d3");
    idxTot = header.indexOf("total");
    idxRes = header.indexOf("result");
  }

  var recentLines = lines.slice(-60);
  for (var i = 0; i < recentLines.length; i++) {
    var cols = recentLines[i];
    if (cols.length >= 8 && cols[idxId] !== "draw_id" && cols[idxId] !== "Mã kỳ") {
      var d1 = Number(cols[idxD1]);
      var d2 = Number(cols[idxD2]);
      var d3 = Number(cols[idxD3]);
      var total = Number(cols[idxTot] || (d1 + d2 + d3));
      var drawId = String(cols[idxId]).replace("#", "").trim().padStart(7, "0");
      records.push({
        draw_id: drawId,
        date: String(cols[idxDate]),
        time: String(cols[idxTime] || ""),
        slot_in_day: Number(cols[idxSlot] || 0),
        d1: d1, d2: d2, d3: d3, total: total,
        result: String(cols[idxRes] || (d1 + " " + d2 + " " + d3 + " " + total))
      });
    }
  }
  return records;
}

// -------------------------------------------------------------------------
// 5. SHEET 'THỐNG KÊ & BIỂU ĐỒ' (ĐA KHUNG THỜI GIAN & BIỂU ĐỒ NHÚNG)
// -------------------------------------------------------------------------
var THEORETICAL_WAYS = [1, 3, 6, 10, 15, 21, 25, 27, 27, 25, 21, 15, 10, 6, 3, 1];

// Bảng ánh xạ bộ 3 viên xúc xắc tối ưu (có số hoán vị cao nhất) cho từng Tổng
var BEST_DICE_COMBO = {
  3: [1, 1, 1],
  4: [1, 1, 2],
  5: [1, 1, 3],
  6: [1, 2, 3],
  7: [1, 2, 4],
  8: [1, 3, 4],
  9: [2, 3, 4],
  10: [2, 3, 5],
  11: [2, 4, 5],
  12: [3, 4, 5],
  13: [3, 4, 6],
  14: [3, 5, 6],
  15: [4, 5, 6],
  16: [4, 6, 6],
  17: [5, 6, 6],
  18: [6, 6, 6]
};

function formatSlotTime(slot) {
  var s = Number(slot);
  if (isNaN(s) || s < 1) s = 1;
  if (s > 96) s = 96;
  var totalMins = 6 * 60 + 5 + (s - 1) * 10;
  var h = Math.floor(totalMins / 60);
  var m = totalMins % 60;
  return (h < 10 ? "0" + h : "" + h) + ":" + (m < 10 ? "0" + m : "" + m);
}

function getDrawTime(timeVal, slotVal, fallbackIndex) {
  var tStr = String(timeVal || "").trim();
  if (tStr && tStr.length >= 4 && tStr.indexOf(":") !== -1) return tStr;
  var s = Number(slotVal || 0);
  if (s <= 0 && fallbackIndex) s = fallbackIndex;
  if (s > 0) return formatSlotTime(s);
  return "--:--";
}

function extractDateStr(val) {
  if (!val) return "";
  if (val instanceof Date) {
    return Utilities.formatDate(val, "Asia/Ho_Chi_Minh", "yyyy-MM-dd");
  }
  var s = String(val).trim();
  var dmy = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (dmy) {
    return dmy[3] + "-" + dmy[2].padStart(2, "0") + "-" + dmy[1].padStart(2, "0");
  }
  var ymd = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (ymd) {
    return ymd[1] + "-" + ymd[2].padStart(2, "0") + "-" + ymd[3].padStart(2, "0");
  }
  return s.substring(0, 10);
}

function setupStatsAndChartsSheet() {
  updateStatsAndChartsSheet();
}

function updateStatsAndChartsSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Thống kê & Biểu đồ") || ss.insertSheet("Thống kê & Biểu đồ");
  var dataSheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
  var lastRow = dataSheet.getLastRow();
  if (lastRow < 2) return;

  var readRows = Math.min(5000, lastRow - 1);
  var rawData = dataSheet.getRange(lastRow - readRows + 1, 1, readRows, 9).getValues();

  var now = new Date();
  var todayStr = Utilities.formatDate(now, "Asia/Ho_Chi_Minh", "yyyy-MM-dd");
  var str7Ago = Utilities.formatDate(new Date(now.getTime() - 7 * 86400000), "Asia/Ho_Chi_Minh", "yyyy-MM-dd");
  var str14Ago = Utilities.formatDate(new Date(now.getTime() - 14 * 86400000), "Asia/Ho_Chi_Minh", "yyyy-MM-dd");

  var countToday = {}, countThisWeek = {}, countLastWeek = {};
  var totalToday = 0, totalThisWeek = 0, totalLastWeek = 0;
  var sizeWeek = { small: 0, tie: 0, big: 0 };
  var comboWeek = { triple: 0, pair: 0, distinct: 0 };

  for (var s = 3; s <= 18; s++) { countToday[s] = 0; countThisWeek[s] = 0; countLastWeek[s] = 0; }

  for (var r = 0; r < rawData.length; r++) {
    var row = rawData[r];
    var dateVal = extractDateStr(row[1]);
    var d1 = Number(row[4]), d2 = Number(row[5]), d3 = Number(row[6]), tot = Number(row[7]);
    if (tot < 3 || tot > 18) continue;

    if (dateVal === todayStr) { countToday[tot]++; totalToday++; }
    if (dateVal >= str7Ago) {
      countThisWeek[tot]++; totalThisWeek++;
      if (tot <= 9) sizeWeek.small++; else if (tot <= 11) sizeWeek.tie++; else sizeWeek.big++;
      if (d1 === d2 && d2 === d3) comboWeek.triple++; else if (d1 === d2 || d2 === d3 || d1 === d3) comboWeek.pair++; else comboWeek.distinct++;
    } else if (dateVal >= str14Ago && dateVal < str7Ago) {
      countLastWeek[tot]++; totalLastWeek++;
    }
  }

  sheet.clear();
  sheet.getRange("A1:N1").merge().setValue("BINGO18 ANALYTICS - THỐNG KÊ & BIẾN ĐỘNG TỈ LỆ ĐA KHUNG THỜI GIAN")
    .setFontWeight("bold").setFontSize(14).setBackground("#1E293B").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange("A2:N2").merge().setValue("Cập nhật tự động: " + Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "dd/MM/yyyy HH:mm:ss") + " | Số kỳ hôm nay: " + totalToday + " | Số kỳ tuần này: " + totalThisWeek)
    .setFontStyle("italic").setHorizontalAlignment("center");

  sheet.getRange(4, 1, 1, 9).setValues([["Tổng", "Cách tạo", "Lý thuyết H0 (%)", "Hôm nay (lần)", "Tuần này (lần)", "Tỉ lệ Tuần này (%)", "Tuần trước (lần)", "Tỉ lệ Tuần trước (%)", "Biến động (Delta %)"]])
    .setFontWeight("bold").setBackground("#3B82F6").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var table1Data = [];
  for (var sIdx = 3; sIdx <= 18; sIdx++) {
    var ways = THEORETICAL_WAYS[sIdx - 3];
    var pTheo = (ways / 216) * 100;
    var cTw = countThisWeek[sIdx];
    var pTw = totalThisWeek > 0 ? (cTw / totalThisWeek) * 100 : 0;
    var cLw = countLastWeek[sIdx];
    var pLw = totalLastWeek > 0 ? (cLw / totalLastWeek) * 100 : 0;
    table1Data.push([sIdx, ways, Number(pTheo.toFixed(2)), countToday[sIdx], cTw, Number(pTw.toFixed(2)), cLw, Number(pLw.toFixed(2)), Number((pTw - pLw).toFixed(2))]);
  }
  sheet.getRange(5, 1, 16, 9).setValues(table1Data).setHorizontalAlignment("center");

  sheet.getRange(4, 11, 1, 4).setValues([["Cửa cược", "Khoảng tổng", "Lý thuyết H0 (%)", "Tuần này (%)"]])
    .setFontWeight("bold").setBackground("#10B981").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  var totW = totalThisWeek > 0 ? totalThisWeek : 1;
  sheet.getRange(5, 11, 3, 4).setValues([
    ["Nhỏ", "3 .. 9", 37.50, Number(((sizeWeek.small / totW) * 100).toFixed(2))],
    ["Hòa", "10 .. 11", 25.00, Number(((sizeWeek.tie / totW) * 100).toFixed(2))],
    ["Lớn", "12 .. 18", 37.50, Number(((sizeWeek.big / totW) * 100).toFixed(2))]
  ]).setHorizontalAlignment("center");

  sheet.getRange(10, 11, 1, 4).setValues([["Tổ hợp xúc xắc", "Mô tả", "Lý thuyết H0 (%)", "Tuần này (%)"]])
    .setFontWeight("bold").setBackground("#8B5CF6").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange(11, 11, 3, 4).setValues([
    ["Tam hoa", "3 số giống nhau (111..666)", 2.78, Number(((comboWeek.triple / totW) * 100).toFixed(2))],
    ["Cặp số", "Có đúng 1 cặp trùng", 41.67, Number(((comboWeek.pair / totW) * 100).toFixed(2))],
    ["Khác nhau", "3 số hoàn toàn khác nhau", 55.56, Number(((comboWeek.distinct / totW) * 100).toFixed(2))]
  ]).setHorizontalAlignment("center");

  var charts = sheet.getCharts();
  for (var c = 0; c < charts.length; c++) sheet.removeChart(charts[c]);

  var chart1 = sheet.newChart().setChartType(Charts.ChartType.COLUMN)
    .addRange(sheet.getRange("A4:A20")).addRange(sheet.getRange("C4:C20")).addRange(sheet.getRange("F4:F20")).addRange(sheet.getRange("H4:H20"))
    .setPosition(22, 1, 10, 10).setOption("title", "SO SÁNH TỈ LỆ 16 TỔNG: LÝ THUYẾT H0 vs TUẦN NÀY vs TUẦN TRƯỚC (%)")
    .setOption("colors", ["#94A3B8", "#3B82F6", "#F97316"]).setOption("legend", { position: "top" }).setOption("width", 720).setOption("height", 340).build();
  sheet.insertChart(chart1);

  var chart2 = sheet.newChart().setChartType(Charts.ChartType.PIE)
    .addRange(sheet.getRange("K4:K7")).addRange(sheet.getRange("N4:N7"))
    .setPosition(22, 11, 10, 10).setOption("title", "TỈ LỆ CỬA CƯỢC THỰC TẾ TUẦN NÀY (LỚN / HÒA / NHỎ)")
    .setOption("pieHole", 0.4).setOption("colors", ["#3B82F6", "#F59E0B", "#EF4444"]).setOption("width", 450).setOption("height", 340).build();
  sheet.insertChart(chart2);
}

// -------------------------------------------------------------------------
// 6. SHEET 'DỰ ĐOÁN HÀNG NGÀY' (MÔ HÌNH HỢP NHẤT M16 & BẢNG DỰ ĐOÁN THEO TỪNG KỲ)
// -------------------------------------------------------------------------
function setupPredictionSheet() {
  updatePredictionSheet();
}

function updatePredictionSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Dự đoán hàng ngày") || ss.insertSheet("Dự đoán hàng ngày");
  var dataSheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
  var lastRow = dataSheet.getLastRow();
  if (lastRow < 20) return;

  var readCount = Math.min(2000, lastRow - 1);
  var rawData = dataSheet.getRange(lastRow - readCount + 1, 1, readCount, 9).getValues();

  var historySums = [];
  var lastRowData = rawData[rawData.length - 1];
  for (var i = 0; i < rawData.length; i++) {
    var tot = Number(rawData[i][7]);
    if (tot >= 3 && tot <= 18) historySums.push(tot);
  }

  var lastSum = historySums[historySums.length - 1];
  var lastDrawId = String(lastRowData[0]).replace("#", "").trim().padStart(7, "0");
  var lastResult = String(lastRowData[8]);

  // Phân phối lý thuyết H0 và tần suất Hot-N
  var pH0 = {}, counts = {}, pMarkov = {};
  for (var s = 3; s <= 18; s++) { pH0[s] = THEORETICAL_WAYS[s - 3] / 216.0; counts[s] = 0; }
  for (var h = 0; h < historySums.length; h++) counts[historySums[h]]++;

  // Ma trận chuyển trạng thái Markov bậc 1
  var transMatrix = {};
  for (var f = 3; f <= 18; f++) {
    transMatrix[f] = {};
    for (var t = 3; t <= 18; t++) transMatrix[f][t] = 0;
  }
  var markovTrans = {}, markovTotal = 0;
  for (var s4 = 3; s4 <= 18; s4++) markovTrans[s4] = 0;

  for (var m = 0; m < historySums.length - 1; m++) {
    var sFrom = historySums[m];
    var sTo = historySums[m + 1];
    if (sFrom >= 3 && sFrom <= 18 && sTo >= 3 && sTo <= 18) {
      transMatrix[sFrom][sTo]++;
      if (sFrom === lastSum) { markovTrans[sTo]++; markovTotal++; }
    }
  }

  for (var s5 = 3; s5 <= 18; s5++) {
    pMarkov[s5] = markovTotal >= 5 ? (markovTrans[s5] + 5.0 * pH0[s5]) / (markovTotal + 5.0) : pH0[s5];
  }

  var nHist = historySums.length;
  var ensembleList = [], predSmall = 0, predTie = 0, predBig = 0;

  for (var s7 = 3; s7 <= 18; s7++) {
    var pHot = counts[s7] / nHist;
    var pBayes = (counts[s7] + 1.0) / (nHist + 16.0);
    var pScore = 0.40 * pMarkov[s7] + 0.30 * pHot + 0.20 * pBayes + 0.10 * pH0[s7];
    var deltaVsH0 = ((pScore - pH0[s7]) / pH0[s7]) * 100;
    var trend = "Ổn định (Chuẩn H0)";
    if (deltaVsH0 > 15) trend = "🔥 Tăng nhiệt (Hot)"; else if (deltaVsH0 < -15) trend = "❄️ Hạ nhiệt (Cold)";

    if (s7 <= 9) predSmall += pScore; else if (s7 <= 11) predTie += pScore; else predBig += pScore;

    ensembleList.push({
      sum: s7,
      pH0: Number((pH0[s7] * 100).toFixed(2)),
      pHot: Number((pHot * 100).toFixed(2)),
      pMarkov: Number((pMarkov[s7] * 100).toFixed(2)),
      pBayes: Number((pBayes * 100).toFixed(2)),
      pEnsemble: Number((pScore * 100).toFixed(2)),
      delta: Number(deltaVsH0.toFixed(1)),
      trend: trend
    });
  }

  ensembleList.sort(function(a, b) { return b.pEnsemble - a.pEnsemble; });

  sheet.clear();
  sheet.getRange("A1:N1").merge().setValue("BINGO18 ANALYTICS - BẢNG DỰ BÁO XÁC SUẤT & PHÂN TÍCH H0 HÀNG NGÀY")
    .setFontWeight("bold").setFontSize(14).setBackground("#0F172A").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange("A2:N2").merge().setValue("Kỳ tham chiếu gần nhất: #" + lastDrawId + " | Kết quả: " + lastResult + " (Tổng " + lastSum + ") | Cập nhật: " + Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "dd/MM/yyyy HH:mm:ss"))
    .setFontStyle("italic").setHorizontalAlignment("center");

  // BẢNG 1: XÁC SUẤT HỢP NHẤT 16 TỔNG
  sheet.getRange(4, 1, 1, 9).setValues([["Hạng", "Tổng", "Dự phóng Hợp nhất (%)", "Lý thuyết H0 (%)", "Mô hình Markov (%)", "Mô hình Hot-500 (%)", "Mô hình Bayes (%)", "Độ lệch / H0 (%)", "Khuyến nghị xu hướng"]])
    .setFontWeight("bold").setBackground("#2563EB").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var mainRows = [];
  for (var rIdx = 0; rIdx < ensembleList.length; rIdx++) {
    var it = ensembleList[rIdx];
    mainRows.push([rIdx + 1, it.sum, it.pEnsemble, it.pH0, it.pMarkov, it.pHot, it.pBayes, it.delta, it.trend]);
  }
  sheet.getRange(5, 1, 16, 9).setValues(mainRows).setHorizontalAlignment("center");

  // THÔNG TIN BÊN PHẢI: TOP 3 & CỬA CƯỢC
  sheet.getRange("K4:N4").merge().setValue("🎯 TOP 3 TỔNG XÁC SUẤT CAO NHẤT KỲ TIẾP THEO")
    .setFontWeight("bold").setBackground("#D97706").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange(5, 11, 3, 4).setValues([
    ["Vị trí #1", "Tổng " + ensembleList[0].sum, ensembleList[0].pEnsemble + "%", ensembleList[0].trend],
    ["Vị trí #2", "Tổng " + ensembleList[1].sum, ensembleList[1].pEnsemble + "%", ensembleList[1].trend],
    ["Vị trí #3", "Tổng " + ensembleList[2].sum, ensembleList[2].pEnsemble + "%", ensembleList[2].trend]
  ]).setFontWeight("bold").setHorizontalAlignment("center");

  sheet.getRange("K9:N9").merge().setValue("⚖️ DỰ BÁO XÁC SUẤT CỬA LỚN / HÒA / NHỎ")
    .setFontWeight("bold").setBackground("#059669").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange(10, 11, 3, 4).setValues([
    ["Nhỏ (3..9)", Number((predSmall * 100).toFixed(2)) + "%", "Lý thuyết: 37.50%", predSmall > 0.38 ? "Ưu thế" : "Bình thường"],
    ["Hòa (10..11)", Number((predTie * 100).toFixed(2)) + "%", "Lý thuyết: 25.00%", predTie > 0.26 ? "Ưu thế" : "Bình thường"],
    ["Lớn (12..18)", Number((predBig * 100).toFixed(2)) + "%", "Lý thuyết: 37.50%", predBig > 0.38 ? "Ưu thế" : "Bình thường"]
  ]).setHorizontalAlignment("center");

  sheet.getRange("K14:N14").merge().setValue("⚠️ NGUYÊN TẮC KHOA HỌC & QUẢN TRỊ RỦI RO")
    .setFontWeight("bold").setBackground("#DC2626").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange(15, 11, 3, 1).mergeAcross().setValues([
    ["1. Giả thuyết H0: Xúc xắc công bằng, mỗi kỳ quay là độc lập ngẫu nhiên."],
    ["2. Mọi mô hình dự báo chỉ phản ánh xu hướng phân phối thống kê ngắn hạn."],
    ["3. Không có phương pháp nào đảm bảo 100% chiến thắng. Tuyệt đối không gấp thếp (Martingale)."]
  ]).setFontSize(9).setFontColor("#475569");

  // -----------------------------------------------------------------------
  // BẢNG DỰ ĐOÁN BỘ SỐ THEO TỪNG KỲ QUAY HÔM NAY (XÚC XẮC 1-2-3, TỔNG, ĐỐI CHIẾU, TỈ LỆ)
  // -----------------------------------------------------------------------
  var refDateStr = extractDateStr(lastRowData[1]);
  var todayDraws = [];
  var dailyCounts = {};
  for (var sInit = 3; sInit <= 18; sInit++) dailyCounts[sInit] = 0;

  for (var d = 0; d < rawData.length; d++) {
    var rowDate = extractDateStr(rawData[d][1]);
    if (rowDate === refDateStr) {
      var dTotal = Number(rawData[d][7]);
      if (dTotal >= 3 && dTotal <= 18) dailyCounts[dTotal]++;
      todayDraws.push({
        draw_id: String(rawData[d][0]).replace("#", "").trim().padStart(7, "0"),
        date: rowDate,
        time: String(rawData[d][2] || ""),
        slot: Number(rawData[d][3] || 0),
        d1: Number(rawData[d][4]),
        d2: Number(rawData[d][5]),
        d3: Number(rawData[d][6]),
        total: dTotal,
        result: String(rawData[d][8] || "")
      });
    }
  }

  var totalTodayDraws = todayDraws.length;

  // Hàm dự đoán tổng tối ưu dựa trên tổng kỳ trước đó qua ma trận Markov smoothed
  function getBestPredictedSumForState(priorSum) {
    if (priorSum >= 3 && priorSum <= 18) {
      var bestCand = 10, maxScore = -1;
      for (var cand = 3; cand <= 18; cand++) {
        var score = transMatrix[priorSum][cand] + 5.0 * (THEORETICAL_WAYS[cand - 3] / 216.0);
        if (score > maxScore) {
          maxScore = score;
          bestCand = cand;
        }
      }
      return bestCand;
    }
    return ensembleList[0].sum;
  }

  // Tiêu đề bảng dự đoán theo từng kỳ
  sheet.getRange("A22:I22").merge().setValue("🔮 BẢNG DỰ ĐOÁN BỘ SỐ THEO TỪNG KỲ QUAY HÔM NAY (" + refDateStr + ")")
    .setFontWeight("bold").setFontSize(13).setBackground("#1E293B").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange("A23:I23").merge().setValue("Kỳ kế tiếp được gắn nhãn [KỲ TIẾP THEO] ở đầu bảng | Đối chiếu kết quả thực tế & tỉ lệ tổng xuất hiện trong ngày")
    .setFontStyle("italic").setHorizontalAlignment("center");

  var tableHeaders = [["Mã kỳ", "Giờ quay", "Xúc xắc 1", "Xúc xắc 2", "Xúc xắc 3", "Tổng dự đoán", "Bộ số thực tế (từ Chi tiết)", "Kết quả đối chiếu", "Tỉ lệ Tổng trong ngày (%)"]];
  sheet.getRange(24, 1, 1, 9).setValues(tableHeaders)
    .setFontWeight("bold").setBackground("#4338CA").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  // DÒNG NỔI BẬT: KỲ TIẾP THEO (UPCOMING DRAW)
  var nextDrawNum = Number(lastDrawId.replace("#", "")) + 1;
  var nextDrawId = String(nextDrawNum).padStart(7, "0");
  var lastSlot = Number(lastRowData[3]) || (todayDraws.length > 0 ? todayDraws[todayDraws.length - 1].slot : 0);
  if (lastSlot <= 0) lastSlot = todayDraws.length;
  var nextSlot = lastSlot < 96 ? lastSlot + 1 : 1;
  var nextTimeStr = formatSlotTime(nextSlot);

  var topPredictedSum = ensembleList[0].sum;
  var topCombo = BEST_DICE_COMBO[topPredictedSum] || [3, 4, 4];
  var todayRateForPredicted = totalTodayDraws > 0 ?
    ((dailyCounts[topPredictedSum] / totalTodayDraws) * 100).toFixed(1) + "% (" + dailyCounts[topPredictedSum] + "/" + totalTodayDraws + " lần)" : "0%";

  var upcomingRow = [
    "#" + nextDrawId + " [KỲ TIẾP THEO]",
    nextTimeStr,
    topCombo[0],
    topCombo[1],
    topCombo[2],
    topPredictedSum,
    "⏳ Đang chờ mở thưởng...",
    "⏳ Chờ kết quả",
    todayRateForPredicted
  ];

  sheet.getRange(25, 1, 1, 9).setValues([upcomingRow])
    .setFontWeight("bold").setBackground("#FEF3C7").setFontColor("#92400E").setHorizontalAlignment("center");

  // CÁC KỲ ĐÃ QUAY TRONG NGÀY (SẮP XẾP TỪ KỲ MỚI NHẤT ĐẾN KỲ CŨ NHẤT)
  var drawRows = [];
  var matchColors = [];

  for (var k = todayDraws.length - 1; k >= 0; k--) {
    var cur = todayDraws[k];
    var prevTotal = (k > 0) ? todayDraws[k - 1].total : 10;
    var predSumK = getBestPredictedSumForState(prevTotal);
    var comboK = BEST_DICE_COMBO[predSumK] || [2, 3, 5];

    var actualDiceStr = cur.d1 + " - " + cur.d2 + " - " + cur.d3 + " (Tổng " + cur.total + ")";
    var matchText = "";
    var isHit = (cur.total === predSumK);
    if (isHit) {
      matchText = "🎯 Trúng Tổng";
    } else {
      var diff = cur.total - predSumK;
      matchText = "Lệch " + (diff > 0 ? "+" : "") + diff;
    }

    var dayRateStr = totalTodayDraws > 0 ?
      ((dailyCounts[cur.total] / totalTodayDraws) * 100).toFixed(1) + "% (" + dailyCounts[cur.total] + "/" + totalTodayDraws + " lần)" : "0%";

    var drawTimeStr = getDrawTime(cur.time, cur.slot, k + 1);

    drawRows.push([
      "#" + cur.draw_id,
      drawTimeStr,
      comboK[0],
      comboK[1],
      comboK[2],
      predSumK,
      actualDiceStr,
      matchText,
      dayRateStr
    ]);

    matchColors.push(isHit ? "#15803D" : "#475569");
  }

  if (drawRows.length > 0) {
    var range = sheet.getRange(26, 1, drawRows.length, 9);
    range.setValues(drawRows).setHorizontalAlignment("center");
    sheet.getRange(26, 1, drawRows.length, 1).setNumberFormat("@");

    // Tô màu nổi bật cột Đối chiếu (Cột H)
    for (var mIdx = 0; mIdx < matchColors.length; mIdx++) {
      var cell = sheet.getRange(26 + mIdx, 8);
      cell.setFontColor(matchColors[mIdx]);
      if (matchColors[mIdx] === "#15803D") {
        cell.setFontWeight("bold").setBackground("#DCFCE7");
      }
    }
  }

  // Căn chỉnh độ rộng các cột
  sheet.setColumnWidth(1, 140); // Mã kỳ
  sheet.setColumnWidth(2, 90);  // Giờ quay
  sheet.setColumnWidth(3, 80);  // Xúc xắc 1
  sheet.setColumnWidth(4, 80);  // Xúc xắc 2
  sheet.setColumnWidth(5, 80);  // Xúc xắc 3
  sheet.setColumnWidth(6, 110); // Tổng dự đoán
  sheet.setColumnWidth(7, 180); // Bộ số thực tế
  sheet.setColumnWidth(8, 140); // Kết quả đối chiếu
  sheet.setColumnWidth(9, 160); // Tỉ lệ trong ngày
}

// -------------------------------------------------------------------------
// 7. WEBHOOK DOPOST (NHẬN DỮ LIỆU TỰ ĐỘNG TỪ GITHUB ACTIONS HOẶC ROBOT)
// -------------------------------------------------------------------------
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "No data" }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    var payload = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
    sheet.setName("Chi tiết");

    var records = payload.records || (payload.record ? [payload.record] : []);
    var rowsToAppend = [];
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      if (r && r.draw_id) {
        var rId = String(r.draw_id).replace("#", "").trim().padStart(7, "0");
        rowsToAppend.push([
          rId,
          r.date || "",
          r.time || "",
          Number(r.slot_in_day || 0),
          Number(r.d1 || 0),
          Number(r.d2 || 0),
          Number(r.d3 || 0),
          Number(r.total || (Number(r.d1||0) + Number(r.d2||0) + Number(r.d3||0))),
          r.result || (r.d1 + " " + r.d2 + " " + r.d3 + " " + r.total)
        ]);
      }
    }
    if (rowsToAppend.length > 0) {
      sheet.getRange(sheet.getLastRow() + 1, 1, rowsToAppend.length, 9).setValues(rowsToAppend);
      updateStatsAndChartsSheet();
      updatePredictionSheet();
    }
    return ContentService.createTextOutput(JSON.stringify({ status: "ok", count: rowsToAppend.length }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", msg: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet() {
  return ContentService.createTextOutput("Bingo18 Pro Automation & Prediction System is Active!")
    .setMimeType(ContentService.MimeType.TEXT);
}
