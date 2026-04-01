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

    # ── Sector-specific (TT200 — Manufacturing / Consumer) ───
    sga_ratio: Optional[float] = None           # (Selling + Admin) / Revenue (%)
    capex_intensity: Optional[float] = None     # Capex / Revenue (%)

    # ── Phân tích dọc (Common-Size) ──────────────────────────
    common_size_bs: dict = field(default_factory=dict)
    common_size_is: dict = field(default_factory=dict)

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
    securities: Optional["SecuritiesMetrics"] = None
    real_estate: Optional["RealEstateMetrics"] = None
    rubber: Optional["RubberMetrics"] = None
    insurance: Optional["InsuranceMetrics"] = None
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
        if self.securities:
            result["securities"] = self.securities.to_dict()
        if self.real_estate:
            result["real_estate"] = self.real_estate.to_dict()
        if self.rubber:
            result["rubber"] = self.rubber.to_dict()
        if self.insurance:
            result["insurance"] = self.insurance.to_dict()
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


@dataclass
class SecuritiesMetrics:
    """
    Chỉ số đặc thù công ty chứng khoán (TT210) — SSI, VND, HCM, MBS...
    Driver lợi nhuận: thanh khoản thị trường + tự doanh (FVTPL) + margin lending
    """

    # ── Tài sản (tỷ đồng) ────────────────────────────────────────────────────
    fvtpl_assets: Optional[float] = None        # Tài sản FVTPL (tự doanh) — BS 112
    margin_loans: Optional[float] = None        # Dư nợ cho vay ký quỹ — BS 114
    total_operating_revenue: Optional[float] = None
    total_operating_revenue_prev: Optional[float] = None

    # ── Cấu trúc doanh thu (tỷ đồng) ─────────────────────────────────────────
    brokerage_revenue: Optional[float] = None   # Môi giới — Income 06
    prop_trading_pnl: Optional[float] = None    # Tự doanh thuần (gains - losses) — 01 - 21
    advisory_revenue: Optional[float] = None    # Tư vấn + tư vấn tài chính — 08 + 10
    interest_income: Optional[float] = None     # Lãi từ cho vay + HTM + AFS — 02+03+04

    # ── Tỷ trọng doanh thu (%) ────────────────────────────────────────────────
    brokerage_ratio: Optional[float] = None     # Môi giới / Tổng DT HĐ
    prop_trading_ratio: Optional[float] = None  # Tự doanh / Tổng DT HĐ
    interest_ratio: Optional[float] = None      # Lãi vay KQ / Tổng DT HĐ

    # ── Đòn bẩy & rủi ro ─────────────────────────────────────────────────────
    margin_to_equity: Optional[float] = None    # Cho vay ký quỹ / VCSH — rủi ro đòn bẩy
    fvtpl_to_equity: Optional[float] = None     # FVTPL / VCSH — rủi ro tự doanh

    # ── Hiệu quả vận hành ─────────────────────────────────────────────────────
    cir: Optional[float] = None                 # Admin expense / Total operating revenue (%)
    revenue_growth_yoy: Optional[float] = None  # % tăng tổng DT HĐ YoY

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class RealEstateMetrics:
    """
    Chỉ số đặc thù bất động sản (TT200) — VIC, VHM, NVL, KDH...
    BCTC khác biệt: doanh thu ghi nhận theo bàn giao, tiền đặt cọc là proxy backlog
    """

    # ── Backlog / Tiền đặt cọc (tỷ đồng) ────────────────────────────────────
    advance_from_customers_st: Optional[float] = None  # Người mua trả tiền trước NH — BS 313
    advance_from_customers_lt: Optional[float] = None  # Người mua trả tiền trước DH — BS 332
    total_advance: Optional[float] = None              # Tổng tiền đặt cọc (ST + LT)
    advance_prev: Optional[float] = None               # Kỳ trước (để tính tăng trưởng)

    # ── Tồn kho BĐS (tỷ đồng) ────────────────────────────────────────────────
    inventory: Optional[float] = None                  # Tổng HTK (BĐS đang XD + chờ bán)

    # ── Tỷ số đặc thù ────────────────────────────────────────────────────────
    advance_to_revenue: Optional[float] = None         # Tiền đặt cọc / DT kỳ (số kỳ coverage)
    advance_to_equity: Optional[float] = None          # Tiền đặt cọc / VCSH — đòn bẩy từ KH
    inventory_to_revenue: Optional[float] = None       # HTK / DT kỳ (kỳ thu hồi HTK)
    inventory_to_equity: Optional[float] = None        # HTK / VCSH

    # ── Chất lượng doanh thu ──────────────────────────────────────────────────
    advance_growth_yoy: Optional[float] = None         # % tăng tiền đặt cọc YoY (leading indicator)
    revenue_growth_yoy: Optional[float] = None         # % tăng DT — không đều theo chu kỳ dự án

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class RubberMetrics:
    """
    Chỉ số đặc thù ngành cao su (TT200) — GVR và tương tự.

    GVR khác HPG ở 4 điểm cốt lõi:
      1. Tài sản sinh học (vườn cây) hạch toán vào TSCĐ hữu hình — depreciation theo chu kỳ khai thác
      2. Danh mục đầu tư tài chính lớn (tiền gửi + HTM) → thu nhập tài chính đáng kể
      3. Phần lãi từ công ty liên kết (KCN) → đóng góp vào lợi nhuận nhưng không phải operating
      4. Minority interest cao → lợi nhuận quy về cổ đông công ty mẹ thấp hơn LNST hợp nhất
    """

    # ── Thu nhập tài chính từ danh mục đầu tư (tỷ đồng) ─────────────────────
    financial_income: Optional[float] = None          # Income code 21 — lãi tiền gửi + trái phiếu
    financial_income_ratio: Optional[float] = None    # financial_income / revenue (%)

    # ── Danh mục đầu tư tài chính (tỷ đồng) ─────────────────────────────────
    investment_assets_st: Optional[float] = None      # BS 120 — đầu tư TC ngắn hạn (tiền gửi, HTM NH)
    investment_assets_lt: Optional[float] = None      # BS 250 — đầu tư TC dài hạn
    total_investment_assets: Optional[float] = None   # Tổng danh mục đầu tư
    investment_yield: Optional[float] = None          # financial_income / total_investment_assets (%)

    # ── Phần lãi từ công ty liên kết (KCN, liên doanh) (tỷ đồng) ────────────
    share_of_associates: Optional[float] = None       # Income code 24 — liên kết / KCN
    associates_to_profit: Optional[float] = None      # share_of_associates / operating_profit (%)

    # ── Thu nhập khác (vườn cây thanh lý, chuyển nhượng đất) (tỷ đồng) ──────
    other_income: Optional[float] = None              # Income code 31 — thường một lần (non-recurring)
    other_income_ratio: Optional[float] = None        # other_income / gross_profit (%) — nếu >30% = flag

    # ── Phân bổ lợi nhuận (NCI — minority interest) ─────────────────────────
    attributable_profit: Optional[float] = None       # Income code 61 — LNST quy về cổ đông công ty mẹ
    nci_profit: Optional[float] = None                # Income code 62 — LNST cổ đông không kiểm soát
    nci_ratio: Optional[float] = None                 # nci_profit / total_net_profit (%) — nếu >30% = flag

    # ── Tài sản vườn cây & tái canh (tỷ đồng) ───────────────────────────────
    plantation_assets: Optional[float] = None         # BS 221 — TSCĐ hữu hình (proxy vườn cây cao su)
    replanting_wip: Optional[float] = None            # BS 242 — XDCB dở dang (chi phí tái canh)
    investment_property: Optional[float] = None       # BS 230 — BĐS đầu tư (đất KCN)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class InsuranceMetrics:
    """
    Chỉ số đặc thù bảo hiểm (TT200) — BVH, BIC, PTI, PVI...
    Derive từ FinancialMetrics — không cần keyword mapping riêng.

    Logic:
      - loss_ratio   = 100 - gross_margin  (COGS ≈ chi phí bồi thường + dự phòng)
      - expense_ratio = sga_ratio          (selling + admin / premium revenue)
      - combined_ratio = loss_ratio + expense_ratio
        < 100% → có lãi từ nghiệp vụ bảo hiểm (underwriting profit)
        > 100% → lỗ từ nghiệp vụ, phải bù đắp bằng lãi đầu tư tài chính
    """
    # ── Tỷ lệ nghiệp vụ (%) ──────────────────────────────────────────────────
    loss_ratio: Optional[float] = None          # Chi phí bồi thường / Phí BH thuần
    expense_ratio: Optional[float] = None       # (Hoa hồng + Quản lý) / Phí BH thuần
    combined_ratio: Optional[float] = None      # loss_ratio + expense_ratio

    # ── Thu nhập đầu tư ───────────────────────────────────────────────────────
    investment_income: Optional[float] = None   # Thu nhập tài chính (đầu tư danh mục)
    investment_yield: Optional[float] = None    # Thu nhập tài chính / Tổng TS (%)

    # ── Tăng trưởng ───────────────────────────────────────────────────────────
    premium_growth_yoy: Optional[float] = None  # % tăng phí BH thuần YoY

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}
