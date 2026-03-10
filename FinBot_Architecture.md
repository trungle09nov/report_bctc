# 🏗️ Kiến trúc Bot Phân Tích Tài Chính (FinBot)
**Target: REST API cho WebApp + Telegram Bot**
**Stack: Python · FastAPI · Claude API · python-telegram-bot**

---

## 1. Tổng quan hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                        │
│   [WebApp React]          [Telegram Bot]                │
└──────────┬───────────────────────┬──────────────────────┘
           │ REST API              │ Webhook / Polling
           ▼                       ▼
┌─────────────────────────────────────────────────────────┐
│                    API GATEWAY (FastAPI)                 │
│  POST /analyze      POST /compare     GET /history      │
│  POST /upload       POST /chat        GET /metrics      │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                   PROCESSING PIPELINE                   │
│                                                         │
│  [1. Parser]  →  [2. Calculator]  →  [3. LLM Analyst]  │
│  PDF/MD/HTML     Python formulas     Claude API         │
│  → structured    → ratios, flags     → narrative +      │
│    JSON data       anomalies           insights         │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                    DATA LAYER                           │
│   PostgreSQL (structured data)   Redis (cache/session)  │
│   S3/MinIO (raw files)                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. API Endpoints

### 2.1 Upload & Parse
```
POST /api/v1/upload
Content-Type: multipart/form-data

Body:
  file: [PDF hoặc MD]
  report_type: "consolidated" | "parent_only"
  company_code: "HPG" (optional)
  period: "Q4/2025" (optional)

Response:
{
  "report_id": "rpt_abc123",
  "company": "Hòa Phát",
  "period": "Q4/2025",
  "type": "consolidated",
  "parsed_sections": ["balance_sheet", "income_stmt", "cashflow", "notes"],
  "status": "ready"
}
```

### 2.2 Phân tích đầy đủ
```
POST /api/v1/analyze
{
  "report_id": "rpt_abc123",
  "analysis_type": "full" | "quick" | "custom",
  "modules": ["liquidity", "profitability", "leverage", "cashflow", "segment"],
  "language": "vi" | "en"
}

Response:
{
  "report_id": "rpt_abc123",
  "summary": "LNST Q4/2025 đạt 3.888 tỷ, tăng 38% YoY...",
  "metrics": { ... },         // các chỉ số đã tính
  "flags": [ ... ],           // bất thường cần chú ý
  "sections": { ... },        // phân tích từng mảng
  "segment_breakdown": { ... }
}
```

### 2.3 Chat / Q&A
```
POST /api/v1/chat
{
  "report_id": "rpt_abc123",
  "message": "Tại sao phải thu khách hàng tăng mạnh vậy?",
  "history": [ ... ]   // conversation history
}

Response:
{
  "answer": "...",
  "cited_figures": ["AR: 10.994 tỷ (+152% YoY)", "Revenue: +17.7% YoY"],
  "confidence": "high"
}
```

### 2.4 So sánh đa kỳ
```
POST /api/v1/compare
{
  "report_ids": ["rpt_q1", "rpt_q2", "rpt_q3", "rpt_q4"],
  "metrics": ["revenue", "net_profit", "gross_margin", "current_ratio"]
}
```

---

## 3. Processing Pipeline Chi Tiết

### 3.1 Parser Module
```python
class FinancialParser:
    """
    Input:  PDF / Markdown / HTML
    Output: Structured dict theo chuẩn Thông tư 200/202
    """
    
    def parse(self, file) -> ReportData:
        # Bước 1: Detect file type
        # Bước 2: Extract tables (pdfplumber / BeautifulSoup)
        # Bước 3: Map mã số khoản mục → semantic label
        #   VD: mã 270 → "total_assets"
        #       mã 300 → "total_liabilities"  
        #       mã 400 → "equity"
        # Bước 4: Parse số VND (xử lý dấu chấm ngăn cách)
        # Bước 5: Detect report type (riêng lẻ vs hợp nhất)
        # Bước 6: Return structured ReportData
```

