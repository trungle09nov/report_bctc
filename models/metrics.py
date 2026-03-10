from dataclasses import dataclass, field
from typing import Optional
from .flag import Flag


@dataclass
class FinancialMetrics:
    """Các chỉ số tài chính đã tính — Python tính, LLM chỉ diễn giải"""

    # ── Thanh khoản ──────────────────────────────────────────
    current_ratio: Optional[float] = None       # Tài sản NH / Nợ NH
    quick_ratio: Optional[float] = None         # (Tài sản NH - HTK) / Nợ NH
    cash_ratio: Optional[float] = None          # Tiền / Nợ NH

    # ── Lợi nhuận ────────────────────────────────────────────
    gross_margin: Optional[float] = None        # LN gộp / DT thuần
    operating_margin: Optional[float] = None    # LN hoạt động / DT thuần
    net_margin: Optional[float] = None          # LNST / DT thuần
    roe: Optional[float] = None                 # LNST / VCSH bình quân
    roa: Optional[float] = None                 # LNST / Tổng TS bình quân
    ebitda_margin: Optional[float] = None

    # ── Đòn bẩy tài chính ────────────────────────────────────
    debt_to_equity: Optional[float] = None      # Tổng nợ / VCSH
    debt_to_assets: Optional[float] = None      # Tổng nợ / Tổng TS
    interest_coverage: Optional[float] = None  # EBIT / Chi phí lãi vay

    # ── Hiệu quả vận hành ────────────────────────────────────
    dso: Optional[float] = None                 # Days Sales Outstanding (ngày)
    inventory_days: Optional[float] = None      # Số ngày tồn kho
    asset_turnover: Optional[float] = None      # DT / Tổng TS

    # ── Tăng trưởng ──────────────────────────────────────────
    revenue_growth_yoy: Optional[float] = None  # % tăng DT so cùng kỳ
    profit_growth_yoy: Optional[float] = None   # % tăng LN so cùng kỳ
    gross_margin_change: Optional[float] = None # Thay đổi biên LN gộp (pp)

    # ── Raw figures (nghìn tỷ VND) ───────────────────────────
    revenue: Optional[float] = None
    revenue_prev: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_profit: Optional[float] = None
    net_profit: Optional[float] = None
    net_profit_prev: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    equity: Optional[float] = None
    cash: Optional[float] = None
    inventory: Optional[float] = None
    trade_receivables: Optional[float] = None
    capex: Optional[float] = None

    # ── Đặc thù holding company ──────────────────────────────
    subsidiary_income: Optional[float] = None
    subsidiary_income_ratio: Optional[float] = None  # % so LNST

    def to_dict(self) -> dict:
        """Chỉ trả về các field có giá trị"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def format_vnd(self, value: Optional[float], unit: str = "tỷ") -> str:
        if value is None:
            return "N/A"
        if unit == "tỷ" and abs(value) >= 1000:
            return f"{value/1000:.1f} nghìn tỷ"
        return f"{value:.1f} {unit}"


@dataclass
class AnalysisResult:
    """Kết quả phân tích đầy đủ"""
    metrics: FinancialMetrics = field(default_factory=FinancialMetrics)
    flags: list[Flag] = field(default_factory=list)
    llm_analysis: dict = field(default_factory=dict)   # Output từ Claude
    segment_analysis: list[dict] = field(default_factory=list)

    def to_api_response(self) -> dict:
        return {
            "metrics": self.metrics.to_dict(),
            "flags": [f.to_dict() for f in self.flags],
            "analysis": self.llm_analysis,
            "segments": self.segment_analysis,
        }
