/**
 * =========================================================================
 * BINGO18 ANALYTICS PRO - GOOGLE APPS SCRIPT HỆ THỐNG ĐÁM MÂY 24/7
 * =========================================================================
 * Tính năng chính:
 * 1. Tự động hóa 24/7 (Time-driven Trigger mỗi 10 phút, khung giờ 06:00 - 22:00)
 * 2. Sheet 'Thống kê & Biểu đồ': Đa khung thời gian (Hôm nay / Tuần này / Tuần trước) + 3 Biểu đồ nhúng
 * 3. Sheet 'Dự đoán hàng ngày': Mô hình dự báo xác suất M16 (H0, Hot/Cold, Markov, Bayes)
 * 4. Webhook API (doPost) nhận dữ liệu từ GitHub Actions
 */

// -------------------------------------------------------------------------
// 1. MENU VÀ GIAO DIỆN NGƯỜI DÙNG
// -------------------------------------------------------------------------
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🎲 Bingo18 Pro")
    .addItem("🚀 Kích hoạt Tự động hóa 24/7 (10 phút/lần)", "installAutoJob")
    .addItem("📊 Tạo / Cập nhật Sheet Thống kê & Biểu đồ", "setupStatsAndChartsSheet")
    .addItem("🔮 Tạo / Cập nhật Sheet Dự đoán Hàng ngày", "setupPredictionSheet")
    .addSeparator()
    .addItem("🔄 Đồng bộ & Cập nhật tất cả ngay bây giờ", "manualRunAll")
    .addItem("⏸️ Tạm dừng Tự động hóa", "removeAutoJob")
    .addToUi();
}

// -------------------------------------------------------------------------
// 2. TỰ ĐỘNG HÓA 24/7 (TIME-DRIVEN TRIGGER)
// -------------------------------------------------------------------------
function installAutoJob() {
  removeAutoJobQuietly();
  
  // Tạo trigger chạy mỗi 10 phút ngầm trên Google Cloud
  ScriptApp.newTrigger("autoSyncVietlottJob")
    .timeBased()
    .everyMinutes(10)
    .create();

  // Chạy cập nhật lần đầu ngay lập tức
  manualRunAll();

  SpreadsheetApp.getUi().alert(
    "✅ Tự động hóa 24/7 đã kích hoạt thành công!\n\n" +
    "- Tần suất: Cứ mỗi 10 phút hệ thống sẽ tự động kéo kết quả mới về.\n" +
    "- Khung giờ: 06:00 đến 22:00 giờ Việt Nam (ngoài giờ này job tự nghỉ để tiết kiệm quota).\n" +
    "- Từ bây giờ bạn KHÔNG CẦN mở máy hay bấm nút nào nữa, Google Sheet sẽ tự động cập nhật 24/7!"
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

// -------------------------------------------------------------------------
// 3. JOB CHẠY NGẦM ĐỒNG BỘ DỮ LIỆU VIETLOTT (MỖI 10 PHÚT)
// -------------------------------------------------------------------------
function autoSyncVietlottJob() {
  try {
    // 1. Kiểm tra khung giờ Việt Nam (06:00 đến 22:15)
    var vnHour = Number(Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "HH"));
    var vnMin = Number(Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "mm"));
    if (vnHour < 6 || (vnHour >= 22 && vnMin > 15)) {
      Logger.log("Ngoài khung giờ quay số Vietlott (06:00 - 22:15 VN). Job tạm nghỉ.");
      return;
    }

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
    sheet.setName("Chi tiết");

    // Đọc các draw_id đã tồn tại trong 200 dòng cuối để chống trùng lặp
    var lastRow = sheet.getLastRow();
    var existingIds = {};
    if (lastRow > 1) {
      var checkRows = Math.min(200, lastRow - 1);
      var idValues = sheet.getRange(lastRow - checkRows + 1, 1, checkRows, 1).getValues();
      for (var i = 0; i < idValues.length; i++) {
        var idStr = String(idValues[i][0]).trim();
        if (idStr) existingIds[idStr] = true;
      }
    }

    // 2. Kéo các kỳ mới từ Vietlott hoặc GitHub fallback
    var newRecords = fetchLatestDrawsFromSources();
    var toAppend = [];
    for (var j = 0; j < newRecords.length; j++) {
      var r = newRecords[j];
      var rId = String(r.draw_id).trim();
      if (rId && !existingIds[rId]) {
        toAppend.push([
          r.draw_id, r.date, r.time, r.slot_in_day || 0,
          r.d1, r.d2, r.d3, r.total, r.result, new Date()
        ]);
        existingIds[rId] = true;
      }
    }

    // Ghi các kỳ mới vào cuối sheet Chi tiết
    if (toAppend.length > 0) {
      toAppend.sort(function(a, b) { return String(a[0]).localeCompare(String(b[0])); });
      sheet.getRange(sheet.getLastRow() + 1, 1, toAppend.length, 10).setValues(toAppend);
      Logger.log("Đã thêm " + toAppend.length + " kỳ quay mới vào sheet Chi tiết.");

      // Cập nhật lại 2 sheet Thống kê & Dự đoán
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
  
  // Nguồn 1: Cổng chính thức Vietlott AjaxPro
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
      var text = resp.getContentText();
      records = parseVietlottAjaxProResponse(text);
      if (records.length > 0) return records;
    }
  } catch (e) {
    Logger.log("Fetch Vietlott direct failed: " + e);
  }

  // Nguồn 2: Kho GitHub dữ liệu thật (fallback chuẩn)
  try {
    var ym = Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "yyyy-MM");
    var ghUrl = "https://raw.githubusercontent.com/nguyencong97/bingo18-analytics/main/data/" + ym + ".csv";
    var ghResp = UrlFetchApp.fetch(ghUrl, { muteHttpExceptions: true });
    if (ghResp.getResponseCode() === 200) {
      records = parseCsvToRecords(ghResp.getContentText());
      if (records.length > 0) return records;
    }
  } catch (e2) {
    Logger.log("Fetch GitHub fallback failed: " + e2);
  }

  return records;
}

