"""
FinBotService — orchestrator chính
Pipeline: Parser → Calculator → DuPont → CashFlow → Beneish → AnomalyDetector → LLMAnalyst
"""
import logging
import os
from pathlib import Path

from models.report import ReportData
from models.metrics import AnalysisResult
from core.parser.adaptive_parser import AdaptiveMarkdownParser
from core.calculator.ratios import FinancialCalculator
from core.calculator.dupont import DuPontCalculator
from core.calculator.cashflow import CashFlowCalculator
from core.calculator.beneish import BeneishCalculator
from core.calculator.anomaly import AnomalyDetector
from core.analyst.llm import LLMAnalyst

logger = logging.getLogger(__name__)


class FinBotService:
    def __init__(self, use_llm: bool = True):
        self.parser      = AdaptiveMarkdownParser()
        self.calculator  = FinancialCalculator()
        self.dupont_calc = DuPontCalculator()
        self.cf_calc     = CashFlowCalculator()
        self.beneish_calc = BeneishCalculator()
        self.detector    = AnomalyDetector()
        self.analyst     = LLMAnalyst() if (use_llm and os.getenv("OPENAI_API_KEY")) else None

    def parse_file(self, file_path: str) -> ReportData:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
        content = path.read_text(encoding="utf-8")
        if path.suffix in (".md", ".html", ".htm", ".txt"):
            return self.parser.parse(content, source_file=str(path))
        raise ValueError(f"Chưa hỗ trợ định dạng: {path.suffix}")

    def parse_content(self, content: str, filename: str = "") -> ReportData:
        return self.parser.parse(content, source_file=filename)

    def calculate(self, data: ReportData) -> AnalysisResult:
        """Full calculation pipeline — không gọi LLM"""
        # 1. Chỉ số cơ bản
        metrics = self.calculator.calculate(data)

        # 2. DuPont decomposition
        try:
            dupont = self.dupont_calc.calculate(data, metrics)
        except Exception as e:
            logger.warning(f"DuPont calc error: {e}")
            dupont = None

        # 3. Cash flow quality & CCC
        try:
            cashflow = self.cf_calc.calculate(data, metrics)
        except Exception as e:
            logger.warning(f"CashFlow calc error: {e}")
            cashflow = None

        # 4. Beneish M-Score (cần CFO từ cashflow)
        try:
            cfo = cashflow.cfo if cashflow else None
            beneish = self.beneish_calc.calculate(data, metrics, cfo=cfo)
        except Exception as e:
            logger.warning(f"Beneish calc error: {e}")
            beneish = None

        # 5. Anomaly detection — basic + advanced
        flags = self.detector.detect(data, metrics)
        try:
            adv_flags = self.detector.detect_advanced(data, metrics, cashflow, beneish)
            flags.extend(adv_flags)
        except Exception as e:
            logger.warning(f"Advanced anomaly error: {e}")

        return AnalysisResult(
            metrics=metrics,
            dupont=dupont,
            cashflow=cashflow,
            beneish=beneish,
            flags=flags,
        )

    def analyze(self, data: ReportData, language: str = "vi") -> AnalysisResult:
        """Full pipeline bao gồm LLM narrative"""
        result = self.calculate(data)
        if self.analyst:
            result.llm_analysis = self.analyst.analyze(data, result, language)
        else:
            result.llm_analysis = {"note": "LLM disabled"}
        return result

    def chat(self, data: ReportData, result: AnalysisResult,
             question: str, history: list = None) -> dict:
        if not self.analyst:
            return {"answer": "LLM không khả dụng.", "cited_figures": []}
        return self.analyst.chat(data, result, question, history)
