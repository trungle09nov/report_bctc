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

class BankingMetrics:
    """Chỉ số đặc thù ngân hàng (TT49) — Python tính, LLM chỉ diễn giải"""

    npl: Optional[float] = None                  # Non-performing loans (nợ xấu)
    llr_npl: Optional[float] = None              # Tỷ lệ dự phòng bao nợ xấu
    car: Optional[float] = None                  # Hệ số an toàn vốn (CAR)
    casa: Optional[float] = None                 # CASA ratio
    non_interest_income: Optional[float] = None  # Thu nhập ngoài lãi

    # ── Thu nhập (tỷ đồng) ───────────────────────────────────────────
    interest_income: Optional[float] = None          # Thu nhập lãi
    interest_expense: Optional[float] = None         # Chi phí lãi
    net_interest_income: Optional[float] = None      # NII = Thu nhập lãi thuần
    net_interest_income_prev: Optional[float] = None
    net_fee_income: Optional[float] = None           # Lãi thuần dịch vụ
    total_operating_income: Optional[float] = None   # TOI = Tổng thu nhập HĐ
    total_operating_income_prev: Optional[float] = None
    operating_expense: Optional[float] = None        # OPEX = Chi phí hoạt động
    pre_provision_profit: Optional[float] = None     # PPOP = LN trước dự phòng
    loan_loss_provision: Optional[float] = None      # CP dự phòng RRTD

    # ── Bảng cân đối (tỷ đồng) ───────────────────────────────────────
    loans_gross: Optional[float] = None              # Dư nợ cho vay KH (gộp)
    loans_gross_prev: Optional[float] = None
    loan_provisions_balance: Optional[float] = None  # Dự phòng trên BCĐKT
    customer_deposits: Optional[float] = None        # Tiền gửi KH
    customer_deposits_prev: Optional[float] = None

    # ── Tỷ số đặc thù ngân hàng (%) ─────────────────────────────────
    nim: Optional[float] = None       # Net Interest Margin (annualized)
    ldr: Optional[float] = None       # Loan-to-Deposit Ratio
    cir: Optional[float] = None       # Cost-to-Income Ratio
    credit_cost: Optional[float] = None  # Provision / Avg Loans (annualized)

    # ── Tăng trưởng (%) ──────────────────────────────────────────────
    nii_growth: Optional[float] = None     # % tăng NII YoY
    toi_growth: Optional[float] = None     # % tăng TOI YoY
    loan_growth: Optional[float] = None    # % tăng dư nợ YoY
    deposit_growth: Optional[float] = None # % tăng tiền gửi YoY

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class AnalysisResult:
    """Kết quả phân tích đầy đủ"""
    metrics: FinancialMetrics = field(default_factory=FinancialMetrics)
    dupont: Optional["DuPontMetrics"] = None
    cashflow: Optional["CashFlowMetrics"] = None
    beneish: Optional["BeneishScore"] = None
    banking: Optional["BankingMetrics"] = None
    flags: list[Flag] = field(default_factory=list)
    llm_analysis: dict = field(default_factory=dict)
    segment_analysis: list[dict] = field(default_factory=list)

    def to_api_response(self) -> dict:
        result = {
            "metrics": self.metrics.to_dict(),
            "flags": [f.to_dict() for f in self.flags],
            "analysis": self.llm_analysis,
            "segments": self.segment_analysis,
        }
        if self.dupont:
            result["dupont"] = self.dupont.to_dict()
        if self.cashflow:
            result["cashflow"] = self.cashflow.to_dict()
        if self.beneish:
            result["beneish"] = self.beneish.to_dict()
        if self.banking:
            result["banking"] = self.banking.to_dict()
        return result


@dataclass
class DuPontMetrics:
    """Phân tích DuPont 3 và 5 nhân tố"""
    # 3-factor
    net_margin: Optional[float] = None          # LNST / DT
    asset_turnover: Optional[float] = None      # DT / TS bình quân (annualized)
    equity_multiplier: Optional[float] = None   # TS / VCSH
    roe_dupont_3: Optional[float] = None        # = net_margin × asset_turnover × equity_multiplier

    # 5-factor (Disaggregate net_margin thành tax + interest burden + EBIT margin)
    tax_burden: Optional[float] = None          # LNST / LNTT  (tax efficiency)
    interest_burden: Optional[float] = None     # LNTT / EBIT   (interest impact)
    ebit_margin: Optional[float] = None         # EBIT / DT     (operating efficiency)
    roe_dupont_5: Optional[float] = None        # = tax × interest × ebit × turnover × leverage

    # Bóc tách nguồn gốc ROE
    roe_from_operations: Optional[float] = None  # Phần ROE đến từ hiệu quả vận hành
    roe_from_leverage: Optional[float] = None    # Phần ROE đến từ đòn bẩy

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class CashFlowMetrics:
    """Cash Conversion Cycle và phân tích dòng tiền nâng cao"""
    # CCC components
    dso: Optional[float] = None                 # Days Sales Outstanding
    dio: Optional[float] = None                 # Days Inventory Outstanding
    dpo: Optional[float] = None                 # Days Payable Outstanding
    ccc: Optional[float] = None                 # CCC = DSO + DIO - DPO

    # Free Cash Flow
    cfo: Optional[float] = None                 # Operating cash flow
    capex_total: Optional[float] = None         # Tổng capex
    fcf: Optional[float] = None                 # FCF = CFO - Capex
    fcf_yield: Optional[float] = None           # FCF / Revenue (%)
    fcf_to_net_profit: Optional[float] = None   # FCF / LNST — chất lượng lợi nhuận

    # Earnings quality
    accrual_ratio: Optional[float] = None       # (LNST - CFO) / TS bình quân
    cash_conversion: Optional[float] = None     # CFO / LNST — >1 là tốt

    # CFO breakdown
    cfo_prev: Optional[float] = None
    cfo_growth: Optional[float] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class BeneishScore:
    """
    Beneish M-Score — phát hiện nguy cơ gian lận BCTC
    Score > -1.78 → nghi ngờ có manipulation
    Score > -2.22 → vùng xám, cần xem xét kỹ
    """
    # 8 thành phần
    dsri: Optional[float] = None    # Days Sales Receivable Index
    gmi: Optional[float] = None     # Gross Margin Index
    aqi: Optional[float] = None     # Asset Quality Index
    sgi: Optional[float] = None     # Sales Growth Index
    depi: Optional[float] = None    # Depreciation Index
    sgai: Optional[float] = None    # SGA Index
    lvgi: Optional[float] = None    # Leverage Index
    tata: Optional[float] = None    # Total Accruals to Total Assets

    m_score: Optional[float] = None
    interpretation: str = ""        # "likely_manipulator" / "gray_zone" / "likely_clean"
    confidence: str = ""            # "high" / "medium" / "low" (phụ thuộc data đủ không)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}