**Mapping mã số Thông tư 200 (quan trọng):**
| Mã | Label | Ghi chú |
|---|---|---|
| 110 | cash_equivalents | |
| 130 | short_term_receivables | |
| 131 | trade_receivables | Dùng tính DSO |
| 140 | inventory | Dùng tính inventory turnover |
| 270 | total_assets | |
| 300 | total_liabilities | |
| 310 | short_term_liabilities | Dùng tính current ratio |
| 330 | long_term_liabilities | |
| 400 | equity | |
| 410 | charter_capital | |
| 01 | revenue | từ KQKD |
| 10 | net_revenue | |
| 20 | cogs | |
| 30 | gross_profit | |
| 60 | operating_profit | |
| 70 | financial_income | Flag nếu là holding |
| 80 | financial_expense | |
| 60 | ebit | |
| 70 | pbt | |
| 60 | pat | Lợi nhuận sau thuế |

### 3.2 Calculator Module
```python
class FinancialCalculator:
    """
    Input:  ReportData (đã parse)
    Output: Metrics dict + Flags list
    
    QUAN TRỌNG: Tất cả số được tính ở đây bằng Python,
    KHÔNG để LLM tự tính để đảm bảo độ chính xác.
    """
    
    def calculate_all(self, data: ReportData) -> AnalysisResult:
        metrics = {}
        flags = []
        
        # --- THANH KHOẢN ---
        metrics["current_ratio"] = current_assets / current_liabilities
        metrics["quick_ratio"] = (current_assets - inventory) / current_liabilities
        metrics["cash_ratio"] = cash / current_liabilities
        
        # --- LỢI NHUẬN ---
        metrics["gross_margin"] = gross_profit / net_revenue
        metrics["operating_margin"] = operating_profit / net_revenue
        metrics["net_margin"] = pat / net_revenue
        metrics["roe"] = pat / equity
        metrics["roa"] = pat / total_assets
        
        # --- ĐÒN BẨY ---
        metrics["debt_to_equity"] = total_liabilities / equity
        metrics["debt_to_assets"] = total_liabilities / total_assets
        metrics["interest_coverage"] = ebit / interest_expense
        
        # --- HIỆU QUẢ VẬN HÀNH ---
        metrics["dso"] = (trade_receivables / net_revenue) * 90  # quarterly
        metrics["inventory_days"] = (inventory / cogs) * 90
        metrics["asset_turnover"] = net_revenue / total_assets
        
        # --- PHÁT HIỆN BẤT THƯỜNG ---
        flags = self._detect_anomalies(data, metrics)
        
        return AnalysisResult(metrics=metrics, flags=flags)
    
    def _detect_anomalies(self, data, metrics) -> list[Flag]:
        flags = []
        
        # Rule 1: Phải thu tăng nhanh hơn doanh thu
        ar_growth = (ar_current - ar_prev) / ar_prev
        rev_growth = (rev_current - rev_prev) / rev_prev
        if ar_growth > rev_growth * 1.5:
            flags.append(Flag(
                type="WARNING",
                code="AR_OUTPACE_REVENUE",
                message="Phải thu khách hàng tăng nhanh hơn doanh thu — kiểm tra DSO",
                data={"ar_growth": ar_growth, "rev_growth": rev_growth}
            ))
        
        # Rule 2: Holding company — LNST cao bất thường
        if financial_income / net_revenue > 0.5:
            flags.append(Flag(
                type="INFO",
                code="HOLDING_COMPANY_PATTERN",
                message="Công ty mẹ holding — lợi nhuận chủ yếu từ công ty con chuyển về",
                data={"financial_income_ratio": financial_income / net_revenue}
            ))
        
        # Rule 3: Tài sản dở dang giảm + TSCĐ tăng tương ứng
        if wip_decrease > 0 and ppe_increase > 0:
            if abs(wip_decrease - ppe_increase) / ppe_increase < 0.2:
                flags.append(Flag(
                    type="INFO",
                    code="CAPEX_PROJECT_COMPLETED",
                    message="Có vẻ dự án đầu tư lớn vừa hoàn thành và đưa vào sử dụng",
                ))
        
        # Rule 4: VAT hoàn thuế lớn
        if vat_receivable / total_current_assets > 0.1:
            flags.append(Flag(
                type="INFO",
                code="LARGE_VAT_REFUND_PENDING",
                message=f"VAT chờ hoàn thuế lớn: {vat_receivable/1e12:.1f} nghìn tỷ",
            ))
        
        # Rule 5: Current ratio < 1
        if metrics["current_ratio"] < 1.0:
            flags.append(Flag(type="ALERT", code="LOW_LIQUIDITY", ...))
        
        return flags
```