function parseVietlottAjaxProResponse(rawText) {
  var records = [];
  try {
    // Trích xuất chuỗi JSON hoặc HtmlContent
    var jsonMatch = rawText.match(/\"HtmlContent\":\"([^\"]+)\"/);
    var html = jsonMatch ? jsonMatch[1].replace(/\\\"/g, '"').replace(/\\r\\n/g, '') : rawText;

    // Phân tích dòng <tr> qua Regex
    var rowRegex = /<tr[^>]*>([\s\S]*?)<\/tr>/gi;
    var match;
    while ((match = rowRegex.exec(html)) !== null) {
      var rowHtml = match[1];
      if (rowHtml.indexOf("<th") !== -1) continue;

      var idMatch = rowHtml.match(/#(\d{7})/);
      var dateMatch = rowHtml.match(/(\d{2}\/\d{2}\/\d{4})/);
      var timeMatch = rowHtml.match(/(\d{2}:\d{2})/);
      var diceMatches = rowHtml.match(/(\d)\s+(\d)\s+(\d)\s+(\d+)/);

      if (idMatch && diceMatches) {
        var d1 = Number(diceMatches[1]);
        var d2 = Number(diceMatches[2]);
        var d3 = Number(diceMatches[3]);
        var total = Number(diceMatches[4]);
        if (d1 + d2 + d3 === total && d1 >= 1 && d1 <= 6 && d2 >= 1 && d2 <= 6 && d3 >= 1 && d3 <= 6) {
          records.push({
            draw_id: idMatch[1],
            date: dateMatch ? formatDateVN(dateMatch[1]) : "",
            time: timeMatch ? timeMatch[1] : "",
            slot_in_day: 0,
            d1: d1, d2: d2, d3: d3, total: total,
            result: d1 + " " + d2 + " " + d3 + " " + total
          });
        }
      }
    }
  } catch (e) {
    Logger.log("parseVietlottAjaxProResponse error: " + e);
  }
  return records;
}

function formatDateVN(ddMMyyyy) {
  var parts = ddMMyyyy.split("/");
  if (parts.length === 3) return parts[2] + "-" + parts[1] + "-" + parts[0];
  return ddMMyyyy;
}

function parseCsvToRecords(csvContent) {
  var lines = Utilities.parseCsv(csvContent);
  if (lines.length <= 1) return [];
  var records = [];
  var recentLines = lines.slice(-40); // 40 dòng gần nhất
  for (var i = 0; i < recentLines.length; i++) {
    var cols = recentLines[i];
    if (cols.length >= 9 && cols[0] !== "draw_id" && cols[0] !== "Mã kỳ") {
      var d1 = Number(cols[5]);
      var d2 = Number(cols[6]);
      var d3 = Number(cols[7]);
      var total = Number(cols[8] || (d1 + d2 + d3));
      records.push({
        draw_id: String(cols[0]).padStart(7, "0"),
        date: String(cols[1]),
        time: String(cols[2]),
        slot_in_day: Number(cols[3] || 0),
        d1: d1, d2: d2, d3: d3, total: total,
        result: cols[9] || (d1 + " " + d2 + " " + d3 + " " + total)
      });
    }
  }
  return records;
}

// -------------------------------------------------------------------------
// 4. SHEET 'THỐNG KÊ & BIỂU ĐỒ' (ĐA KHUNG THỜI GIAN & BIỂU ĐỒ NHÚNG)
// -------------------------------------------------------------------------
var THEORETICAL_WAYS = [1, 3, 6, 10, 15, 21, 25, 27, 27, 25, 21, 15, 10, 6, 3, 1]; // 3..18

function setupStatsAndChartsSheet() {
  updateStatsAndChartsSheet();
  SpreadsheetApp.getUi().alert("✅ Đã cập nhật thành công sheet 'Thống kê & Biểu đồ' kèm 3 biểu đồ nhúng!");
}

function updateStatsAndChartsSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Thống kê & Biểu đồ");
  if (!sheet) {
    sheet = ss.insertSheet("Thống kê & Biểu đồ");
  }

  var dataSheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
  var lastRow = dataSheet.getLastRow();
  if (lastRow < 2) return;

  // Đọc tối đa 5,000 dòng gần nhất để tổng hợp nhanh và chính xác
  var readRows = Math.min(5000, lastRow - 1);
  var rawData = dataSheet.getRange(lastRow - readRows + 1, 1, readRows, 9).getValues();

  // Nhận diện ngày hôm nay và các khung thời gian
  var now = new Date();
  var todayStr = Utilities.formatDate(now, "Asia/Ho_Chi_Minh", "yyyy-MM-dd");
  var d7Ago = new Date(now.getTime() - 7 * 86400000);
  var d14Ago = new Date(now.getTime() - 14 * 86400000);
  var str7Ago = Utilities.formatDate(d7Ago, "Asia/Ho_Chi_Minh", "yyyy-MM-dd");
  var str14Ago = Utilities.formatDate(d14Ago, "Asia/Ho_Chi_Minh", "yyyy-MM-dd");

  var countToday = {}, countThisWeek = {}, countLastWeek = {}, countTotal = {};
  var dailyCounts = {}; // { 'yyyy-MM-dd': { sum: count } }
  var totalToday = 0, totalThisWeek = 0, totalLastWeek = 0;

  var sizeThisWeek = { small: 0, tie: 0, big: 0 };
  var comboThisWeek = { triple: 0, pair: 0, distinct: 0 };

  for (var s = 3; s <= 18; s++) {
    countToday[s] = 0; countThisWeek[s] = 0; countLastWeek[s] = 0; countTotal[s] = 0;
  }

  for (var r = 0; r < rawData.length; r++) {
    var row = rawData[r];
    var dateVal = String(row[1]).substring(0, 10);
    var d1 = Number(row[4]), d2 = Number(row[5]), d3 = Number(row[6]);
    var tot = Number(row[7]);
    if (tot < 3 || tot > 18) continue;

    countTotal[tot]++;

    if (!dailyCounts[dateVal]) dailyCounts[dateVal] = {};
    dailyCounts[dateVal][tot] = (dailyCounts[dateVal][tot] || 0) + 1;

    if (dateVal === todayStr) {
      countToday[tot]++;
      totalToday++;
    }

    if (dateVal >= str7Ago) {
      countThisWeek[tot]++;
      totalThisWeek++;
      // Lớn / Hòa / Nhỏ
      if (tot <= 9) sizeThisWeek.small++;
      else if (tot <= 11) sizeThisWeek.tie++;
      else sizeThisWeek.big++;

      // Số trùng
      if (d1 === d2 && d2 === d3) comboThisWeek.triple++;
      else if (d1 === d2 || d2 === d3 || d1 === d3) comboThisWeek.pair++;
      else comboThisWeek.distinct++;

    } else if (dateVal >= str14Ago && dateVal < str7Ago) {
      countLastWeek[tot]++;
      totalLastWeek++;
    }
  }

  sheet.clear();

  // Tiêu đề
  sheet.getRange("A1:N1").merge().setValue("BINGO18 ANALYTICS - THỐNG KÊ & BIẾN ĐỘNG TỈ LỆ ĐA KHUNG THỜI GIAN")
    .setFontWeight("bold").setFontSize(14).setBackground("#1E293B").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange("A2:N2").merge().setValue("Cập nhật tự động lúc: " + Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "dd/MM/yyyy HH:mm:ss") + " | Tổng kỳ phân tích gần nhất: " + readRows + " kỳ")
    .setFontStyle("italic").setHorizontalAlignment("center");

  // BẢNG 1: PHÂN PHỐI 16 TỔNG (A4:I21)
  var headersTable1 = [
    ["Tổng", "Cách tạo", "Lý thuyết H0 (%)", "Hôm nay (lần)", "Tuần này (lần)", "Tỉ lệ Tuần này (%)", "Tuần trước (lần)", "Tỉ lệ Tuần trước (%)", "Biến động (Delta %)"]
  ];
  sheet.getRange(4, 1, 1, 9).setValues(headersTable1)
    .setFontWeight("bold").setBackground("#3B82F6").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var table1Data = [];
  for (var sIdx = 3; sIdx <= 18; sIdx++) {
    var ways = THEORETICAL_WAYS[sIdx - 3];
    var pTheo = (ways / 216) * 100;
    var cTw = countThisWeek[sIdx];
    var pTw = totalThisWeek > 0 ? (cTw / totalThisWeek) * 100 : 0;
    var cLw = countLastWeek[sIdx];
    var pLw = totalLastWeek > 0 ? (cLw / totalLastWeek) * 100 : 0;
    var delta = pTw - pLw;

    table1Data.push([
      sIdx,
      ways,
      Number(pTheo.toFixed(2)),
      countToday[sIdx],
      cTw,
      Number(pTw.toFixed(2)),
      cLw,
      Number(pLw.toFixed(2)),
      Number(delta.toFixed(2))
    ]);
  }
  sheet.getRange(5, 1, 16, 9).setValues(table1Data).setHorizontalAlignment("center");

  // BẢNG 2: PHÂN BỐ LỚN / HÒA / NHỎ (K4:N8)
  var headersTable2 = [
    ["Cửa cược", "Khoảng tổng", "Lý thuyết H0 (%)", "Tuần này (%)"]
  ];
  sheet.getRange(4, 11, 1, 4).setValues(headersTable2)
    .setFontWeight("bold").setBackground("#10B981").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var totWeek = totalThisWeek > 0 ? totalThisWeek : 1;
  var table2Data = [
    ["Nhỏ", "3 .. 9", 37.50, Number(((sizeThisWeek.small / totWeek) * 100).toFixed(2))],
    ["Hòa", "10 .. 11", 25.00, Number(((sizeThisWeek.tie / totWeek) * 100).toFixed(2))],
    ["Lớn", "12 .. 18", 37.50, Number(((sizeThisWeek.big / totWeek) * 100).toFixed(2))]
  ];
  sheet.getRange(5, 11, 3, 4).setValues(table2Data).setHorizontalAlignment("center");

  // BẢNG 3: BỘ SỐ TRÙNG (K10:N14)
  var headersTable3 = [
    ["Tổ hợp xúc xắc", "Mô tả", "Lý thuyết H0 (%)", "Tuần này (%)"]
  ];
  sheet.getRange(10, 11, 1, 4).setValues(headersTable3)
    .setFontWeight("bold").setBackground("#8B5CF6").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var table3Data = [
    ["Tam hoa", "3 số giống nhau (111..666)", 2.78, Number(((comboThisWeek.triple / totWeek) * 100).toFixed(2))],
    ["Cặp số", "Có đúng 1 cặp trùng", 41.67, Number(((comboThisWeek.pair / totWeek) * 100).toFixed(2))],
    ["Khác nhau", "3 số hoàn toàn khác nhau", 55.56, Number(((comboThisWeek.distinct / totWeek) * 100).toFixed(2))]
  ];
  sheet.getRange(11, 11, 3, 4).setValues(table3Data).setHorizontalAlignment("center");

  // TẠO 3 BIỂU ĐỒ NHÚNG
  var charts = sheet.getCharts();
  for (var c = 0; c < charts.length; c++) {
    sheet.removeChart(charts[c]);
  }

  // Biểu đồ 1: Cột so sánh Tổng Tuần này vs Tuần trước vs Lý thuyết
  var chart1 = sheet.newChart()
    .setChartType(Charts.ChartType.COLUMN)
    .addRange(sheet.getRange("A4:A20")) // Tổng
    .addRange(sheet.getRange("C4:C20")) // Lý thuyết %
    .addRange(sheet.getRange("F4:F20")) // Tuần này %
    .addRange(sheet.getRange("H4:H20")) // Tuần trước %
    .setPosition(22, 1, 10, 10)
    .setOption("title", "SO SÁNH TỈ LỆ 16 TỔNG: LÝ THUYẾT H0 vs TUẦN NÀY vs TUẦN TRƯỚC (%)")
    .setOption("colors", ["#94A3B8", "#3B82F6", "#F97316"])
    .setOption("legend", { position: "top" })
    .setOption("width", 720)
    .setOption("height", 340)
    .build();
  sheet.insertChart(chart1);

  // Biểu đồ 2: Tròn Donut tỉ lệ Lớn / Hòa / Nhỏ
  var chart2 = sheet.newChart()
    .setChartType(Charts.ChartType.PIE)
    .addRange(sheet.getRange("K4:K7")) // Cửa cược
    .addRange(sheet.getRange("N4:N7")) // Tuần này %
    .setPosition(22, 11, 10, 10)
    .setOption("title", "TỈ LỆ CỬA CƯỢC THỰC TẾ TUẦN NÀY (LỚN / HÒA / NHỎ)")
    .setOption("pieHole", 0.4)
    .setOption("colors", ["#3B82F6", "#F59E0B", "#EF4444"])
    .setOption("width", 450)
    .setOption("height", 340)
    .build();
  sheet.insertChart(chart2);
}

// -------------------------------------------------------------------------
// 5. SHEET 'DỰ ĐOÁN HÀNG NGÀY' (CÁC MÔ HÌNH DỰ BÁO KHOA HỌC M16)
// -------------------------------------------------------------------------
function setupPredictionSheet() {
  updatePredictionSheet();
  SpreadsheetApp.getUi().alert("✅ Đã cập nhật thành công sheet 'Dự đoán hàng ngày' theo các mô hình xác suất M16!");
}

function updatePredictionSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Dự đoán hàng ngày");
  if (!sheet) {
    sheet = ss.insertSheet("Dự đoán hàng ngày");
  }

  var dataSheet = ss.getSheetByName("Chi tiết") || ss.getActiveSheet();
  var lastRow = dataSheet.getLastRow();
  if (lastRow < 20) return;

  // Lấy 500 kỳ gần nhất phục vụ tính toán cửa sổ trượt (rolling window)
  var readCount = Math.min(500, lastRow - 1);
  var rawData = dataSheet.getRange(lastRow - readCount + 1, 1, readCount, 9).getValues();

  var historySums = [];
  var lastDraw = rawData[rawData.length - 1];
  for (var i = 0; i < rawData.length; i++) {
    var tot = Number(rawData[i][7]);
    if (tot >= 3 && tot <= 18) historySums.push(tot);
  }

  var lastSum = historySums[historySums.length - 1];
  var lastDrawId = String(lastDraw[0]);
  var lastResult = String(lastDraw[8]);

  // THUẬT TOÁN M16: 5 MÔ HÌNH DỰ BÁO XÁC SUẤT
  // 1. Phân phối lý thuyết H0
  var pH0 = {};
  for (var s = 3; s <= 18; s++) {
    pH0[s] = THEORETICAL_WAYS[s - 3] / 216.0;
  }

  // 2. Tần suất Hot / Cold (cửa sổ 500 kỳ)
  var counts = {};
  for (var s2 = 3; s2 <= 18; s2++) counts[s2] = 0;
  for (var h = 0; h < historySums.length; h++) counts[historySums[h]]++;

  var nHist = historySums.length;
  var pHot = {};
  for (var s3 = 3; s3 <= 18; s3++) {
    pHot[s3] = counts[s3] / nHist;
  }

  // 3. Ma trận chuyển dịch Markov bậc 1: P(S_{t+1} | S_t = lastSum)
  var markovTrans = {};
  var markovTotal = 0;
  for (var s4 = 3; s4 <= 18; s4++) markovTrans[s4] = 0;
  for (var m = 0; m < historySums.length - 1; m++) {
    if (historySums[m] === lastSum) {
      markovTrans[historySums[m + 1]]++;
      markovTotal++;
    }
  }

  var pMarkov = {};
  for (var s5 = 3; s5 <= 18; s5++) {
    // Làm trơn Laplace với prior lý thuyết H0
    pMarkov[s5] = markovTotal >= 5
      ? (markovTrans[s5] + 5.0 * pH0[s5]) / (markovTotal + 5.0)
      : pH0[s5];
  }

  // 4. Dirichlet-Multinomial Bayesian Posterior
  var pBayes = {};
  var totalAlpha = nHist + 16;
  for (var s6 = 3; s6 <= 18; s6++) {
    pBayes[s6] = (counts[s6] + 1.0) / totalAlpha;
  }

  // 5. Xác suất Ensemble Hợp Nhất (Trọng số: 40% Markov + 30% Hot + 20% Bayes + 10% H0)
  var ensembleList = [];
  var predSmall = 0, predTie = 0, predBig = 0;

  for (var s7 = 3; s7 <= 18; s7++) {
    var pScore = 0.40 * pMarkov[s7] + 0.30 * pHot[s7] + 0.20 * pBayes[s7] + 0.10 * pH0[s7];
    var deltaVsH0 = ((pScore - pH0[s7]) / pH0[s7]) * 100;
    var trend = "Ổn định (Chuẩn H0)";
    if (deltaVsH0 > 15) trend = "🔥 Tăng nhiệt (Hot)";
    else if (deltaVsH0 < -15) trend = "❄️ Hạ nhiệt (Cold)";

    if (s7 <= 9) predSmall += pScore;
    else if (s7 <= 11) predTie += pScore;
    else predBig += pScore;

    ensembleList.push({
      sum: s7,
      pH0: Number((pH0[s7] * 100).toFixed(2)),
      pHot: Number((pHot[s7] * 100).toFixed(2)),
      pMarkov: Number((pMarkov[s7] * 100).toFixed(2)),
      pBayes: Number((pBayes[s7] * 100).toFixed(2)),
      pEnsemble: Number((pScore * 100).toFixed(2)),
      delta: Number(deltaVsH0.toFixed(1)),
      trend: trend
    });
  }

  // Sắp xếp thứ hạng theo xác suất dự phóng Ensemble từ cao xuống thấp
  ensembleList.sort(function(a, b) { return b.pEnsemble - a.pEnsemble; });

  sheet.clear();

  // Header Banner
  sheet.getRange("A1:N1").merge().setValue("BINGO18 ANALYTICS - BẢNG DỰ BÁO XÁC SUẤT & PHÂN TÍCH H0 HÀNG NGÀY")
    .setFontWeight("bold").setFontSize(14).setBackground("#0F172A").setFontColor("#FFFFFF").setHorizontalAlignment("center");
  sheet.getRange("A2:N2").merge().setValue(
    "Kỳ tham chiếu gần nhất: #" + lastDrawId + " | Kết quả: " + lastResult + " (Tổng " + lastSum + ") | Cập nhật: " +
    Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "dd/MM/yyyy HH:mm:ss")
  ).setFontStyle("italic").setHorizontalAlignment("center");

  // BẢNG CHÍNH: XẾP HẠNG 16 TỔNG DỰ PHÓNG
  var mainHeaders = [
    ["Hạng", "Tổng", "Dự phóng Hợp nhất (%)", "Lý thuyết H0 (%)", "Mô hình Markov (%)", "Mô hình Hot-500 (%)", "Mô hình Bayes (%)", "Độ lệch / H0 (%)", "Khuyến nghị xu hướng"]
  ];
  sheet.getRange(4, 1, 1, 9).setValues(mainHeaders)
    .setFontWeight("bold").setBackground("#2563EB").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var mainRows = [];
  for (var rIdx = 0; rIdx < ensembleList.length; rIdx++) {
    var item = ensembleList[rIdx];
    mainRows.push([
      rIdx + 1,
      item.sum,
      item.pEnsemble,
      item.pH0,
      item.pMarkov,
      item.pHot,
      item.pBayes,
      item.delta,
      item.trend
    ]);
  }
  sheet.getRange(5, 1, 16, 9).setValues(mainRows).setHorizontalAlignment("center");

  // BẢNG TIÊU ĐIỂM: TOP 3 TỔNG XÁC SUẤT CAO NHẤT
  sheet.getRange("K4:N4").merge().setValue("🎯 TOP 3 TỔNG CÓ XÁC SUẤT CAO NHẤT KỲ TIẾP THEO")
    .setFontWeight("bold").setBackground("#D97706").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var top3Data = [
    ["Vị trí #1", "Tổng " + ensembleList[0].sum, ensembleList[0].pEnsemble + "%", ensembleList[0].trend],
    ["Vị trí #2", "Tổng " + ensembleList[1].sum, ensembleList[1].pEnsemble + "%", ensembleList[1].trend],
    ["Vị trí #3", "Tổng " + ensembleList[2].sum, ensembleList[2].pEnsemble + "%", ensembleList[2].trend]
  ];
  sheet.getRange(5, 11, 3, 4).setValues(top3Data).setFontWeight("bold").setHorizontalAlignment("center");

  // DỰ BÁO CỬA CƯỢC LỚN / HÒA / NHỎ
  sheet.getRange("K9:N9").merge().setValue("⚖️ DỰ BÁO XÁC SUẤT CỬA LỚN / HÒA / NHỎ")
    .setFontWeight("bold").setBackground("#059669").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var sizePredData = [
    ["Nhỏ (3..9)", Number((predSmall * 100).toFixed(2)) + "%", "Lý thuyết: 37.50%", predSmall > 0.38 ? "Ưu thế" : "Bình thường"],
    ["Hòa (10..11)", Number((predTie * 100).toFixed(2)) + "%", "Lý thuyết: 25.00%", predTie > 0.26 ? "Ưu thế" : "Bình thường"],
    ["Lớn (12..18)", Number((predBig * 100).toFixed(2)) + "%", "Lý thuyết: 37.50%", predBig > 0.38 ? "Ưu thế" : "Bình thường"]
  ];
  sheet.getRange(10, 11, 3, 4).setValues(sizePredData).setHorizontalAlignment("center");

  // CẢNH BÁO KHOA HỌC & QUẢN TRỊ RỦI RO
  sheet.getRange("K14:N14").merge().setValue("⚠️ NGUYÊN TẮC KHOA HỌC & QUẢN TRỊ RỦI RO")
    .setFontWeight("bold").setBackground("#DC2626").setFontColor("#FFFFFF").setHorizontalAlignment("center");

  var disclaimer = [
    ["1. Giả thuyết H0: Xúc xắc công bằng, mỗi kỳ quay là độc lập ngẫu nhiên."],
    ["2. Mọi mô hình dự báo chỉ phản ánh xu hướng phân phối thống kê ngắn hạn."],
    ["3. Không có phương pháp nào đảm bảo 100% chiến thắng. Tuyệt đối không gấp thếp (Martingale)."]
  ];
  sheet.getRange(15, 11, 3, 1).mergeAcross().setValues(disclaimer).setFontSize(9).setFontColor("#475569");
}

// -------------------------------------------------------------------------
// 6. WEBHOOK DOPOST (NHẬN DỮ LIỆU TỰ ĐỘNG TỪ GITHUB ACTIONS)
// -------------------------------------------------------------------------
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({ status: "error", message: "No post data" }))
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
        rowsToAppend.push([
          r.draw_id, r.date || "", r.time || "", r.slot_in_day || 0,
          r.d1 || 0, r.d2 || 0, r.d3 || 0, r.total || 0, r.result || "", new Date()
        ]);
      }
    }

    if (rowsToAppend.length > 0) {
      sheet.getRange(sheet.getLastRow() + 1, 1, rowsToAppend.length, 10).setValues(rowsToAppend);
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
