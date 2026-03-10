from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.analyst import FinBotService
from db.store import get_report, update_result

router = APIRouter()
service = FinBotService(use_llm=True)


class AnalyzeRequest(BaseModel):
    report_id: str
    language: str = "vi"
    use_llm: bool = True


class MetricsOnlyRequest(BaseModel):
    report_id: str


@router.post("/analyze")
async def analyze_report(req: AnalyzeRequest):
    """
    Phân tích đầy đủ báo cáo (metrics + anomaly detection + LLM narrative).
    """
    entry = get_report(req.report_id)
    if not entry:
        raise HTTPException(404, f"Không tìm thấy report_id: {req.report_id}")

    data, cached_result = entry

    try:
        if req.use_llm:
            result = service.analyze(data, language=req.language)
        else:
            result = service.calculate(data)

        update_result(req.report_id, result)

    except Exception as e:
        raise HTTPException(500, f"Lỗi phân tích: {str(e)}")

    return {
        "report_id": req.report_id,
        "company": data.company_name,
        "period": data.period,
        "report_type": data.report_type.value,
        "is_consolidated": data.is_consolidated,
        "is_holding_company": data.is_holding_company,
        **result.to_api_response()
    }


@router.post("/metrics")
async def get_metrics_only(req: MetricsOnlyRequest):
    """
    Chỉ tính metrics và anomaly flags (không gọi LLM — nhanh hơn).
    """
    entry = get_report(req.report_id)
    if not entry:
        raise HTTPException(404, f"Không tìm thấy report_id: {req.report_id}")

    data, _ = entry

    try:
        result = service.calculate(data)
        update_result(req.report_id, result)
    except Exception as e:
        raise HTTPException(500, f"Lỗi tính toán: {str(e)}")

    return {
        "report_id": req.report_id,
        "metrics": result.metrics.to_dict(),
        "flags": [f.to_dict() for f in result.flags],
        "segments": data.segments,
    }


@router.get("/reports")
async def list_reports():
    """Danh sách reports đã upload"""
    from db.store import list_reports as _list
    return {"reports": _list()}