### 3.3 LLM Analyst Module
```python
SYSTEM_PROMPT = """
Bạn là chuyên gia phân tích tài chính cấp cao, chuyên về thị trường chứng khoán Việt Nam.
Bạn có kiến thức sâu về chuẩn mực kế toán VAS (Thông tư 200, 202), đặc thù ngành thép,
và thị trường vốn Việt Nam.

QUY TẮC BẮT BUỘC:
1. KHÔNG tự tính toán số liệu — tất cả số đã được tính sẵn và truyền vào cho bạn
2. Luôn cite số liệu cụ thể khi nhận định
3. Phân biệt rõ báo cáo riêng lẻ (công ty mẹ) vs hợp nhất
4. Đối với công ty mẹ holding: giải thích rõ bản chất holding, không áp chỉ số 
   vận hành thông thường
5. Khi phân tích KQKD riêng lẻ của HPG: lưu ý LNST cao là do lợi nhuận con 
   chuyển về, không phải hoạt động kinh doanh trực tiếp
6. Luôn so sánh với kỳ trước (YoY hoặc QoQ) khi có dữ liệu
7. Flag các điểm bất thường trước khi kết luận
8. Ngôn ngữ: {language}

FORMAT ĐẦU RA (JSON):
{
  "executive_summary": "2-3 câu tóm tắt quan trọng nhất",
  "highlights": [...],      // top 3-5 điểm nổi bật
  "risks": [...],           // rủi ro cần chú ý
  "sections": {
    "profitability": "...",
    "liquidity": "...",
    "leverage": "...",
    "cashflow": "...",
    "segment": "..."        // nếu có
  },
  "outlook": "..."          // nhận định triển vọng ngắn hạn
}
"""

def analyze_with_llm(report_data: ReportData, calc_result: AnalysisResult) -> str:
    # Truyền data đã tính sẵn vào prompt
    user_prompt = f"""
Phân tích báo cáo tài chính sau:

THÔNG TIN BÁO CÁO:
- Công ty: {report_data.company_name}
- Kỳ: {report_data.period}
- Loại: {"Hợp nhất" if report_data.is_consolidated else "Riêng lẻ (Công ty mẹ)"}

CHỈ SỐ ĐÃ TÍNH (sử dụng trực tiếp, không tính lại):
{json.dumps(calc_result.metrics, ensure_ascii=False, indent=2)}

CÁC BẤT THƯỜNG PHÁT HIỆN:
{json.dumps([f.to_dict() for f in calc_result.flags], ensure_ascii=False, indent=2)}

SỐ LIỆU CHÍNH:
{json.dumps(report_data.key_figures, ensure_ascii=False, indent=2)}

Hãy phân tích toàn diện và trả về JSON theo format đã quy định.
"""
    # Gọi Claude API
    response = anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": user_prompt}],
        system=SYSTEM_PROMPT.format(language="Tiếng Việt")
    )
    return response.content[0].text
```

---

## 4. Telegram Bot Flow

```python
# handlers.py
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# /start — Giới thiệu bot
async def start(update, context):
    await update.message.reply_text(
        "📊 *FinBot — Phân Tích Tài Chính*\n\n"
        "Gửi file PDF báo cáo tài chính để tôi phân tích.\n\n"
        "Lệnh có sẵn:\n"
        "/analyze — Phân tích báo cáo vừa upload\n"
        "/metrics — Xem các chỉ số tài chính\n"
        "/ask [câu hỏi] — Hỏi về báo cáo\n"
        "/compare — So sánh các kỳ",
        parse_mode="Markdown"
    )

# Nhận file PDF
async def handle_document(update, context):
    file = await update.message.document.get_file()
    # Download → gọi /upload API → lưu report_id vào context
    report_id = await call_api_upload(file)
    context.user_data["report_id"] = report_id
    await update.message.reply_text(
        f"✅ Đã nhận báo cáo!\n"
        f"Gõ /analyze để phân tích, hoặc /ask [câu hỏi] để hỏi trực tiếp."
    )

# /analyze — Phân tích đầy đủ
async def analyze(update, context):
    report_id = context.user_data.get("report_id")
    if not report_id:
        await update.message.reply_text("Vui lòng gửi file PDF trước.")
        return
    
    msg = await update.message.reply_text("⏳ Đang phân tích...")
    result = await call_api_analyze(report_id)
    
    # Format cho Telegram (Markdown)
    text = format_telegram_response(result)
    await msg.edit_text(text, parse_mode="Markdown")

# /ask — Chat với báo cáo
async def ask(update, context):
    question = " ".join(context.args)
    report_id = context.user_data.get("report_id")
    result = await call_api_chat(report_id, question)
    await update.message.reply_text(result["answer"])
```

