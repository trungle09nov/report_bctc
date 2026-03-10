"""
FinBotService — orchestrator chính
Kết hợp Parser → Calculator → AnomalyDetector → LLMAnalyst
"""
import logging
from pathlib import Path

from models.report import ReportData
from models.metrics import AnalysisResult
from core.parser.md_parser import MarkdownParser
from core.calculator.ratios import FinancialCalculator
from core.calculator.anomaly import AnomalyDetector
from core.analyst.llm import LLMAnalyst

logger = logging.getLogger(__name__)


class FinBotService:
    def __init__(self, use_llm: bool = True):
        self.parser = MarkdownParser()
        self.calculator = FinancialCalculator()
        self.detector = AnomalyDetector()
        self.analyst = LLMAnalyst() if use_llm else None

    def parse_file(self, file_path: str) -> ReportData:
        """Bước 1: Parse file → ReportData"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        content = path.read_text(encoding="utf-8")

        if path.suffix in (".md", ".html", ".htm"):
            return self.parser.parse(content, source_file=str(path))

        raise ValueError(f"Chưa hỗ trợ định dạng: {path.suffix}")

    def parse_content(self, content: str, filename: str = "") -> ReportData:
        """Parse từ raw string content"""
        return self.parser.parse(content, source_file=filename)

    def calculate(self, data: ReportData) -> AnalysisResult:
        """Bước 2+3: Tính metrics + detect anomalies"""
        metrics = self.calculator.calculate(data)
        flags = self.detector.detect(data, metrics)
        return AnalysisResult(metrics=metrics, flags=flags)

    def analyze(self, data: ReportData, language: str = "vi") -> AnalysisResult:
        """Full pipeline: parse → calculate → anomaly → LLM"""
        result = self.calculate(data)

        if self.analyst:
            result.llm_analysis = self.analyst.analyze(data, result, language)
        else:
            result.llm_analysis = {"note": "LLM disabled — chỉ có metrics và flags"}

        return result

    def chat(
        self,
        data: ReportData,
        result: AnalysisResult,
        question: str,
        history: list = None
    ) -> dict:
        """Chat Q&A với báo cáo"""
        if not self.analyst:
            return {"answer": "LLM không khả dụng.", "cited_figures": []}
        return self.analyst.chat(data, result, question, history)
