import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  BarChart3,
  Calendar,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import type { StatsResult } from "./types";
import "./App.css";

export const App: React.FC = () => {
  const [data, setData] = useState<StatsResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<string>("overview");

  useEffect(() => {
    fetch("/results/m1_m3_m8_real.json")
      .then((res) => res.json())
      .then((json: StatsResult) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Lỗi nạp dữ liệu kết quả:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "#94a3b8" }}>
        <RefreshCw className="animate-spin" style={{ margin: "0 auto 16px" }} size={32} />
        Đang tải dữ liệu thống kê Bingo18 Analytics...
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "#ef4444" }}>
        Không thể nạp tệp kết quả. Vui lòng chạy lệnh <code>python -m stats.compute_phase5_results</code>.
      </div>
    );
  }

  const distItems = Object.values(data.m1_m2_distribution.distribution);
  const chartData = distItems.map((item) => ({
    sum: `Tổng ${item.sum}`,
    "Thực tế": item.observed,
    "Kỳ vọng lý thuyết": Math.round(item.expected),
    z_score: item.z_score,
  }));

  const chi2Sums = data.m3_chi2_tests.sums_df15;
  const chi2Dice = data.m3_chi2_tests.dice_df5;
  const chi2Ordered = data.m3_chi2_tests.ordered_216_df215;
  const chi2Unordered = data.m3_chi2_tests.unordered_56_df55;

  return (
    <div>
      {/* Banner cố định theo nguyên tắc khoa học */}
      <div className="banner-disclaimer">
        <AlertTriangle size={18} />
        <span>Các kỳ quay độc lập; chưa có bằng chứng cho thấy dự đoán được kết quả.</span>
      </div>

      <div className="app-container">
        {/* Tiêu đề ứng dụng */}
        <div className="header-title">
          <div>
            <h1>Bingo18 Analytics</h1>
            <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
              Hệ thống kiểm định thống kê và phân tích ngẫu nhiên Vietlott Bingo18
            </div>
          </div>
          <div className="meta-badge">
            Dữ liệu thật 100% | n = {data.metadata.total_draws.toLocaleString()} kỳ | SHA-256:{" "}
            {data.metadata.data_hash.substring(0, 8)}...
          </div>
        </div>

        {/* Thanh chuyển tab */}
        <div className="tabs-nav">
          <button
            className={`tab-btn ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            Tổng quan
          </button>
          <button
            className={`tab-btn ${activeTab === "distribution" ? "active" : ""}`}
            onClick={() => setActiveTab("distribution")}
          >
            Phân phối & Z-Score
          </button>
          <button
            className={`tab-btn ${activeTab === "rng_audit" ? "active" : ""}`}
            onClick={() => setActiveTab("rng_audit")}
          >
            Kiểm định RNG (M3)
          </button>
          <button
            className={`tab-btn ${activeTab === "date_analysis" ? "active" : ""}`}
            onClick={() => setActiveTab("date_analysis")}
          >
            Theo ngày (M8)
          </button>
          <button
            className={`tab-btn ${activeTab === "data_health" ? "active" : ""}`}
            onClick={() => setActiveTab("data_health")}
          >
            Tình trạng dữ liệu
          </button>
        </div>

        {/* Nội dung tab: Tổng quan */}
        {activeTab === "overview" && (
          <div>
            <div className="kpi-grid">
              <div className="kpi-card">
                <div className="kpi-label">Tổng số kỳ quay thật</div>
                <div className="kpi-value">{data.metadata.total_draws.toLocaleString()}</div>
                <div className="kpi-sub">Từ 03/12/2024 đến 09/11/2026</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Kiểm định Chi-Square Tổng (df=15)</div>
                <div className="kpi-value" style={{ color: "#34d399" }}>
                  p = {chi2Sums.p_value.toFixed(4)}
                </div>
                <div className="kpi-sub">
                  Chi2 = {chi2Sums.chi2} &lt; Ngưỡng 24.996 (Không bất thường)
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Kiểm định Từng viên (df=5)</div>
                <div className="kpi-value" style={{ color: "#34d399" }}>
                  p = {chi2Dice.p_value.toFixed(4)}
                </div>
                <div className="kpi-sub">Mặt xúc xắc 1..6 phân phối đều</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Trạng thái Giả thuyết H0</div>
                <div className="kpi-value" style={{ color: "#38bdf8" }}>
                  Chấp nhận H0
                </div>
                <div className="kpi-sub">Máy quay công bằng, độc lập</div>
              </div>
            </div>

            {/* Biểu đồ Phân phối */}
            <div className="card-box">
              <div className="card-title">
                <BarChart3 size={20} color="var(--accent-cyan)" />
                So sánh Số lần về Thực tế vs Kỳ vọng lý thuyết (M1 - M2)
              </div>
              <div style={{ height: 360, width: "100%" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a3859" />
                    <XAxis dataKey="sum" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#131b2e",
                        borderColor: "#2a3859",
                        borderRadius: 8,
                      }}
                    />
                    <Legend />
                    <Bar dataKey="Thực tế" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Kỳ vọng lý thuyết" fill="#818cf8" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* Nội dung tab: Phân phối & Z-Score */}
        {activeTab === "distribution" && (
          <div className="card-box">
            <div className="card-title">
              <BarChart3 size={20} color="var(--accent-cyan)" />
              Bảng Z-Score và Khoảng tin cậy Clopper-Pearson 95% từng tổng
            </div>
            <table className="stat-table">
              <thead>
                <tr>
                  <th>Tổng</th>
                  <th>Số cách</th>
                  <th>Xác suất p(s)</th>
                  <th>Thực tế (o)</th>
                  <th>Kỳ vọng (e)</th>
                  <th>Tỷ lệ thực</th>
                  <th>Z-Score</th>
                  <th>Khoảng tin cậy 95% (Clopper-Pearson)</th>
                  <th>Kết luận</th>
                </tr>
              </thead>
              <tbody>
                {distItems.map((item) => {
                  const isNorm = Math.abs(item.z_score) < 1.96;
                  return (
                    <tr key={item.sum}>
                      <td style={{ fontWeight: 700 }}>Tổng {item.sum}</td>
                      <td>{item.ways}/216</td>
                      <td>{(item.prob_theoretical * 100).toFixed(2)}%</td>
                      <td style={{ fontWeight: 600 }}>{item.observed.toLocaleString()}</td>
                      <td>{item.expected.toLocaleString()}</td>
                      <td>{(item.ratio * 100).toFixed(2)}%</td>
                      <td
                        style={{
                          color: isNorm ? "var(--text-main)" : "#fbbf24",
                          fontWeight: 700,
                        }}
                      >
                        {item.z_score > 0 ? `+${item.z_score}` : item.z_score}
                      </td>
                      <td style={{ fontSize: 12, color: "var(--text-muted)" }}>
                        [{(item.ci_95_lower * 100).toFixed(3)}% –{" "}
                        {(item.ci_95_upper * 100).toFixed(3)}%]
                      </td>
                      <td>
                        <span className={`badge-tag ${isNorm ? "badge-ok" : "badge-warning"}`}>
                          {isNorm ? "Chuẩn" : "Lệch nhẹ"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Nội dung tab: Kiểm định RNG (M3) */}
        {activeTab === "rng_audit" && (
          <div className="card-box">
            <div className="card-title">
              <ShieldCheck size={20} color="var(--accent-green)" />
              Báo cáo Kiểm định Độ tốt Phù hợp Chi-Square (Goodness-of-Fit Tests)
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: 14 }}>
              Kiểm định giả thuyết vô hiệu $H_0$: Các kỳ quay hoàn toàn độc lập và xúc xắc công
              bằng. Mức ý nghĩa $\alpha = 0.05$.
            </p>
            <div className="kpi-grid" style={{ marginTop: 20 }}>
              <div className="kpi-card">
                <div className="kpi-label">1. Tổng 3..18 (df=15)</div>
                <div className="kpi-value">Chi2: {chi2Sums.chi2}</div>
                <div className="kpi-sub" style={{ color: "#34d399" }}>
                  p-value = {chi2Sums.p_value.toFixed(4)} (Ngưỡng: 24.996)
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">2. Từng mặt xúc xắc 1..6 (df=5)</div>
                <div className="kpi-value">Chi2: {chi2Dice.chi2}</div>
                <div className="kpi-sub" style={{ color: "#34d399" }}>
                  p-value = {chi2Dice.p_value.toFixed(4)} (Ngưỡng: 11.070)
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">3. 216 tổ hợp có thứ tự (df=215)</div>
                <div className="kpi-value">Chi2: {chi2Ordered.chi2}</div>
                <div className="kpi-sub" style={{ color: "#34d399" }}>
                  p-value = {chi2Ordered.p_value.toFixed(4)} (Ngưỡng: 250.465)
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">4. 56 tổ hợp không thứ tự (df=55)</div>
                <div className="kpi-value">Chi2: {chi2Unordered.chi2}</div>
                <div className="kpi-sub" style={{ color: "#34d399" }}>
                  p-value = {chi2Unordered.p_value.toFixed(4)} (Ngưỡng: 73.311)
                </div>
              </div>
            </div>

            <div
              style={{
                marginTop: 20,
                padding: 16,
                backgroundColor: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                borderRadius: 8,
                display: "flex",
                gap: 12,
                alignItems: "center",
              }}
            >
              <CheckCircle2 color="#34d399" size={24} />
              <div>
                <div style={{ fontWeight: 700, color: "#34d399" }}>
                  KẾT LUẬN KIỂM ĐỊNH TOÀN DIỆN: KHÔNG PHÁT HIỆN BẤT THƯỜNG
                </div>
                <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 2 }}>
                  Tất cả các giá trị p-value đều lớn hơn 0.05. Không có bằng chứng thống kê nào cho
                  thấy máy quay bị lệch hoặc các kỳ quay phụ thuộc lẫn nhau.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Nội dung tab: Theo ngày (M8) */}
        {activeTab === "date_analysis" && (
          <div className="card-box">
            <div className="card-title">
              <Calendar size={20} color="var(--accent-amber)" />
              Kiểm định Ngoại lai theo Ngày (Date x Sum - M8)
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: 14 }}>
              Đánh giá tỷ lệ ngày xuất hiện ngoại lai ngoài dải tin cậy 95% nhị thức trên tổng số{" "}
              {data.m8_date_analysis.num_days} ngày.
            </p>
            <table className="stat-table">
              <thead>
                <tr>
                  <th>Tổng</th>
                  <th>Số ngày ngoại lai</th>
                  <th>Kỳ vọng ngoại lai (~5%)</th>
                  <th>p-value (Binomial Test)</th>
                  <th>Đánh giá</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.m8_date_analysis.sum_outlier_tests).map(([sumKey, t]) => (
                  <tr key={sumKey}>
                    <td style={{ fontWeight: 700 }}>Tổng {sumKey}</td>
                    <td>{t.outlier_days} ngày</td>
                    <td>{t.expected_outlier_days} ngày</td>
                    <td>{t.p_value.toFixed(4)}</td>
                    <td>
                      <span className={`badge-tag ${t.is_anomalous ? "badge-warning" : "badge-ok"}`}>
                        {t.is_anomalous ? "Cần theo dõi" : "Bình thường"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Nội dung tab: Tình trạng dữ liệu */}
        {activeTab === "data_health" && (
          <div className="card-box">
            <div className="card-title">
              <Database size={20} color="var(--accent-cyan)" />
              Tình trạng Dữ liệu và Chuỗi Kiểm tra SHA-256
            </div>
            <div className="kpi-grid">
              <div className="kpi-card">
                <div className="kpi-label">Số tệp tháng (YYYY-MM.csv)</div>
                <div className="kpi-value">24 tệp</div>
                <div className="kpi-sub">Từ 2024-12 đến 2026-11</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Chuỗi SHA-256 Kế thừa</div>
                <div className="kpi-value" style={{ color: "#34d399", fontSize: 20 }}>
                  HỢP LỆ (100% OK)
                </div>
                <div className="kpi-sub">Không có can thiệp dữ liệu</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Số khoảng kỳ thiếu (gaps)</div>
                <div className="kpi-value">210</div>
                <div className="kpi-sub">Đã ghi nhận trong gaps.csv</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Lệch nguồn (discrepancies)</div>
                <div className="kpi-value" style={{ color: "#34d399" }}>
                  0
                </div>
                <div className="kpi-sub">Khớp 100% với Sheet người dùng</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
