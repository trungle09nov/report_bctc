# 📊 FinBot — Bot Phân Tích Tài Chính Việt Nam

Bot phân tích BCTC theo chuẩn VAS (Thông tư 200/202).  
Hỗ trợ: **REST API** (WebApp) + **Telegram Bot**

## Kiến trúc
```
PDF/MD → Parser → Calculator (Python) → Anomaly Detector → Claude API → Output
```
**Nguyên tắc cốt lõi**: Python tính số, Claude chỉ diễn giải.

---

## Cài đặt nhanh

```bash
# 1. Clone và cài dependencies
git clone ...
pip install -r requirements.txt

# 2. Cấu hình
cp .env.example .env
# Điền ANTHROPIC_API_KEY và TELEGRAM_BOT_TOKEN

# 3. Chạy API
uvicorn api.main:app --reload --port 8000

# 4. Chạy Telegram Bot (terminal khác)
python telegram/bot.py
```

---

## Sử dụng API

### Upload báo cáo
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@HPG_Q4_2025.md"

# Response:
# { "report_id": "a1b2c3d4", "company": "Tập đoàn Hòa Phát", ... }
```

### Phân tích đầy đủ (với LLM)
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"report_id": "a1b2c3d4", "language": "vi"}'
```

### Chỉ lấy metrics (không cần LLM — nhanh hơn)
```bash
curl -X POST http://localhost:8000/api/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{"report_id": "a1b2c3d4"}'
```

### Chat Q&A
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "a1b2c3d4",
    "message": "Tại sao phải thu khách hàng tăng mạnh?",
    "history": []
  }'
```

---

## Telegram Bot

Lệnh:
- `/start` — Giới thiệu
- Gửi file `.md` hoặc `.txt` → Bot parse tự động
- `/analyze` — Phân tích đầy đủ
- `/metrics` — Bảng chỉ số
- `/flags` — Xem bất thường
- `/ask [câu hỏi]` — Chat với báo cáo
- `/clear` — Xóa session

---

## Chạy test

```bash
# Test với file HPG thực tế (không cần API key)
python tests/test_integration.py
```

---

## Cấu trúc project

```
finbot/
├── api/                    # FastAPI endpoints
│   ├── main.py
│   └── routers/
│       ├── upload.py       # POST /upload
│       ├── analyze.py      # POST /analyze, /metrics
│       └── chat.py         # POST /chat
├── core/
│   ├── parser/
│   │   ├── md_parser.py    # Parse Markdown/HTML → ReportData
│   │   ├── mapping.py      # Thông tư 200/202 mã số → labels
│   │   └── utils.py        # parse_vnd(), to_billion()
│   ├── calculator/
│   │   ├── ratios.py       # Tính toán chỉ số tài chính
│   │   └── anomaly.py      # Phát hiện bất thường
│   └── analyst/
│       ├── __init__.py     # FinBotService orchestrator
│       ├── llm.py          # Claude API wrapper
│       └── prompts.py      # System prompts
├── telegram/
│   ├── bot.py              # Telegram bot handlers
│   └── formatter.py        # Format output → Markdown
├── models/                 # Dataclasses
├── db/
│   └── store.py            # In-memory store (MVP)
└── tests/
    ├── test_integration.py
    └── fixtures/           # Sample reports
```

---

## Roadmap

- [ ] PDF parser (pdfplumber)
- [ ] PostgreSQL + Redis persistence
- [ ] Multi-period comparison
- [ ] Webhook mode cho Telegram
- [ ] Benchmarking ngành
