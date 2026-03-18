from fastapi import APIRouter, UploadFile, File, HTTPException
import tempfile
from pathlib import Path
import asyncio
from pydantic import BaseModel
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.analyst import FinBotService
from db.store import save_report

# LlamaCloud import
from llama_cloud import AsyncLlamaCloud
from dotenv import load_dotenv

load_dotenv()  # Load biến môi trường từ .env
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
    if len(content_bytes) > 30 * 1024 * 1024:  # 23MB
        raise HTTPException(400, "File quá lớn (tối đa 30MB)")

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


# --- New endpoint: Upload PDF, OCR & parse with llama_cloud ---
class UploadPDFResponse(BaseModel):
    markdown: str
    report_id: str
    company: str
    period: str
    report_type: str
    is_holding_company: bool
    parsed_sections: list[str]
    status: str


@router.post("/upload/pdf", response_model=UploadPDFResponse)
async def upload_pdf_llama(file: UploadFile = File(...)):
    """
    Upload file PDF, dùng llama_cloud OCR + parse, trả về markdown và report_id.
    """

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Chỉ hỗ trợ file PDF")

    # Tạo thư mục OCR nếu chưa có
    ocr_dir = Path("OCR")
    ocr_dir.mkdir(exist_ok=True)
    pdf_path = ocr_dir / file.filename
    # Nếu trùng tên thì thêm hậu tố
    if pdf_path.exists():
        base, ext = pdf_path.stem, pdf_path.suffix
        i = 1
        while (ocr_dir / f"{base}_{i}{ext}").exists():
            i += 1
        pdf_path = ocr_dir / f"{base}_{i}{ext}"
    with open(pdf_path, "wb") as f:
        f.write(await file.read())
    tmp_path = str(pdf_path)

    # LlamaCloud OCR + parse
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise HTTPException(500, "Thiếu biến môi trường LLAMA_CLOUD_API_KEY")

    client = AsyncLlamaCloud(api_key=api_key)
    try:
        file_obj = await client.files.create(file=tmp_path, purpose="parse")
        result = await client.parsing.parse(
            file_id=file_obj.id,
            tier="agentic",
            version="latest",
            output_options={
                "markdown": {"tables": {"output_tables_as_markdown": False}},
            },
            processing_options={
                "ignore": {"ignore_diagonal_text": True},
                "ocr_parameters": {"languages": ["vi", "en"]},
            },
            expand=["markdown"],
        )
    except Exception as e:
        raise HTTPException(500, f"Lỗi llama_cloud: {str(e)}")

    # Ghép markdown từ tất cả các trang (bỏ qua trang lỗi)
    if not result.markdown or not result.markdown.pages:
        raise HTTPException(500, "LlamaParse không trả về markdown")
    markdown = "\n".join([p.markdown for p in result.markdown.pages if hasattr(p, "markdown")])

    # Lưu markdown ra file cùng thư mục OCR
    md_path = pdf_path.with_suffix(".md")
    md_path.write_text(markdown, encoding="utf-8")

    # Parse markdown như upload thường
    try:
        data = service.parse_content(markdown, filename=file.filename)
    except Exception as e:
        raise HTTPException(500, f"Lỗi parse markdown: {str(e)}")

    report_id = save_report(data)
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

    return UploadPDFResponse(
        markdown=markdown,
        report_id=report_id,
        company=data.company_name or "Không xác định",
        period=data.period or "Không xác định",
        report_type=data.report_type.value,
        is_holding_company=data.is_holding_company,
        parsed_sections=sections,
        status="ready"
    )
