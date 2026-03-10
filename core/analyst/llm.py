"""
LLM Analyst — wrapper cho Claude API
Nhận metrics + flags đã tính → trả về narrative analysis
"""
import json
import os
import logging
from anthropic import Anthropic

from models.report import ReportData
from models.metrics import AnalysisResult
from models.flag import Flag
from core.analyst.prompts import (
    SYSTEM_FULL_ANALYSIS, build_analysis_prompt, build_chat_prompt
)

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2000


class LLMAnalyst:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY chưa được set — LLM sẽ không hoạt động")
            self.client = None
            return
        self.client = Anthropic(api_key=api_key)

    def analyze(
        self,
        data: ReportData,
        result: AnalysisResult,
        language: str = "vi"
    ) -> dict:
        """
        Phân tích đầy đủ — trả về dict với executive_summary, highlights, sections, v.v.
        """
        prompt = build_analysis_prompt(data, result.metrics, result.flags, language)

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_FULL_ANALYSIS,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()

            # Clean JSON (đôi khi model thêm fence)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            return json.loads(raw)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error từ LLM: {e}")
            return {
                "executive_summary": "Phân tích thành công nhưng không thể parse output.",
                "highlights": [],
                "risks": [f.to_dict() for f in result.flags],
                "sections": {},
                "outlook": ""
            }
        except Exception as e:
            logger.error(f"LLM analyze error: {e}")
            raise

    def chat(
        self,
        data: ReportData,
        result: AnalysisResult,
        question: str,
        history: list = None
    ) -> dict:
        """
        Q&A về báo cáo tài chính — trả về answer + cited_figures
        """
        system, messages = build_chat_prompt(
            data, result.metrics, result.flags,
            question, history or []
        )

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=800,
                system=system,
                messages=messages
            )
            raw = response.content[0].text.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            return json.loads(raw)

        except json.JSONDecodeError:
            return {
                "answer": response.content[0].text,
                "cited_figures": [],
                "confidence": "medium"
            }
        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            raise
