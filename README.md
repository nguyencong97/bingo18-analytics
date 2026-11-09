# Bingo18 Analytics (Vietlott)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fnguyencong97%2Fbingo18-analytics)

Hệ thống thu thập dữ liệu thật 100% từ Vietlott Bingo18, lưu trữ tệp phẳng CSV (không database), phân tích thống kê và kiểm định khoa học (M1–M16) với giả thuyết vô hiệu $H_0$ (máy quay công bằng, các kỳ độc lập), mô phỏng null đối chứng và giao diện trực quan hóa tiếng Việt.

---

## 🚀 Triển Khai Nhanh Lên Vercel (1-Click)
Bấm vào nút **Deploy with Vercel** ở trên hoặc truy cập [Vercel New Project](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fnguyencong97%2Fbingo18-analytics) để xuất bản trang web Dashboard trực quan hoàn toàn miễn phí trong 30 giây (tên miền dạng `https://bingo18-analytics.vercel.app`).

---

## 🛡️ Nguyên Tắc Bất Khả Xâm Phạm

1. **DỮ LIỆU THẬT 100%**: Không làm giả, không nội suy, không tự điền kỳ thiếu, không làm tròn. Kỳ thiếu được ghi nhận minh bạch vào `data/gaps.csv`.
2. **CÁCH LY MÔ PHỎNG**: Dữ liệu mô phỏng đối chứng (null simulation) chỉ nằm trong `sim/` và luôn được gắn nhãn **"MÔ PHỎNG"** trên giao diện người dùng. Không bao giờ ghi vào `data/`.
3. **TRUY VẾT MINH BẠCH**: Mọi con số hiển thị truy vết từ nguồn gốc $\to$ snapshot thô $\to$ dòng CSV $\to$ hàm tính $\to$ mã băm SHA-256 kế thừa và seed.
4. **CẢNH BÁO BẢNG HỆ SỐ**: Hệ số thưởng chỉ lấy từ `config/payouts.json`. Nếu chưa có xác nhận chính thức từ người dùng (`verified: false`), UI luôn hiển thị banner cảnh báo.
5. **KIỂM ĐỊNH KHOA HỌC**: Không hứa hẹn dự đoán kỳ sau. $H_0$: máy quay công bằng, các kỳ độc lập. Mọi kết luận bất thường phải qua hiệu chỉnh đa so sánh Benjamini-Hochberg (FDR 5%). Nếu không có bằng chứng, UI hiển thị rõ *"không phát hiện bất thường"*.

---

## 📁 Cấu Trúc Thư Mục

```text
d:\vietlot/
├── config/
│   ├── payouts.json          # Bảng hệ số thưởng kèm cờ verified
│   └── settings.json         # Cấu hình crawler, rate limit, ngưỡng test
├── data/
│   ├── raw/YYYY/MM/DD/       # Snapshot thô nguyên bản từ Vietlott AjaxPro
│   ├── YYYY-MM.csv           # Dữ liệu chuẩn hóa từng tháng (append-only)
│   ├── all.csv               # Tệp hợp nhất toàn bộ kỳ quay (sắp theo draw_id)
│   ├── gaps.csv              # Nhật ký các khoảng kỳ khuyết thiếu
│   ├── discrepancies.csv     # Nhật ký sai lệch giữa các nguồn
│   ├── corrections.csv       # Nhật ký hiệu chỉnh có truy vết lý do
│   ├── checksums.txt         # Chuỗi mã băm SHA-256 kế thừa từng tháng
│   └── errors.csv            # Dòng dữ liệu vi phạm ràng buộc
├── fixtures/                 # Mẫu thật lấy từ vietlott.vn + STRUCTURE.md
├── crawler/                  # HTTP client, parser, storage, alerts
├── backfill/                 # Nạp dữ liệu lịch sử (user sheet + vietvudanh)
├── stats/                    # Các mô-đun toán học & thống kê M1 - M16
├── sim/                      # Mô phỏng Null đối chứng (M14)
├── results/                  # Kết quả JSON phục vụ kiểm định và Frontend
├── web/                      # Ứng dụng Frontend React + Vite + TypeScript
├── scripts/                  # Kịch bản chạy cron Linux và Task Scheduler Windows
└── tests/                    # Bộ 41 kiểm thử tự động chấp nhận (pytest)
```

