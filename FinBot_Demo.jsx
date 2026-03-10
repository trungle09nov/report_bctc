import { useState, useEffect } from "react";

// ── HPG Q4/2025 Data (pre-calculated from both reports) ──────────────────────
const HPG_DATA = {
  company: "Tập đoàn Hòa Phát (HPG)",
  period: "Q4/2025",
  consolidated: {
    label: "Hợp nhất",
    metrics: {
      revenue: 40600,
      revenue_prev: 34491,
      net_profit: 3888,
      net_profit_prev: 2810,
      gross_margin: 15.2,
      gross_margin_prev: 13.8,
      operating_margin: 11.4,
      net_margin: 9.6,
      current_ratio: 1.42,
      quick_ratio: 0.87,
      debt_to_equity: 1.08,
      roe: 16.8,
      roa: 6.1,
      dso: 24.4,
      inventory_days: 117,
      total_assets: 257921,
      equity: 140477,
      inventory: 52828,
      cash: 8301,
    },
    flags: [
      { type: "WARNING", code: "AR_OUTPACE_REVENUE", msg: "Phải thu KH tăng +152% YoY, trong khi DT chỉ +17.7% — kiểm tra DSO" },
      { type: "INFO", code: "CAPEX_PROJECT_COMPLETED", msg: "TSCĐ tăng ~2x (67→133 nghìn tỷ) — Dung Quất 2 đã hoàn thành & đưa vào sử dụng" },
      { type: "INFO", code: "LARGE_VAT_REFUND_PENDING", msg: "VAT chờ hoàn thuế: 7.4 nghìn tỷ đồng — tồn đọng từ đầu tư CAPEX lớn" },
    ],
    segments: [
      { name: "Thép", revenue: 35400, profit: 3380, margin: 9.6, share: 87.2 },
      { name: "Nông nghiệp", revenue: 2050, profit: 402, margin: 19.6, share: 5.0 },
      { name: "BĐS", revenue: 1150, profit: 310, margin: 27.0, share: 2.8 },
    ],
    summary: "LNST đạt 3.888 tỷ (+38% YoY), được thúc đẩy bởi sản lượng thép thô tăng mạnh, giá vốn được kiểm soát tốt, và biên lợi nhuận gộp cải thiện từ 13.8% lên 15.2%. Dung Quất 2 chính thức hoàn thành đưa TSCĐ tăng gần gấp đôi.",
  },
  parent: {
    label: "Công ty mẹ (riêng lẻ)",
    metrics: {
      revenue: 126,
      revenue_prev: 166,
      net_profit: 5597,
      net_profit_prev: 2243,
      gross_margin: 6.8,
      net_margin: 4458,
      current_ratio: 3.71,
      quick_ratio: 3.66,
      debt_to_equity: 0.044,
      total_assets: 98671,
      equity: 94431,
      cash: 481,
      subsidiary_income: 5667,
    },
    flags: [
      { type: "INFO", code: "HOLDING_COMPANY_PATTERN", msg: "LNST cao (5.597 tỷ) chủ yếu từ lợi nhuận công ty con chuyển về (5.667 tỷ) — không phản ánh hoạt động trực tiếp" },
      { type: "INFO", code: "EQUITY_INVESTMENT_GROWTH", msg: "Đầu tư vào công ty con tăng từ 80.586 → 97.018 nghìn tỷ (+20.4%)" },
      { type: "WARNING", code: "SERVICE_REVENUE_DECLINE", msg: "Doanh thu dịch vụ giảm từ 165 tỷ → 125 tỷ (-24.3% YoY)" },
    ],
    summary: "Công ty mẹ thuần holding — 98.6% tài sản là đầu tư vào công ty con. LNST 5.597 tỷ (+149% YoY) hoàn toàn nhờ lợi nhuận con chuyển về. KHÔNG nên so sánh các chỉ số vận hành với báo cáo hợp nhất.",
  },
};

// ── Components ─────────────────────────────────────────────────────────────
const colors = {
  bg: "#0d1117",
  surface: "#161b22",
  surface2: "#21262d",
  border: "#30363d",
  accent: "#f78166",
  accentBlue: "#58a6ff",
  accentGreen: "#3fb950",
  accentYellow: "#d29922",
  accentPurple: "#bc8cff",
  text: "#e6edf3",
  textMuted: "#8b949e",
  textDim: "#484f58",
};

