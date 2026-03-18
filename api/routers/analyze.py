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

    resp = result.to_api_response()
    resp["segments"] = data.segments  # ghi đè segment_analysis (luôn rỗng) bằng dữ liệu thực
    return {
        "report_id": req.report_id,
        "company": data.company_name,
        "period": data.period,
        "report_type": data.report_type.value,
        "is_consolidated": data.is_consolidated,
        "is_holding_company": data.is_holding_company,
        **resp
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


class CombinedRequest(BaseModel):
    consolidated_id: Optional[str] = None
    parent_id: Optional[str] = None


def _format_section(data, result) -> dict:
    """Format một report thành structure output.json."""
    label = f"{data.company_name or 'Unknown'} {'Hợp nhất' if data.is_consolidated else 'Công ty mẹ'} {data.period}"

    # Metrics: lấy từ result.metrics.to_dict()
    metrics = result.metrics.to_dict()

    # DuPont: rename roe_dupont_3 → roe_dupont_3f, roe_dupont_5 → roe_dupont_5f
    dupont = {}
    if result.dupont:
        raw = result.dupont.to_dict()
        dupont = {
            k.replace("roe_dupont_3", "roe_dupont_3f").replace("roe_dupont_5", "roe_dupont_5f"): v
            for k, v in raw.items()
        }

    # Cashflow
    cashflow = result.cashflow.to_dict() if result.cashflow else {}

    # Beneish: tách components ra khỏi top-level
    beneish = {}
    if result.beneish:
        raw = result.beneish.to_dict()
        components = {k: raw[k] for k in ("dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi", "tata") if k in raw}
        beneish = {
            "m_score": raw.get("m_score"),
            "interpretation": raw.get("interpretation", ""),
            "confidence": raw.get("confidence", ""),
        }
        if components:
            beneish["components"] = components

    return {
        "label": label,
        "metadata": {
            "company_name": data.company_name,
            "period": data.period,
            "report_type": data.report_type.value,
            "is_holding_company": data.is_holding_company,
        },
        "metrics": metrics,
        "dupont": dupont,
        "cashflow": cashflow,
        "beneish": beneish,
        "flags": [f.to_dict() for f in result.flags],
    }


@router.post("/analyze/combined")
async def analyze_combined(req: CombinedRequest):
    """
    Phân tích 1 hoặc 2 báo cáo (consolidated + parent), trả về format output.json.
    Mỗi report_id phân tích độc lập — không bắt buộc phải có cả hai.
    """
    if not req.consolidated_id and not req.parent_id:
        raise HTTPException(400, "Cần ít nhất một consolidated_id hoặc parent_id")

    output = {}

    for key, report_id in [("consolidated", req.consolidated_id), ("parent", req.parent_id)]:
        if not report_id:
            continue
        entry = get_report(report_id)
        if not entry:
            raise HTTPException(404, f"Không tìm thấy report_id: {report_id}")
        data, _ = entry
        try:
            result = service.calculate(data)
            update_result(report_id, result)
        except Exception as e:
            raise HTTPException(500, f"Lỗi phân tích {key}: {str(e)}")
        output[key] = _format_section(data, result)

    return output