---

## 📊 Tóm Tắt Kết Quả Kiểm Định (Trên 99,561 kỳ thật)

| Chỉ số / Kiểm định | Phép thử khoa học | Kết quả thực tế | Ngưỡng kiểm định | Kết luận |
| :--- | :--- | :--- | :--- | :--- |
| **M3: Tổng 3..18** | $\chi^2$ Goodness-of-Fit ($df=15$) | $\chi^2 = 7.9668$ | $p = 0.9251 > 0.05$ | **Công bằng (H0)** |
| **M3: Từng mặt 1..6** | $\chi^2$ Goodness-of-Fit ($df=5$) | $\chi^2 = 7.5576$ | $p = 0.1824 > 0.05$ | **Phân phối đều** |
| **M3: 216 tổ hợp có thứ tự** | $\chi^2$ Goodness-of-Fit ($df=215$) | $\chi^2 = 222.1592$ | $p = 0.3544 > 0.05$ | **Công bằng (H0)** |
| **M4: Độc lập giữa các viên** | Bảng $6 \times 6$ từng cặp ($df=25$) | $p > 0.10$ cả 3 cặp | $p > 0.05$ | **Độc lập hoàn toàn** |
| **M5: Lặp tổng kỳ sau** | Z-test so với $\sum p^2 = 0.09285$ | $p_{\text{obs}} = 0.09265$ | $z = -0.22, p = 0.82$ | **Không có bệt** |
| **M6: Tự tương quan chuỗi** | Ljung-Box test ($Q, df=50$) | $Q = 48.21$ | $p = 0.54 > 0.05$ | **Là nhiễu trắng** |
| **M6: Tính ngẫu nhiên Lớn/Nhỏ** | Wald-Wolfowitz Runs Test | $z = 0.45$ | $p = 0.65 > 0.05$ | **Ngẫu nhiên hoàn hảo** |
| **M11: Shannon Entropy** | Entropy chuỗi tổng thực tế | $H = 3.5982$ bits | Lý thuyết: $3.5984$ bits | **Độ hỗn loạn cực đại** |
| **M12: CUSUM Drift** | Cửa sổ trượt $W=5000$, bước $500$ | $\max \chi^2 = 26.4$ | Ngưỡng: $37.7$ | **Không có trôi dạt** |
| **M14: Mô phỏng Null (B=1000)** | Monte Carlo p-value thực nghiệm | $p_{\text{emp}} = 0.928$ | $928/1000 \ge \text{thật}$ | **Đồng dạng máy chuẩn** |
| **M16: So sánh dự báo** | Walk-forward Backtest vs Baseline | Diebold-Mariano test | Mọi mô hình $p_{\text{adj}} \ge 0.05$ | **Baseline thắng thế** |

---

## 🚀 Hướng Dẫn Cài Đặt & Vận Hành

### 1. Cài đặt môi trường Python
```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Chạy bộ kiểm thử tự động (41 tests)
```bash
python -m pytest tests/ -v
```

### 3. Chạy Crawler thu thập kỳ mới
```bash
python -m crawler.run
```

### 4. Kiểm tra tính toàn vẹn dữ liệu
```bash
python -m stats.integrity
```

### 5. Khởi chạy Giao diện Frontend
```bash
cd web
npm install
npm run dev
```

Truy cập: `http://localhost:5173` để trải nghiệm giao diện phân tích tiếng Việt với đầy đủ 8 chuyên mục trực quan hóa.

---

## 🌐 Hướng Dẫn Triển Khai Cloudflare Pages / GitHub Pages

1. Đóng gói ứng dụng web tĩnh:
   ```bash
   cd web
   npm run build
   ```
2. Thư mục `web/dist` là trang web tĩnh độc lập (Single Page App) có thể triển khai miễn phí 100% lên:
   - **Cloudflare Pages**: Kết nối kho Git, đặt Build command `npm run build`, Output directory `dist`.
   - **GitHub Pages**: Đẩy thư mục `dist` lên nhánh `gh-pages` hoặc dùng GitHub Actions kèm theo.
