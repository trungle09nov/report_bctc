"""
In-memory store cho reports (MVP).
Production: thay bằng Redis + PostgreSQL.
"""
import uuid
from typing import Optional
from models.report import ReportData
from models.metrics import AnalysisResult

# report_id → (ReportData, AnalysisResult | None)
_store: dict[str, tuple[ReportData, Optional[AnalysisResult]]] = {}


def save_report(data: ReportData, result: Optional[AnalysisResult] = None) -> str:
    report_id = str(uuid.uuid4())[:8]
    _store[report_id] = (data, result)
    return report_id


def get_report(report_id: str) -> Optional[tuple[ReportData, Optional[AnalysisResult]]]:
    return _store.get(report_id)


def update_result(report_id: str, result: AnalysisResult):
    if report_id in _store:
        data, _ = _store[report_id]
        _store[report_id] = (data, result)


def list_reports() -> list[dict]:
    return [
        {"report_id": rid, **data.to_dict()}
        for rid, (data, _) in _store.items()
    ]