function Badge({ type }) {
  const map = {
    WARNING: { bg: "#3d2900", color: "#d29922", label: "⚠ Cảnh báo" },
    INFO: { bg: "#0d2149", color: "#58a6ff", label: "ℹ Lưu ý" },
    ALERT: { bg: "#3d0000", color: "#f78166", label: "🚨 Alert" },
  };
  const s = map[type] || map.INFO;
  return (
    <span style={{ background: s.bg, color: s.color, padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
      {s.label}
    </span>
  );
}

function MetricCard({ label, value, unit = "", prev, highlight }) {
  const growth = prev ? ((value - prev) / Math.abs(prev)) * 100 : null;
  const isPositive = growth >= 0;
  return (
    <div style={{
      background: colors.surface2,
      border: `1px solid ${highlight ? colors.accentBlue : colors.border}`,
      borderRadius: 8,
      padding: "14px 16px",
    }}>
      <div style={{ color: colors.textMuted, fontSize: 11, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ color: colors.text, fontSize: 20, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
        {typeof value === "number" && value > 1000
          ? (value / 1000).toFixed(1) + " nghìn tỷ"
          : typeof value === "number" && !Number.isInteger(value)
          ? value.toFixed(1) + unit
          : value + unit}
      </div>
      {growth !== null && (
        <div style={{ color: isPositive ? colors.accentGreen : colors.accent, fontSize: 12, marginTop: 4 }}>
          {isPositive ? "▲" : "▼"} {Math.abs(growth).toFixed(1)}% YoY
        </div>
      )}
    </div>
  );
}

function SegmentBar({ segments }) {
  const total = segments.reduce((s, x) => s + x.revenue, 0);
  const segColors = [colors.accentBlue, colors.accentGreen, colors.accentPurple];
  return (
    <div>
      <div style={{ display: "flex", height: 20, borderRadius: 6, overflow: "hidden", marginBottom: 10 }}>
        {segments.map((s, i) => (
          <div key={i} style={{ width: `${(s.revenue / total) * 100}%`, background: segColors[i] }} title={s.name} />
        ))}
      </div>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        {segments.map((s, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: segColors[i] }} />
            <span style={{ color: colors.text }}>{s.name}</span>
            <span style={{ color: colors.textMuted }}>{s.share}%</span>
            <span style={{ color: colors.accentGreen }}>biên {s.margin}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ArchitectureDiagram() {
  const layers = [
    {
      label: "CLIENT", color: colors.accentPurple,
      items: ["🌐 WebApp (React)", "🤖 Telegram Bot"],
    },
    {
      label: "API GATEWAY", color: colors.accentBlue,
      items: ["POST /upload", "POST /analyze", "POST /chat", "POST /compare"],
    },
    {
      label: "PROCESSING PIPELINE", color: colors.accentGreen,
      items: ["① Parser (PDF/MD → JSON)", "② Calculator (Python formulas)", "③ LLM Analyst (Claude API)"],
    },
    {
      label: "DATA LAYER", color: colors.accentYellow,
      items: ["PostgreSQL (structured)", "Redis (cache/session)", "S3 (raw files)"],
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {layers.map((layer, i) => (
        <div key={i}>
          <div style={{
            background: colors.surface2,
            border: `1px solid ${layer.color}40`,
            borderLeft: `3px solid ${layer.color}`,
            borderRadius: 6, padding: "10px 14px",
          }}>
            <div style={{ color: layer.color, fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", marginBottom: 6 }}>{layer.label}</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {layer.items.map((item, j) => (
                <span key={j} style={{
                  background: colors.surface, border: `1px solid ${colors.border}`,
                  borderRadius: 4, padding: "3px 10px", fontSize: 12, color: colors.text,
                }}>{item}</span>
              ))}
            </div>
          </div>
          {i < layers.length - 1 && (
            <div style={{ textAlign: "center", color: colors.textDim, fontSize: 18, lineHeight: "20px" }}>↓</div>
          )}
        </div>
      ))}
    </div>
  );
}

function TelegramPreview({ data }) {
  const d = data.consolidated;
  const lines = [
    { t: "header", v: `📊 ${data.company} — ${data.period}` },
    { t: "divider" },
    { t: "section", v: "📌 Tóm tắt" },
    { t: "text", v: d.summary },
    { t: "divider" },
    { t: "section", v: "📈 Kết quả chính" },
    { t: "metric", label: "Doanh thu thuần", v: "40.6 nghìn tỷ", delta: "+17.7% YoY", pos: true },
    { t: "metric", label: "Lợi nhuận sau thuế", v: "3.888 tỷ", delta: "+38% YoY", pos: true },
    { t: "metric", label: "Biên LN gộp", v: "15.2%", delta: "↑ từ 13.8%", pos: true },
    { t: "divider" },
    { t: "section", v: "⚠️ Điểm cần chú ý" },
    ...d.flags.map(f => ({ t: "flag", badge: f.type, v: f.msg })),
    { t: "divider" },
    { t: "footer", v: "💡 Dùng /ask để hỏi chi tiết" },
  ];

  return (
    <div style={{
      background: "#17212b", borderRadius: 12, padding: 16,
      fontFamily: "'Segoe UI', sans-serif", maxWidth: 400,
      border: `1px solid #2b5278`,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <div style={{ width: 36, height: 36, borderRadius: "50%", background: "#2481cc", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>📊</div>
        <div>
          <div style={{ color: "#fff", fontSize: 13, fontWeight: 600 }}>FinBot</div>
          <div style={{ color: "#708499", fontSize: 11 }}>online</div>
        </div>
      </div>
      <div style={{ background: "#1e2c3a", borderRadius: 10, padding: 12, display: "flex", flexDirection: "column", gap: 6 }}>
        {lines.map((line, i) => {
          if (line.t === "header") return <div key={i} style={{ color: "#fff", fontWeight: 700, fontSize: 14 }}>{line.v}</div>;
          if (line.t === "divider") return <hr key={i} style={{ border: "none", borderTop: "1px solid #2b3e52", margin: "2px 0" }} />;
          if (line.t === "section") return <div key={i} style={{ color: "#4eb2e0", fontWeight: 600, fontSize: 12 }}>{line.v}</div>;
          if (line.t === "text") return <div key={i} style={{ color: "#b0c4de", fontSize: 12, lineHeight: 1.5 }}>{line.v}</div>;
          if (line.t === "metric") return (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
              <span style={{ color: "#7f9bb5" }}>• {line.label}</span>
              <span>
                <span style={{ color: "#fff", fontWeight: 600 }}>{line.v}</span>
                <span style={{ color: line.pos ? "#4caf50" : "#f44336", marginLeft: 6 }}>{line.delta}</span>
              </span>
            </div>
          );
          if (line.t === "flag") return (
            <div key={i} style={{ fontSize: 11, color: line.badge === "WARNING" ? "#ffb300" : "#58a6ff", paddingLeft: 8, borderLeft: `2px solid ${line.badge === "WARNING" ? "#ffb300" : "#58a6ff"}` }}>
              {line.v}
            </div>
          );
          if (line.t === "footer") return <div key={i} style={{ color: "#4eb2e0", fontSize: 11, fontStyle: "italic" }}>{line.v}</div>;
          return null;
        })}
      </div>
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────────
export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [reportType, setReportType] = useState("consolidated");
  const data = HPG_DATA[reportType];

  const tabs = [
    { id: "overview", label: "📊 Phân tích" },
    { id: "arch", label: "🏗️ Kiến trúc" },
    { id: "telegram", label: "🤖 Telegram" },
    { id: "prompts", label: "🧠 AI Prompts" },
  ];

  return (
    <div style={{ background: colors.bg, minHeight: "100vh", color: colors.text, fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {/* Header */}
      <div style={{ borderBottom: `1px solid ${colors.border}`, padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: colors.text }}>
            <span style={{ color: colors.accentBlue }}>Fin</span>Bot
          </div>
          <div style={{ fontSize: 11, color: colors.textMuted }}>Financial Analysis Bot — Design Preview</div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: colors.textMuted }}>HPG Q4/2025</span>
          <div style={{ display: "flex", background: colors.surface2, borderRadius: 6, border: `1px solid ${colors.border}`, overflow: "hidden" }}>
            {["consolidated", "parent"].map(t => (
              <button key={t} onClick={() => setReportType(t)} style={{
                padding: "5px 12px", fontSize: 11, border: "none", cursor: "pointer",
                background: reportType === t ? colors.accentBlue : "transparent",
                color: reportType === t ? "#000" : colors.textMuted,
                fontWeight: reportType === t ? 600 : 400,
              }}>
                {t === "consolidated" ? "Hợp nhất" : "Riêng lẻ"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ borderBottom: `1px solid ${colors.border}`, display: "flex", padding: "0 24px" }}>
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            padding: "10px 16px", background: "none", border: "none",
            borderBottom: activeTab === tab.id ? `2px solid ${colors.accentBlue}` : "2px solid transparent",
            color: activeTab === tab.id ? colors.text : colors.textMuted,
            fontSize: 13, cursor: "pointer", fontWeight: activeTab === tab.id ? 600 : 400,
          }}>{tab.label}</button>
        ))}
      </div>

      <div style={{ padding: "24px" }}>

        {/* ── TAB: OVERVIEW ── */}
        {activeTab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Report type banner */}
            {reportType === "parent" && (
              <div style={{ background: "#1a1a00", border: `1px solid ${colors.accentYellow}`, borderRadius: 8, padding: "10px 16px", fontSize: 13, color: colors.accentYellow }}>
                ⚡ <strong>Báo cáo Công ty Mẹ (Riêng lẻ)</strong> — Đây là báo cáo HOLDING COMPANY. Hầu hết tài sản (98.6%) là đầu tư vào công ty con. Chỉ số vận hành không phản ánh thực tế tập đoàn.
              </div>
            )}

            {/* Summary */}
            <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 16 }}>
              <div style={{ color: colors.textMuted, fontSize: 11, marginBottom: 6, textTransform: "uppercase" }}>Tóm tắt điều hành</div>
              <div style={{ fontSize: 14, lineHeight: 1.7, color: colors.text }}>{data.summary}</div>
            </div>

            {/* Key metrics */}
            <div>
              <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>Chỉ số chính</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                {reportType === "consolidated" ? <>
                  <MetricCard label="Doanh thu thuần" value={data.metrics.revenue} prev={data.metrics.revenue_prev} highlight />
                  <MetricCard label="Lợi nhuận sau thuế" value={data.metrics.net_profit} prev={data.metrics.net_profit_prev} highlight />
                  <MetricCard label="Biên LN gộp" value={data.metrics.gross_margin} unit="%" prev={data.metrics.gross_margin_prev} />
                  <MetricCard label="Biên LN ròng" value={data.metrics.net_margin} unit="%" />
                  <MetricCard label="Current Ratio" value={data.metrics.current_ratio} unit="x" />
                  <MetricCard label="D/E Ratio" value={data.metrics.debt_to_equity} unit="x" />
                  <MetricCard label="ROE" value={data.metrics.roe} unit="%" />
                  <MetricCard label="DSO" value={data.metrics.dso} unit=" ngày" />
                </> : <>
                  <MetricCard label="DT dịch vụ" value={data.metrics.revenue} prev={data.metrics.revenue_prev} />
                  <MetricCard label="LNST" value={data.metrics.net_profit} prev={data.metrics.net_profit_prev} highlight />
                  <MetricCard label="LN công ty con" value={data.metrics.subsidiary_income} highlight />
                  <MetricCard label="Current Ratio" value={data.metrics.current_ratio} unit="x" />
                  <MetricCard label="D/E Ratio" value={data.metrics.debt_to_equity} unit="x" />
                  <MetricCard label="Tổng tài sản" value={data.metrics.total_assets} />
                  <MetricCard label="Vốn chủ sở hữu" value={data.metrics.equity} />
                </>}
              </div>
            </div>

            {/* Segment breakdown - only for consolidated */}
            {reportType === "consolidated" && data.segments && (
              <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: 16 }}>
                <div style={{ color: colors.textMuted, fontSize: 11, marginBottom: 12, textTransform: "uppercase" }}>Phân khúc kinh doanh</div>
                <SegmentBar segments={data.segments} />
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginTop: 14 }}>
                  {data.segments.map((s, i) => (
                    <div key={i} style={{ background: colors.surface2, borderRadius: 6, padding: 10, textAlign: "center" }}>
                      <div style={{ color: colors.textMuted, fontSize: 11 }}>{s.name}</div>
                      <div style={{ color: colors.text, fontWeight: 700, fontSize: 15 }}>{(s.revenue / 1000).toFixed(1)}K tỷ</div>
                      <div style={{ color: colors.accentGreen, fontSize: 12 }}>Biên {s.margin}%</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Flags */}
            <div>
              <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>Phát hiện tự động</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {data.flags.map((f, i) => (
                  <div key={i} style={{
                    background: colors.surface2, border: `1px solid ${colors.border}`,
                    borderLeft: `3px solid ${f.type === "WARNING" ? colors.accentYellow : f.type === "ALERT" ? colors.accent : colors.accentBlue}`,
                    borderRadius: 6, padding: "10px 14px",
                    display: "flex", gap: 10, alignItems: "flex-start",
                  }}>
                    <Badge type={f.type} />
                    <span style={{ fontSize: 13, color: colors.text, lineHeight: 1.5 }}>{f.msg}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB: ARCHITECTURE ── */}
        {activeTab === "arch" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 700 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Kiến trúc hệ thống</div>
              <div style={{ color: colors.textMuted, fontSize: 13 }}>REST API phục vụ cả WebApp và Telegram Bot</div>
            </div>
            <ArchitectureDiagram />

            <div style={{ background: colors.surface2, border: `1px solid ${colors.border}`, borderRadius: 8, padding: 16 }}>
              <div style={{ color: colors.accentGreen, fontSize: 12, fontWeight: 700, marginBottom: 10 }}>🔑 Nguyên tắc thiết kế quan trọng</div>
              {[
                ["Python tính số, Claude phân tích ngữ nghĩa", "Mọi ratio/metrics được tính bằng Python code trước, sau đó truyền vào prompt. Claude KHÔNG tự tính toán."],
                ["Phân biệt riêng lẻ vs hợp nhất", "Bot tự nhận diện loại báo cáo và áp dụng logic phân tích phù hợp. Cảnh báo người dùng khi so sánh không đúng."],
                ["Anomaly detection rule-based", "Các pattern bất thường (AR tăng nhanh hơn doanh thu, capex hoàn thành, VAT lớn...) được hardcode thành rules rõ ràng."],
                ["Segment analysis module riêng", "Bảng phân khúc kinh doanh được parse và phân tích độc lập, không trộn với BCTC tổng hợp."],
              ].map(([title, desc], i) => (
                <div key={i} style={{ marginBottom: 12 }}>
                  <div style={{ color: colors.accentBlue, fontSize: 12, fontWeight: 600 }}>{i + 1}. {title}</div>
                  <div style={{ color: colors.textMuted, fontSize: 12, marginTop: 2 }}>{desc}</div>
                </div>
              ))}
            </div>

            <div style={{ background: colors.surface2, border: `1px solid ${colors.border}`, borderRadius: 8, padding: 16 }}>
              <div style={{ color: colors.accentYellow, fontSize: 12, fontWeight: 700, marginBottom: 10 }}>📦 Tech Stack</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12 }}>
                {[
                  ["API Framework", "FastAPI + Uvicorn"],
                  ["PDF Parsing", "pdfplumber + BeautifulSoup"],
                  ["AI Engine", "Claude claude-sonnet-4-20250514 (Anthropic)"],
                  ["Telegram", "python-telegram-bot v21"],
                  ["Database", "PostgreSQL + Redis"],
                  ["Deployment", "Docker Compose"],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: "flex", gap: 8 }}>
                    <span style={{ color: colors.textMuted }}>{k}:</span>
                    <span style={{ color: colors.text, fontWeight: 500 }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB: TELEGRAM ── */}
        {activeTab === "telegram" && (
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <div style={{ flex: "0 0 auto" }}>
              <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 10, textTransform: "uppercase" }}>Preview tin nhắn Telegram</div>
              <TelegramPreview data={HPG_DATA} />
            </div>
            <div style={{ flex: "1 1 300px", display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ fontSize: 12, color: colors.textMuted, textTransform: "uppercase", marginBottom: 4 }}>Commands</div>
              {[
                ["/start", "Giới thiệu bot, hướng dẫn sử dụng"],
                ["/analyze", "Phân tích đầy đủ báo cáo vừa upload"],
                ["/metrics", "Bảng chỉ số tài chính tóm gọn"],
                ["/ask [câu hỏi]", "Chat Q&A với báo cáo"],
                ["/compare", "So sánh với kỳ trước (nếu có)"],
                ["/flags", "Chỉ hiện các bất thường phát hiện được"],
              ].map(([cmd, desc]) => (
                <div key={cmd} style={{ background: colors.surface2, border: `1px solid ${colors.border}`, borderRadius: 6, padding: "8px 12px", display: "flex", gap: 12 }}>
                  <span style={{ color: colors.accentBlue, fontFamily: "monospace", fontSize: 13, whiteSpace: "nowrap" }}>{cmd}</span>
                  <span style={{ color: colors.textMuted, fontSize: 12 }}>{desc}</span>
                </div>
              ))}
              <div style={{ background: "#0d2149", border: `1px solid ${colors.accentBlue}40`, borderRadius: 6, padding: 12, fontSize: 12, color: colors.accentBlue, marginTop: 4 }}>
                💡 Telegram bot dùng chung API backend với WebApp — chỉ khác ở lớp formatter (Markdown thay vì JSON/HTML)
              </div>
            </div>
          </div>
        )}

        {/* ── TAB: PROMPTS ── */}
        {activeTab === "prompts" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 750 }}>
            <div style={{ fontSize: 13, color: colors.textMuted }}>
              Thiết kế prompt quyết định 70% chất lượng phân tích. Dưới đây là cấu trúc prompts cho từng tình huống.
            </div>
            {[
              {
                title: "System Prompt — Full Analysis",
                color: colors.accentGreen,
                code: `Bạn là chuyên gia phân tích tài chính, chuyên thị trường Việt Nam.
Chuẩn mực: VAS (Thông tư 200, 202), IFRS.

QUY TẮC BẮT BUỘC:
1. KHÔNG tự tính số — dùng metrics đã cho sẵn
2. Luôn cite số liệu cụ thể (VD: "DT 40.6 nghìn tỷ, +17.7% YoY")
3. Phân biệt báo cáo riêng lẻ vs hợp nhất
4. Với holding company: cảnh báo bản chất holding
5. Flag bất thường TRƯỚC khi kết luận

OUTPUT: JSON với executive_summary, highlights, risks, sections, outlook`,
              },
              {
                title: "User Prompt — Truyền dữ liệu đã tính",
                color: colors.accentBlue,
                code: `Phân tích báo cáo: HPG Hợp nhất Q4/2025

CHỈ SỐ (Python đã tính — dùng trực tiếp):
{
  "revenue": 40600,     // tỷ đồng
  "net_profit": 3888,
  "gross_margin": 15.2, // %
  "current_ratio": 1.42,
  "dso": 24.4,          // ngày
  ...
}

FLAGS PHÁT HIỆN:
- WARNING: AR tăng +152% vs DT +17.7%
- INFO: CAPEX project completed (Dung Quất 2)
- INFO: VAT refund pending 7.4K tỷ

→ Phân tích và trả về JSON theo format quy định.`,
              },
              {
                title: "System Prompt — Chat Q&A",
                color: colors.accentPurple,
                code: `Bạn là trợ lý phân tích báo cáo tài chính.
Context báo cáo đã được cung cấp.

Khi trả lời:
- Cite con số cụ thể từ báo cáo
- Giải thích ngắn gọn, không hoa mỹ  
- Nếu câu hỏi liên quan holding vs hợp nhất,
  chủ động giải thích sự khác biệt
- Nếu không có đủ thông tin: nói rõ,
  không đoán mò

Format: {"answer": "...", "cited_figures": [...]}`,
              },
            ].map((p, i) => (
              <div key={i} style={{ background: colors.surface2, border: `1px solid ${colors.border}`, borderRadius: 8, overflow: "hidden" }}>
                <div style={{ background: colors.surface, padding: "8px 14px", borderBottom: `1px solid ${colors.border}`, color: p.color, fontSize: 12, fontWeight: 600 }}>
                  {p.title}
                </div>
                <pre style={{ margin: 0, padding: 14, fontSize: 11, lineHeight: 1.6, color: colors.text, overflowX: "auto", whiteSpace: "pre-wrap" }}>
                  {p.code}
                </pre>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
