"""
LLM Analyst — wrapper cho OpenAI-compatible API
Nhận metrics + flags đã tính → trả về narrative analysis
Hỗ trợ OpenAI, Azure OpenAI, hoặc bất kỳ endpoint tương thích OpenAI
"""
import json
import os
import logging
from openai import OpenAI

from models.report import ReportData
from models.metrics import AnalysisResult
from models.flag import Flag
from core.analyst.prompts import (
    SYSTEM_FULL_ANALYSIS, build_analysis_prompt, build_chat_prompt
)
from core.parser.company_extractor import VN30_SECTOR_MAP, SECTOR_PROFIT_DRIVERS

logger = logging.getLogger(__name__)

# Cấu hình qua env vars
# OPENAI_API_KEY: API key
# OPENAI_BASE_URL: URL endpoint (mặc định: https://api.openai.com/v1)
# OPENAI_MODEL: Model name (mặc định: gpt-4o)
DEFAULT_MODEL = "gpt-4o"
MAX_TOKENS = 2000


class LLMAnalyst:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        """
        Khởi tạo LLM client với OpenAI-compatible API.
        
        Args:
            api_key: API key (hoặc lấy từ OPENAI_API_KEY env)
            base_url: Base URL cho API (hoặc lấy từ OPENAI_BASE_URL env)
                      Ví dụ: "http://localhost:8000/v1" cho local LLM
                             "https://api.openai.com/v1" cho OpenAI
            model: Tên model (hoặc lấy từ OPENAI_MODEL env)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY chưa được set — LLM sẽ không hoạt động")
            self.client = None
            return
        
        # Khởi tạo client với base_url nếu có (hỗ trợ custom endpoints)
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            logger.info(f"Sử dụng custom endpoint: {self.base_url}")
        
        self.client = OpenAI(**client_kwargs)
        logger.info(f"LLM initialized với model: {self.model}")

    def analyze(
        self,
        data: ReportData,
        result: AnalysisResult,
        language: str = "vi"
    ) -> dict:
        """
        Phân tích đầy đủ — trả về dict với executive_summary, highlights, sections, v.v.
        """
        if not self.client:
            raise RuntimeError("LLM client chưa được khởi tạo (thiếu API key)")
            
        # Build sector_info từ VN30_SECTOR_MAP nếu ticker được nhận diện
        sector_info = None
        ticker = getattr(data, "company_code", "") or ""
        if ticker and ticker.upper() in VN30_SECTOR_MAP:
            entry = VN30_SECTOR_MAP[ticker.upper()]
            sector_info = {
                "sector":        entry["sector"],
                "sub":           entry["sub"],
                "label":         entry["label"],
                "profit_driver": SECTOR_PROFIT_DRIVERS.get(entry["sub"], ""),
            }

        prompt = build_analysis_prompt(
            data, result.metrics, result.flags, language,
            dupont=result.dupont, cashflow=result.cashflow,
            beneish=result.beneish, banking=result.banking,
            securities=result.securities, real_estate=result.real_estate,
            insurance=result.insurance,
            sector_info=sector_info,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": SYSTEM_FULL_ANALYSIS},
                    {"role": "user", "content": prompt}
                ]
            )
            raw = response.choices[0].message.content.strip()

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
        if not self.client:
            raise RuntimeError("LLM client chưa được khởi tạo (thiếu API key)")
            
        system, messages = build_chat_prompt(
            data, result.metrics, result.flags,
            question, history or []
        )
        
        # Convert sang format OpenAI messages
        openai_messages = [{"role": "system", "content": system}]
        openai_messages.extend(messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=800,
                messages=openai_messages
            )
            raw = response.choices[0].message.content.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            return json.loads(raw)

        except json.JSONDecodeError:
            return {
                "answer": response.choices[0].message.content,
                "cited_figures": [],
                "confidence": "medium"
            }
        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            raise
