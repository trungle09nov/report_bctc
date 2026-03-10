from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.analyst import FinBotService
from db.store import get_report

router = APIRouter()
service = FinBotService(use_llm=True)


class ChatRequest(BaseModel):
    report_id: str
    message: str
    history: list = []


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Chat Q&A với báo cáo tài chính.
    Cần đã gọi /analyze hoặc /metrics trước để có result trong cache.
    """
    entry = get_report(req.report_id)
    if not entry:
        raise HTTPException(404, f"Không tìm thấy report_id: {req.report_id}")

    data, result = entry
    if result is None:
        # Auto-calculate nếu chưa có
        result = service.calculate(data)

    try:
        response = service.chat(data, result, req.message, req.history)
    except Exception as e:
        raise HTTPException(500, f"Lỗi chat: {str(e)}")

    return {
        "report_id": req.report_id,
        "question": req.message,
        **response
    }
