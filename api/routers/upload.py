from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.analyst import FinBotService
from db.store import save_report

router = APIRouter()
service = FinBotService(use_llm=False)  # Parser only, không cần LLM


class UploadResponse(BaseModel):
    report_id: str
    company: str
    period: str
    report_type: str
    is_holding_company: bool
    parsed_sections: list[str]
    status: str


@router.post("/upload", response_model=UploadResponse)
async def upload_report(file: UploadFile = File(...)):
    """
    Upload file báo cáo tài chính (PDF, Markdown, HTML).
    Trả về report_id để dùng cho các endpoint tiếp theo.
    """
    allowed_types = {
        "text/markdown", "text/html", "text/plain",
        "application/pdf", "application/octet-stream"
    }
    filename = file.filename or ""
    if not any(filename.endswith(ext) for ext in [".md", ".html", ".htm", ".pdf", ".txt"]):
        raise HTTPException(400, "Chỉ hỗ trợ file .md, .html, .pdf, .txt")

    content_bytes = await file.read()
    if len(content_bytes) > 20 * 1024 * 1024:  # 20MB
        raise HTTPException(400, "File quá lớn (tối đa 20MB)")

    content_str = content_bytes.decode("utf-8", errors="replace")

    try:
        data = service.parse_content(content_str, filename=filename)
    except Exception as e:
        raise HTTPException(500, f"Lỗi parse file: {str(e)}")

    report_id = save_report(data)

    # Detect which sections were parsed
    sections = []
    if data.balance_sheet_current.items:
        sections.append("balance_sheet")
    if data.income_current.items:
        sections.append("income_statement")
    if data.cashflow_current.items:
        sections.append("cashflow")
    if data.segments:
        sections.append("segments")
    if data.notes_text:
        sections.append("notes")

    return UploadResponse(
        report_id=report_id,
        company=data.company_name or "Không xác định",
        period=data.period or "Không xác định",
        report_type=data.report_type.value,
        is_holding_company=data.is_holding_company,
        parsed_sections=sections,
        status="ready"
    )