**Telegram Response Format (ví dụ):**
```
📊 *HPG — Hợp nhất Q4/2025*

📌 *Tóm tắt*
LNST đạt 3.888 tỷ (+38% YoY), nhờ sản lượng thép tăng mạnh và giá vốn được kiểm soát tốt.

📈 *Điểm nổi bật*
• Doanh thu thuần: 40.6 nghìn tỷ (+17.7% YoY)
• Gross margin: 15.2% (cải thiện so với 13.8% Q4/2024)
• TSCĐ tăng gần 2x → Dung Quất 2 đã HOÀN THÀNH

⚠️ *Cần chú ý*
• Phải thu khách hàng +152% YoY — theo dõi DSO
• VAT chờ hoàn: 7.4 nghìn tỷ (tồn đọng từ CAPEX)
• D/E ratio tăng — cần theo dõi chi phí lãi vay

💡 Dùng /ask để hỏi chi tiết hơn
```

---

## 5. Project Structure

```
finbot/
├── api/
│   ├── main.py              # FastAPI app
│   ├── routers/
│   │   ├── upload.py
│   │   ├── analyze.py
│   │   ├── chat.py
│   │   └── compare.py
│   └── middleware/
│       ├── auth.py          # API key auth
│       └── rate_limit.py
│
├── core/
│   ├── parser/
│   │   ├── pdf_parser.py    # pdfplumber
│   │   ├── md_parser.py     # BeautifulSoup
│   │   └── mapping.py       # Thông tư 200/202 mã số → labels
│   │
│   ├── calculator/
│   │   ├── ratios.py        # Công thức các chỉ số
│   │   ├── anomaly.py       # Phát hiện bất thường
│   │   └── segment.py       # Phân tích theo phân khúc
│   │
│   └── analyst/
│       ├── llm.py           # Claude API wrapper
│       ├── prompts.py       # System prompts
│       └── formatter.py     # Format output
│
├── telegram/
│   ├── bot.py               # Bot application
│   ├── handlers.py          # Command handlers
│   └── formatter.py         # Telegram Markdown format
│
├── models/
│   ├── report.py            # ReportData dataclass
│   ├── metrics.py           # AnalysisResult dataclass
│   └── flag.py              # Flag dataclass
│
├── db/
│   ├── postgres.py
│   └── redis.py
│
├── tests/
│   ├── test_parser.py
│   ├── test_calculator.py
│   └── test_fixtures/       # Sample reports
│
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## 6. Tech Stack & Dependencies

```
# requirements.txt

# API Framework
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9

# Financial Document Parsing
pdfplumber==0.11.0
beautifulsoup4==4.12.3
lxml==5.2.2

# AI
anthropic==0.34.0

# Telegram
python-telegram-bot==21.5

# Database
sqlalchemy==2.0.31
asyncpg==0.29.0
redis==5.0.8
alembic==1.13.2

# Utils
pydantic==2.8.0
python-dotenv==1.0.1
aiohttp==3.10.0
pandas==2.2.2        # Xử lý bảng số liệu
```

---

## 7. Environment Variables

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=...
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/finbot
REDIS_URL=redis://localhost:6379
API_SECRET_KEY=...            # cho WebApp
MAX_FILE_SIZE_MB=20
RATE_LIMIT_PER_MIN=10
```

---

## 8. Deployment (Docker Compose)

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis]
  
  telegram:
    build: .
    command: python -m telegram.bot
    env_file: .env
    depends_on: [api]
  
  postgres:
    image: postgres:16
    volumes: ["pgdata:/var/lib/postgresql/data"]
  
  redis:
    image: redis:7-alpine
```

---

## 9. Roadmap

| Phase | Tính năng | Timeline |
|---|---|---|
| MVP | Upload PDF → Parse → Phân tích cơ bản → Telegram | 2-3 tuần |
| v1.0 | Chat Q&A · So sánh đa kỳ · WebApp API đầy đủ | +2 tuần |
| v1.5 | Segment analysis · Anomaly detection · History | +2 tuần |
| v2.0 | Multi-company benchmarking · Alert theo dõi · Dashboard | +1 tháng |
